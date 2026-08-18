"""Persistent HotSwap v2 — atomic posterior learning and lossless Route roundtrips."""
from __future__ import annotations
import json,random
from qdw.core import utc_now
from qdw.core.db import Database
from qdw.hotswap.stats import beta_pseudo_counts,wilson_lower,clamp
from qdw.hotswap.types import Posterior,Route

class PersistentBanditStore:
    def __init__(self,db:Database):
        self.db=db

    def _prior(self,route:Route)->Posterior:
        p=route.prior_success if route.prior_success is not None else .5
        strength=2.0+8.0*clamp(route.prior_confidence)
        return Posterior(1.0+strength*p,1.0+strength*(1.0-p))

    def get(self,cell_id:str,route:Route)->Posterior:
        with self.db.connect() as con:
            row=con.execute("""SELECT alpha,beta FROM route_posteriors
                WHERE cell_id=? AND route_id=?""",(cell_id,route.route_id)).fetchone()
        if row:return Posterior(row["alpha"],row["beta"])
        prior=self._prior(route)
        # Critical: initialization must never overwrite a concurrently learned row.
        with self.db.tx(immediate=True) as con:
            con.execute("""INSERT OR IGNORE INTO route_posteriors(
                cell_id,route_id,alpha,beta,updated_at
            ) VALUES(?,?,?,?,?)""",(cell_id,route.route_id,prior.alpha,prior.beta,utc_now()))
            row=con.execute("""SELECT alpha,beta FROM route_posteriors
                WHERE cell_id=? AND route_id=?""",(cell_id,route.route_id)).fetchone()
        return Posterior(row["alpha"],row["beta"])

    def update(self,cell_id:str,route_id:str,success:bool,weight:float=1.0)->Posterior:
        with self.db.tx(immediate=True) as con:
            con.execute("""INSERT OR IGNORE INTO route_posteriors(
                cell_id,route_id,alpha,beta,updated_at
            ) VALUES(?,?,1.0,1.0,?)""",(cell_id,route_id,utc_now()))
            if success:
                con.execute("""UPDATE route_posteriors SET alpha=alpha+?,updated_at=?
                    WHERE cell_id=? AND route_id=?""",(weight,utc_now(),cell_id,route_id))
            else:
                con.execute("""UPDATE route_posteriors SET beta=beta+?,updated_at=?
                    WHERE cell_id=? AND route_id=?""",(weight,utc_now(),cell_id,route_id))
            row=con.execute("""SELECT alpha,beta FROM route_posteriors
                WHERE cell_id=? AND route_id=?""",(cell_id,route_id)).fetchone()
        return Posterior(row["alpha"],row["beta"])

    def mean_and_lower(self,cell_id:str,route:Route)->tuple[float,float]:
        p=self.get(cell_id,route)
        successes,trials=beta_pseudo_counts(p.alpha,p.beta)
        return p.mean,wilson_lower(successes,trials)

    def thompson(self,cell_id:str,route:Route,rng:random.Random|None=None)->float:
        r=rng or random
        p=self.get(cell_id,route)
        return r.betavariate(p.alpha,p.beta)

    def save_route(self,route:Route)->None:
        with self.db.tx(immediate=True) as con:
            con.execute("""INSERT INTO route_definitions(
                route_id,model_id,provider_id,active,free,input_per_m,output_per_m,context_tokens,
                tools_supported,json_supported,reliability,latency_ms,cheapest_paid_replacement_cost,
                created_at,updated_at,endpoint_id,account_id,prior_success,prior_confidence,
                breaker_open,quota_pressure,evidence_ids_json
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(route_id) DO UPDATE SET
                model_id=excluded.model_id,provider_id=excluded.provider_id,active=excluded.active,
                free=excluded.free,input_per_m=excluded.input_per_m,output_per_m=excluded.output_per_m,
                context_tokens=excluded.context_tokens,tools_supported=excluded.tools_supported,
                json_supported=excluded.json_supported,reliability=excluded.reliability,
                latency_ms=excluded.latency_ms,
                cheapest_paid_replacement_cost=excluded.cheapest_paid_replacement_cost,
                endpoint_id=excluded.endpoint_id,account_id=excluded.account_id,
                prior_success=excluded.prior_success,prior_confidence=excluded.prior_confidence,
                breaker_open=excluded.breaker_open,quota_pressure=excluded.quota_pressure,
                evidence_ids_json=excluded.evidence_ids_json,updated_at=excluded.updated_at""",
            (
                route.route_id,route.model_id,route.provider_id,1 if route.active else 0,1 if route.free else 0,
                route.input_per_m,route.output_per_m,route.context_tokens,
                None if route.tools_supported is None else int(route.tools_supported),
                None if route.json_supported is None else int(route.json_supported),
                route.reliability,route.latency_ms,route.cheapest_paid_replacement_cost,
                utc_now(),utc_now(),route.endpoint_id,route.account_id,route.prior_success,
                route.prior_confidence,1 if route.breaker_open else 0,route.quota_pressure,
                json.dumps(list(route.evidence_ids or []),sort_keys=True),
            ))

    def load_routes(self,active_only:bool=True)->list[Route]:
        with self.db.connect() as con:
            sql="SELECT * FROM route_definitions"
            if active_only:sql+=" WHERE active=1"
            sql+=" ORDER BY route_id"
            rows=con.execute(sql).fetchall()
        out=[]
        for r in rows:
            out.append(Route(
                route_id=r["route_id"],model_id=r["model_id"],provider_id=r["provider_id"],
                endpoint_id=r["endpoint_id"],account_id=r["account_id"],active=bool(r["active"]),
                free=bool(r["free"]),input_per_m=r["input_per_m"],output_per_m=r["output_per_m"],
                context_tokens=r["context_tokens"],
                tools_supported=None if r["tools_supported"] is None else bool(r["tools_supported"]),
                json_supported=None if r["json_supported"] is None else bool(r["json_supported"]),
                reliability=r["reliability"],latency_ms=r["latency_ms"],prior_success=r["prior_success"],
                prior_confidence=r["prior_confidence"],breaker_open=bool(r["breaker_open"]),
                quota_pressure=r["quota_pressure"],
                cheapest_paid_replacement_cost=r["cheapest_paid_replacement_cost"],
                evidence_ids=json.loads(r["evidence_ids_json"] or "[]"),
            ))
        return out

class RouteRegistry:
    """Durable identity + in-memory projection keyed by route_id."""
    def __init__(self,store:PersistentBanditStore):
        self.store=store
        self._routes={r.route_id:r for r in store.load_routes()}

    def register(self,route:Route)->None:
        self.store.save_route(route)
        self._routes[route.route_id]=route

    def active(self)->list[Route]:
        return [self._routes[k] for k in sorted(self._routes) if self._routes[k].active]

    def get(self,route_id:str)->Route:
        return self._routes[route_id]

    def reload(self)->None:
        self._routes={r.route_id:r for r in self.store.load_routes()}

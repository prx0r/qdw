from __future__ import annotations
import json,secrets,sqlite3
from datetime import UTC,datetime
from .hashing import sha256_obj
from .models import InvocationRequest,InvocationRecord,InvocationStatus,RouteDecision
from .schema_validation import validate_shallow
from .federation import CertificateReference,CertificateResolver

def now():return datetime.now(UTC)

class InvocationService:
    def __init__(self,db,store,leases,router,dispatcher,resolver:CertificateResolver):
        self.db,self.store,self.leases,self.router,self.dispatcher,self.resolver=(
          db,store,leases,router,dispatcher,resolver)

    def invoke(self,req:InvocationRequest,*,client_id:str)->InvocationRecord:
        # AUTHORIZATION FIRST. No idempotent output can be disclosed before valid lease proof.
        lease=self.leases.verify(req.lease_token,req.capability,operation="invoke",client_id=client_id)
        asset,decision=self.router.choose(req.capability,asset_id=lease.asset_id,version=lease.version)
        ih=sha256_obj(req.arguments)

        with self.db.connect() as con:
            old=con.execute("""SELECT * FROM invocations
              WHERE client_id=? AND client_request_id=?""",(client_id,req.client_request_id)).fetchone()
        if old:
            if old["capability"]!=req.capability or old["asset_id"]!=lease.asset_id or old["version"]!=lease.version:
                raise ValueError("IDEMPOTENCY_ROUTE_MISMATCH")
            if old["input_hash"]!=ih:raise ValueError("IDEMPOTENCY_INPUT_MISMATCH")
            return self._row(old)

        errs=validate_shallow(asset.input_schema,req.arguments)
        if errs:raise ValueError("input schema violation: "+"; ".join(errs))
        quoted=float(asset.pricing.per_call)
        self.leases.reserve(lease.lease_id,quoted)
        iid="inv_"+secrets.token_hex(12);created=now()

        try:
            with self.db.tx(immediate=True) as con:
                con.execute("""INSERT INTO invocations(
                  invocation_id,client_id,client_request_id,lease_id,capability,asset_id,version,input_hash,
                  status,quoted_cost_usd,billable_cost_usd,pricing_violation,route_json,created_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (iid,client_id,req.client_request_id,lease.lease_id,req.capability,asset.asset_id,
                 asset.version,ih,InvocationStatus.ACCEPTED.value,quoted,quoted,0,
                 decision.model_dump_json(),created.isoformat()))
        except sqlite3.IntegrityError:
            # Concurrent duplicate: re-read and apply the same binding checks.
            with self.db.connect() as con:
                old=con.execute("""SELECT * FROM invocations
                  WHERE client_id=? AND client_request_id=?""",(client_id,req.client_request_id)).fetchone()
            if not old:raise
            # Reservation was made by this contender. Refund it.
            self.leases.settle(lease.lease_id,quoted,0)
            if old["capability"]!=req.capability or old["asset_id"]!=lease.asset_id or old["version"]!=lease.version:
                raise ValueError("IDEMPOTENCY_ROUTE_MISMATCH")
            if old["input_hash"]!=ih:raise ValueError("IDEMPOTENCY_INPUT_MISMATCH")
            return self._row(old)

        try:
            output,actual=self.dispatcher.invoke(asset,req.arguments)
            settlement=self.leases.settle(lease.lease_id,quoted,float(actual))
            oh=sha256_obj(output);finished=now()
            with self.db.tx(immediate=True) as con:
                con.execute("""UPDATE invocations SET status=?,output_json=?,output_hash=?,
                  actual_cost_usd=?,billable_cost_usd=?,pricing_violation=?,finished_at=?
                  WHERE invocation_id=?""",
                (InvocationStatus.SUCCEEDED_UNVERIFIED.value,json.dumps(output,sort_keys=True),
                 oh,settlement["actual_cost_usd"],settlement["billable_cost_usd"],
                 1 if settlement["pricing_violation"] else 0,finished.isoformat(),iid))
            return self.get(iid)
        except Exception as exc:
            # A dispatcher exception without an actual-cost receipt is not billable.
            settlement=self.leases.settle(lease.lease_id,quoted,0)
            finished=now()
            with self.db.tx(immediate=True) as con:
                con.execute("""UPDATE invocations SET status=?,actual_cost_usd=0,billable_cost_usd=0,
                  failure=?,finished_at=? WHERE invocation_id=?""",
                  (InvocationStatus.FAILED.value,str(exc),finished.isoformat(),iid))
            return self.get(iid)

    def bind_verification(self,invocation_id:str,cert:CertificateReference,*,client_id:str):
        inv=self.get(invocation_id)
        # Caller must own the invocation.
        with self.db.connect() as con:
            r=con.execute("SELECT client_id FROM invocations WHERE invocation_id=?",(invocation_id,)).fetchone()
        if not r or r["client_id"]!=client_id:raise PermissionError("invocation client mismatch")
        if cert.issuer_system!="qdw":raise PermissionError("untrusted issuer")
        if cert.subject.system!="forge" or cert.subject.object_type!="invocation":
            raise ValueError("certificate subject type mismatch")
        if cert.subject.object_id!=invocation_id:raise ValueError("certificate invocation mismatch")
        expected=inv.output_hash or sha256_obj({"failed":invocation_id})
        if cert.subject_output_digest!=expected:raise ValueError("certificate output mismatch")

        resolved=self.resolver.resolve(cert)
        if resolved.get("certificate_hash")!=cert.certificate_hash:raise ValueError("resolved certificate hash mismatch")
        if resolved.get("status")!=cert.status:raise ValueError("resolved certificate status mismatch")
        if (resolved.get("subject") or {}).get("object_id")!=invocation_id:raise ValueError("resolved subject mismatch")
        if resolved.get("output_digest")!=expected:raise ValueError("resolved output mismatch")

        success=cert.status=="VERIFIED"
        applied=self.store.apply_verified_result(
          asset_id=inv.asset_id,version=inv.version,capability=inv.capability,
          certificate_id=cert.certificate_id,certificate_hash=cert.certificate_hash,
          invocation_id=invocation_id,output_hash=expected,policy_hash=cert.policy_hash,
          success=success,cost_usd=float(inv.cost_usd))
        if applied:
            with self.db.tx(immediate=True) as con:
                con.execute("UPDATE invocations SET status=?,verification_certificate_id=? WHERE invocation_id=?",
                            (InvocationStatus.VERIFIED.value if success else InvocationStatus.REJECTED.value,
                             cert.certificate_id,invocation_id))
        return self.get(invocation_id)

    def get(self,invocation_id):
        with self.db.connect() as con:r=con.execute("SELECT * FROM invocations WHERE invocation_id=?",(invocation_id,)).fetchone()
        if not r:raise KeyError(invocation_id)
        return self._row(r)

    def _row(self,r):
        # Preserve public V1 `cost_usd` as billable cost while detailed fields remain queryable in DB/API v2.
        return InvocationRecord(
          invocation_id=r["invocation_id"],client_request_id=r["client_request_id"],lease_id=r["lease_id"],
          capability=r["capability"],asset_id=r["asset_id"],version=r["version"],input_hash=r["input_hash"],
          status=InvocationStatus(r["status"]),output=json.loads(r["output_json"]) if r["output_json"] else None,
          output_hash=r["output_hash"],cost_usd=float(r["billable_cost_usd"] or 0),
          route_decision=RouteDecision.model_validate_json(r["route_json"]) if r["route_json"] else None,
          verification_certificate_id=r["verification_certificate_id"],failure=r["failure"],
          created_at=datetime.fromisoformat(r["created_at"]),
          finished_at=datetime.fromisoformat(r["finished_at"]) if r["finished_at"] else None)

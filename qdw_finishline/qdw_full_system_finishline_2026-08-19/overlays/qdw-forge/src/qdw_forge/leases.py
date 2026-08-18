from __future__ import annotations
import hashlib,secrets,time
from datetime import UTC,datetime
from .models import CapabilityLease,LeaseRequest
from .tokens import LeaseTokenSigner

def now():return datetime.now(UTC)
def token_hash(token):return hashlib.sha256(token.encode()).hexdigest()

class LeaseService:
    def __init__(self,db,router,signer:LeaseTokenSigner):
        self.db,self.router,self.signer=db,router,signer

    def create(self,req:LeaseRequest,*,client_id:str):
        if not client_id:raise ValueError("client_id required")
        asset,decision=self.router.choose(req.capability,asset_id=req.asset_id,version=req.version,
                                          quality_floor=req.quality_floor)
        lid="lease_"+secrets.token_hex(12)
        exp=time.time()+req.ttl_seconds
        claims={"lease_id":lid,"client_id":client_id,"capability":req.capability,
                "asset_id":asset.asset_id,"version":asset.version,
                "operations":sorted(set(req.allowed_operations)),"exp":exp}
        token=self.signer.issue(claims);th=token_hash(token)
        lease=CapabilityLease(
          lease_id=lid,capability=req.capability,asset_id=asset.asset_id,version=asset.version,
          calls_total=req.calls,calls_used=0,max_spend_usd=req.max_spend_usd,spend_usd=0,
          allowed_operations=claims["operations"],expires_at=datetime.fromtimestamp(exp,UTC),status="ACTIVE")
        with self.db.tx(immediate=True) as con:
            con.execute("""INSERT INTO leases(
              lease_id,capability,asset_id,version,token_hash,calls_total,calls_used,max_spend_usd,
              spend_usd,allowed_operations_json,expires_at,status,client_id
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (lid,req.capability,asset.asset_id,asset.version,th,req.calls,0,req.max_spend_usd,0,
             __import__("json").dumps(claims["operations"]),lease.expires_at.isoformat(),"ACTIVE",client_id))
        return lease,token,decision

    def verify(self,token:str,capability:str,*,operation:str,client_id:str)->CapabilityLease:
        try:claims=self.signer.verify(token)
        except ValueError as e:raise PermissionError(str(e)) from e
        if claims.get("client_id")!=client_id:raise PermissionError("lease client mismatch")
        if claims.get("capability")!=capability:raise PermissionError("lease capability mismatch")
        if operation not in set(claims.get("operations") or []):raise PermissionError("operation not permitted")
        lid=claims.get("lease_id")
        with self.db.connect() as con:r=con.execute("SELECT * FROM leases WHERE lease_id=?",(lid,)).fetchone()
        if not r or r["status"]!="ACTIVE":raise PermissionError("lease inactive")
        if r["client_id"]!=client_id:raise PermissionError("lease database client mismatch")
        if r["token_hash"]!=token_hash(token):raise PermissionError("lease token binding mismatch")
        if r["expires_at"]<now().isoformat():raise PermissionError("lease expired")
        if r["asset_id"]!=claims.get("asset_id") or r["version"]!=claims.get("version"):
            raise PermissionError("lease asset binding mismatch")
        import json
        ops=json.loads(r["allowed_operations_json"])
        if operation not in ops:raise PermissionError("operation not permitted")
        return CapabilityLease(
          lease_id=r["lease_id"],capability=r["capability"],asset_id=r["asset_id"],version=r["version"],
          calls_total=r["calls_total"],calls_used=r["calls_used"],max_spend_usd=r["max_spend_usd"],
          spend_usd=r["spend_usd"],allowed_operations=ops,expires_at=datetime.fromisoformat(r["expires_at"]),
          status=r["status"])

    def reserve(self,lease_id:str,quoted_cost:float):
        if quoted_cost<0:raise ValueError("negative quoted cost")
        with self.db.tx(immediate=True) as con:
            r=con.execute("SELECT * FROM leases WHERE lease_id=?",(lease_id,)).fetchone()
            if not r or r["status"]!="ACTIVE":raise PermissionError("lease inactive")
            if r["calls_used"]>=r["calls_total"]:raise PermissionError("lease call quota exhausted")
            new_spend=float(r["spend_usd"])+quoted_cost
            if r["max_spend_usd"] is not None and new_spend>float(r["max_spend_usd"])+1e-12:
                raise PermissionError("lease spend budget exceeded")
            con.execute("UPDATE leases SET calls_used=calls_used+1,spend_usd=? WHERE lease_id=?",
                        (new_spend,lease_id))
        return quoted_cost

    def settle(self,lease_id:str,quoted_cost:float,actual_cost:float):
        if actual_cost<0:raise ValueError("negative actual cost")
        billable=min(quoted_cost,actual_cost)
        violation=actual_cost>quoted_cost+1e-12
        refund=quoted_cost-billable
        if refund:
            with self.db.tx(immediate=True) as con:
                r=con.execute("SELECT spend_usd FROM leases WHERE lease_id=?",(lease_id,)).fetchone()
                if not r:raise KeyError(lease_id)
                con.execute("UPDATE leases SET spend_usd=? WHERE lease_id=?",
                            (max(0,float(r["spend_usd"])-refund),lease_id))
        return {"quoted_cost_usd":quoted_cost,"actual_cost_usd":actual_cost,
                "billable_cost_usd":billable,"pricing_violation":violation}

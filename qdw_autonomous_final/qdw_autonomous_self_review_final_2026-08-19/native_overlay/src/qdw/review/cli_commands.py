from __future__ import annotations
from pathlib import Path
import json,subprocess
from .models import ReviewRequest
from .policy import load_policy

def _git(root:Path):
    sha=subprocess.run(["git","rev-parse","HEAD"],cwd=root,capture_output=True,text=True,check=True).stdout.strip()
    dirty=bool(subprocess.run(["git","status","--porcelain"],cwd=root,capture_output=True,text=True,check=True).stdout.strip())
    base=subprocess.run(["git","rev-parse","HEAD~1"],cwd=root,capture_output=True,text=True)
    base_sha=base.stdout.strip() if base.returncode==0 else None
    diff=subprocess.run(["git","diff","--name-only",base_sha or "HEAD","HEAD"],cwd=root,capture_output=True,text=True)
    changed=tuple(x for x in diff.stdout.splitlines() if x)
    return sha,dirty,base_sha,changed

def cmd_review(system,args,*,repo_root=".")->int:
    """Integrate under existing `qdw review ...` CLI dispatcher."""
    root=Path(repo_root).resolve()
    if not args:
        print("Usage: qdw review <scan|run|status|findings|pack> ...")
        return 2
    sub=args[0]

    if sub=="scan":
        profile=args[args.index("--profile")+1] if "--profile" in args else "quick"
        policy=load_policy(root/f"policies/review/{profile if profile in {'quick','release','self-review'} else 'change-aware'}.json")
        sha,dirty,base,changed=_git(root)
        req=ReviewRequest(sha,dirty,base,changed,"manual_scan",profile,policy)
        rid=system.review.start(req)
        plan=system.review.begin_round(
            rid,subject_sha=sha,changed_paths=changed,profile=profile,policy=policy,repo_root=root
        )
        print(json.dumps({"review_run_id":rid,**plan},indent=2))
        return 0

    if sub=="run":
        profile=args[args.index("--profile")+1] if "--profile" in args else "change-aware"
        policy_name="release" if profile=="release" else ("self-review" if profile=="self-review" else profile)
        if policy_name not in {"quick","change-aware","release","self-review"}:policy_name="change-aware"
        policy=load_policy(root/f"policies/review/{policy_name}.json")
        sha,dirty,base,changed=_git(root)
        req=ReviewRequest(sha,dirty,base,changed,"manual_run",profile,policy)
        out=system.review_controller.run(
            req,policy=policy,workspace=root,certifier_worker_id="qdw-review-certifier",
            remote_ci=None,pack_path=root/".qdw/review"/f"qdw-review-{sha[:12]}.zip",
        )
        print(json.dumps(out.__dict__,indent=2))
        return 0 if out.status=="CERTIFIED" else 1

    if sub=="status":
        rid=args[1]
        print(json.dumps(system.review.report(rid),indent=2,default=str))
        return 0

    if sub=="findings":
        rid=args[1]
        rows=system.review.store.open_findings(rid)
        print(json.dumps(rows,indent=2,default=str))
        return 0

    if sub=="pack":
        rid=args[1]
        out=Path(args[2] if len(args)>2 else f".qdw/review/{rid}.zip")
        print(json.dumps(system.review.export_pack(rid,out),indent=2))
        return 0

    print(f"Unknown review subcommand: {sub}")
    return 2

from __future__ import annotations
import ast,hashlib,json,os,py_compile,re,shutil,sqlite3,subprocess,sys,tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
VAL=ROOT/"validation"
VAL.mkdir(exist_ok=True)

def sha_bytes(b):return hashlib.sha256(b).hexdigest()

result={"schema":"qdw.finishline-pack-validation.v2","checks":{}}

# Python syntax without polluting pack with pyc files.
tmp=Path(tempfile.mkdtemp(prefix="qdw-finishline-pyc-"))
bad=[];count=0
try:
    for i,p in enumerate(sorted(ROOT.rglob("*.py"))):
        count+=1
        try:py_compile.compile(str(p),cfile=str(tmp/f"{i}.pyc"),doraise=True)
        except Exception as e:bad.append({"path":str(p.relative_to(ROOT)),"error":repr(e)})
finally:shutil.rmtree(tmp,ignore_errors=True)
result["checks"]["python_syntax"]={"files":count,"failures":bad}

# JSON.
bad=[];count=0
for p in sorted(ROOT.rglob("*.json")):
    if p.name in {"PACK_VALIDATION.json","MANIFEST.json"}:continue
    count+=1
    try:json.loads(p.read_text())
    except Exception as e:bad.append({"path":str(p.relative_to(ROOT)),"error":repr(e)})
result["checks"]["json"]={"files":count,"failures":bad}

# Shell.
bad=[];count=0
for p in sorted(ROOT.rglob("*.sh")):
    count+=1;q=subprocess.run(["bash","-n",str(p)],capture_output=True,text=True)
    if q.returncode:bad.append({"path":str(p.relative_to(ROOT)),"stderr":q.stderr})
result["checks"]["shell_syntax"]={"files":count,"failures":bad}

# Acceptance immutable hashes.
bad=[];count=0
for p in sorted((ROOT/"acceptance/specs").glob("*.json")):
    count+=1;d=json.loads(p.read_text());stored=d.pop("acceptance_hash")
    actual="sha256:"+hashlib.sha256(json.dumps(d,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    if stored!=actual:bad.append({"path":str(p.relative_to(ROOT)),"stored":stored,"actual":actual})
result["checks"]["acceptance_hashes"]={"files":count,"failures":bad}

# Test-tree anti-cheat.
findings=[]
for root in [ROOT/"reference_finishline/tests",ROOT/"lab/tests",ROOT/"overlays"]:
    for p in root.rglob("test_*.py"):
        tree=ast.parse(p.read_text())
        for n in ast.walk(tree):
            if isinstance(n,ast.Assert) and isinstance(n.test,ast.Constant) and n.test.value is True:
                findings.append({"path":str(p.relative_to(ROOT)),"line":n.lineno,"code":"ASSERT_TRUE"})
            if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name.startswith("test_"):
                if len(n.body)==1 and isinstance(n.body[0],ast.Pass):
                    findings.append({"path":str(p.relative_to(ROOT)),"line":n.lineno,"code":"EMPTY_TEST"})
                for d in n.decorator_list:
                    name=ast.unparse(d)
                    if "skip" in name or "xfail" in name:
                        findings.append({"path":str(p.relative_to(ROOT)),"line":n.lineno,"code":"SKIP_XFAIL"})
            if isinstance(n,ast.Call) and ast.unparse(n.func) in {"pytest.skip","pytest.xfail"}:
                findings.append({"path":str(p.relative_to(ROOT)),"line":n.lineno,"code":"SKIP_XFAIL"})
result["checks"]["test_integrity"]={"findings":findings}

# Executable code unfinished markers.
markers=[]
needles=[r"\bTODO\b",r"\bFIXME\b",r"NotImplementedError"]
for p in ROOT.rglob("*.py"):
    if p==Path(__file__).resolve():continue
    text=p.read_text(errors="replace")
    for pat in needles:
        for m in re.finditer(pat,text,re.I):
            markers.append({"path":str(p.relative_to(ROOT)),"line":text[:m.start()].count("\n")+1,"pattern":pat})
result["checks"]["unfinished_code"]={"findings":markers}

# QDW migration simulation.
qdw=sqlite3.connect(":memory:")
qdw.executescript("""
PRAGMA foreign_keys=OFF;
CREATE TABLE route_definitions(route_id TEXT PRIMARY KEY,updated_at TEXT);
CREATE TABLE work_nodes(node_id TEXT PRIMARY KEY);
CREATE TABLE factory_runs(factory_run_id TEXT PRIMARY KEY);
CREATE TABLE cost_events(cost_event_id TEXT PRIMARY KEY);
CREATE TABLE external_systems(system_id TEXT PRIMARY KEY);
CREATE TABLE external_snapshots(snapshot_id TEXT PRIMARY KEY);
CREATE TABLE forge_leases(lease_id TEXT PRIMARY KEY,asset_id TEXT,version TEXT,capability TEXT,token TEXT,max_spend_usd REAL,created_at TEXT);
CREATE TABLE forge_invocation_certs(invocation_id TEXT,certificate_id TEXT,certificate_hash TEXT,status TEXT,created_at TEXT);
""")
qdw_error=None
try:qdw.executescript((ROOT/"overlays/qdw/migrations/0011_federation_finishline.sql").read_text())
except Exception as e:qdw_error=repr(e)
qdw_tables={x[0] for x in qdw.execute("SELECT name FROM sqlite_master WHERE type='table'")}
qdw_cols={x[1] for x in qdw.execute("PRAGMA table_info(route_definitions)")}
qdw.close()
result["checks"]["qdw_migration"]={
 "error":qdw_error,
 "retired_fake_lease_table":"forge_leases" not in qdw_tables,
 "fixed_cost_column":"fixed_request_cost_usd" in qdw_cols,
 "attempt_table":"federation_attempts_v2" in qdw_tables}

# Forge migration simulation.
forge=sqlite3.connect(":memory:")
forge.executescript("""
PRAGMA foreign_keys=OFF;
CREATE TABLE assets(asset_id TEXT,version TEXT,kind TEXT,name TEXT,status TEXT,manifest_json TEXT,manifest_hash TEXT,certificate_id TEXT,created_at TEXT,PRIMARY KEY(asset_id,version));
CREATE TABLE leases(lease_id TEXT PRIMARY KEY,capability TEXT,asset_id TEXT,version TEXT,calls_total INTEGER,calls_used INTEGER,max_spend_usd REAL,spend_usd REAL,allowed_operations_json TEXT,expires_at TEXT,status TEXT,token_hash TEXT,created_at TEXT);
CREATE TABLE invocations(invocation_id TEXT PRIMARY KEY,client_request_id TEXT UNIQUE,lease_id TEXT,capability TEXT,asset_id TEXT,version TEXT,input_hash TEXT,status TEXT,output_json TEXT,output_hash TEXT,cost_usd REAL,route_json TEXT,verification_certificate_id TEXT,failure TEXT,created_at TEXT,finished_at TEXT);
""")
forge_error=None
try:forge.executescript((ROOT/"overlays/qdw-forge/migrations/0001_finishline.sql").read_text())
except Exception as e:forge_error=repr(e)
forge_tables={x[0] for x in forge.execute("SELECT name FROM sqlite_master WHERE type='table'")}
forge_cols={x[1] for x in forge.execute("PRAGMA table_info(invocations)")}
forge.close()
result["checks"]["forge_migration"]={
 "error":forge_error,
 "verification_applications":"verification_applications" in forge_tables,
 "client_id":"client_id" in forge_cols,
 "billable_cost":"billable_cost_usd" in forge_cols}

# Reference executable suite.
env=os.environ.copy();env["PYTHONPATH"]=str(ROOT/"reference_finishline/src")
collect=subprocess.run([sys.executable,"-m","pytest","reference_finishline/tests","--collect-only","-q"],
                       cwd=ROOT,env=env,capture_output=True,text=True,timeout=180)
run=subprocess.run([sys.executable,"-m","pytest","reference_finishline/tests","-q"],
                   cwd=ROOT,env=env,capture_output=True,text=True,timeout=180)
(VAL/"reference_collect.stdout").write_text(collect.stdout)
(VAL/"reference_collect.stderr").write_text(collect.stderr)
(VAL/"reference_pytest.stdout").write_text(run.stdout)
(VAL/"reference_pytest.stderr").write_text(run.stderr)
test_count=sum(int(x) for x in re.findall(r":\s+(\d+)\s*$",collect.stdout,re.M))
result["checks"]["reference_tests"]={
 "collect_exit":collect.returncode,"test_exit":run.returncode,"collected":test_count,
 "collect_stdout_sha256":sha_bytes(collect.stdout.encode()),
 "test_stdout_sha256":sha_bytes(run.stdout.encode())}

# Native git transport limitation is a declared non-proof, not a pass.
git=subprocess.run(["git","ls-remote","https://github.com/prx0r/qdw.git","HEAD"],
                   capture_output=True,text=True,timeout=20)
result["source_transport"]={
 "native_git_exit":git.returncode,"stderr":git.stderr.strip(),
 "fallback_used_for_review":"GitHub connector exact-SHA source inspection"}

def failures():
    c=result["checks"]
    return (
      c["python_syntax"]["failures"] or c["json"]["failures"] or c["shell_syntax"]["failures"]
      or c["acceptance_hashes"]["failures"] or c["test_integrity"]["findings"]
      or c["unfinished_code"]["findings"] or c["qdw_migration"]["error"]
      or c["forge_migration"]["error"] or not c["qdw_migration"]["retired_fake_lease_table"]
      or not c["qdw_migration"]["fixed_cost_column"] or not c["forge_migration"]["verification_applications"]
      or c["reference_tests"]["collect_exit"]!=0 or c["reference_tests"]["test_exit"]!=0
    )

result["status"]="PASS" if not failures() else "FAIL"
result["proven_here"]=[
 "pack Python syntax","pack JSON parse","shell syntax","acceptance hash integrity",
 "test-tree anti-cheat scan","QDW 0011 synthetic migration","Forge 0001 synthetic migration",
 "independent semantic reference suite"]
result["not_proven_here"]=[
 "native clone/install of the five GitHub repositories",
 "post-overlay native repository suites",
 "real sibling HTTP V11",
 "QDW process-restart V11",
 "remote GitHub CI/branch protection"]
(VAL/"PACK_VALIDATION.json").write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
raise SystemExit(0 if result["status"]=="PASS" else 1)

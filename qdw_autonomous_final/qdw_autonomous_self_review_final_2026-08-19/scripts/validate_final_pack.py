#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
from hashlib import sha256
import ast, json, os, py_compile, re, shutil, subprocess, sys, tempfile, zipfile

ROOT=Path(__file__).resolve().parents[1]
VAL=ROOT/'validation'
VAL.mkdir(exist_ok=True)


def H(b:bytes)->str:return sha256(b).hexdigest()

def run(step_id,argv,env=None,timeout=180):
    e=os.environ.copy();e.update(env or {})
    p=subprocess.run(argv,cwd=ROOT,capture_output=True,timeout=timeout,env=e)
    op=VAL/f'{step_id}.stdout.log';ep=VAL/f'{step_id}.stderr.log'
    op.write_bytes(p.stdout);ep.write_bytes(p.stderr)
    return {
        'step_id':step_id,'argv':argv,'exit_code':p.returncode,
        'status':'PASS' if p.returncode==0 else 'FAIL',
        'stdout_path':str(op.relative_to(ROOT)),'stderr_path':str(ep.relative_to(ROOT)),
        'stdout_sha256':H(p.stdout),'stderr_sha256':H(p.stderr),
    }

errors=[]

# Syntax compile to a temp destination: never writes __pycache__ into the pack.
syntax=[]
with tempfile.TemporaryDirectory(prefix='qdw-pack-compile-') as td:
    td=Path(td)
    for i,p in enumerate(sorted(ROOT.rglob('*.py'))):
        if '__pycache__' in p.parts:continue
        try:
            py_compile.compile(str(p),cfile=str(td/f'{i}.pyc'),doraise=True)
            syntax.append({'path':str(p.relative_to(ROOT)),'ok':True})
        except Exception as exc:
            syntax.append({'path':str(p.relative_to(ROOT)),'ok':False,'error':repr(exc)})
            errors.append(f'syntax:{p.relative_to(ROOT)}:{exc}')

# JSON parse.
json_checks=[]
for p in sorted(ROOT.rglob('*.json')):
    if p.name in {'MANIFEST.json','VALIDATION_SUMMARY.json'}:continue
    try:
        json.loads(p.read_text(encoding='utf-8'))
        json_checks.append({'path':str(p.relative_to(ROOT)),'ok':True})
    except Exception as exc:
        json_checks.append({'path':str(p.relative_to(ROOT)),'ok':False,'error':repr(exc)})
        errors.append(f'json:{p.relative_to(ROOT)}:{exc}')

# Obvious fake-green patterns in reference/native test trees.
anti=[]
for base in [ROOT/'reference/tests',ROOT/'native_overlay/tests']:
    for p in sorted(base.rglob('test_*.py')):
        try:tree=ast.parse(p.read_text(encoding='utf-8'))
        except Exception as exc:
            anti.append({'path':str(p.relative_to(ROOT)),'line':0,'code':'PARSE','detail':repr(exc)});continue
        for n in ast.walk(tree):
            if isinstance(n,ast.Assert) and isinstance(n.test,ast.Constant) and n.test.value is True:
                anti.append({'path':str(p.relative_to(ROOT)),'line':n.lineno,'code':'ASSERT_TRUE'})
            if isinstance(n,ast.Call):
                try:fn=ast.unparse(n.func)
                except Exception:fn=''
                if fn in {'pytest.skip','pytest.xfail'}:
                    anti.append({'path':str(p.relative_to(ROOT)),'line':n.lineno,'code':'SKIP_XFAIL'})
            if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name.startswith('test_') and len(n.body)==1 and isinstance(n.body[0],ast.Pass):
                anti.append({'path':str(p.relative_to(ROOT)),'line':n.lineno,'code':'EMPTY_TEST'})
if anti:errors.append(f'anti_cheat:{len(anti)}')

# No actual implementation placeholders in production overlay/reference engine.
placeholder=[]
rx=re.compile(r'\b(?:TODO|FIXME|NotImplementedError)\b',re.I)
for base in [ROOT/'native_overlay/src',ROOT/'native_overlay/replacements',ROOT/'reference/src']:
    for p in base.rglob('*.py'):
        for i,line in enumerate(p.read_text(errors='replace').splitlines(),1):
            if rx.search(line):placeholder.append({'path':str(p.relative_to(ROOT)),'line':i,'text':line.strip()})
if placeholder:errors.append(f'production_placeholders:{len(placeholder)}')

# Reviewer/prompt/formula consistency.
manifests=[]
for p in sorted((ROOT/'manifests/reviewers').glob('*.json')):
    manifests.append(json.loads(p.read_text()))
ids=[m['contractor_id'] for m in manifests]
if len(ids)!=len(set(ids)):errors.append('duplicate_reviewer_ids')
missing_prompts=[]
for rid in ids:
    if not (ROOT/f'prompts/reviewers/{rid}.md').exists():missing_prompts.append(rid)
if missing_prompts:errors.append('missing_prompts:'+','.join(missing_prompts))
formula_refs=[];bad_formula_refs=[]
for p in sorted((ROOT/'manifests/formulas').glob('*.json')):
    d=json.loads(p.read_text())
    refs=[]
    refs.extend(d.get('reviewers',[]));refs.extend(d.get('always',[]));refs.extend(d.get('required_reviewers',[]))
    for n in d.get('nodes',[]):
        rid=n.get('reviewer_id') or n.get('contractor_id') or n.get('contractor') or n.get('reviewer')
        if rid:refs.append(rid)
    for stage in d.get('stages',[]):
        refs.extend(stage.get('reviewers',[]))
        rid=stage.get('reviewer') or stage.get('reviewer_id')
        if rid:refs.append(rid)
    for r in refs:
        r=r.split('@')[0];formula_refs.append(r)
        if r not in ids:bad_formula_refs.append((p.name,r))
if bad_formula_refs:errors.append('bad_formula_refs:'+repr(bad_formula_refs))

attacks=json.loads((ROOT/'attacks/ATTACK_CATALOG.json').read_text())
attack_ids=[a['attack_id'] for a in attacks]
if len(attack_ids)!=len(set(attack_ids)):errors.append('duplicate_attack_ids')

# Current review consistency.
cur=json.loads((ROOT/'current/CURRENT_REVIEW.json').read_text())
cur_findings=[f for m in cur.get('modules',[]) for f in m.get('findings',[])]
counts={s:sum(1 for f in cur_findings if f['severity']==s) for s in ['CRITICAL','HIGH','MEDIUM','LOW','INFO']}
if counts!=cur.get('counts'):errors.append(f'current_count_mismatch:{counts}!={cur.get("counts")}')

# Process-backed validation.
base_env={'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(ROOT/'reference/src'),'PYTEST_ADDOPTS':'-p no:cacheprovider'}
receipts=[]
receipts.append(run('reference-tests',[sys.executable,'-m','pytest','reference/tests','-q'],base_env))
receipts.append(run('reference-collect',[sys.executable,'-m','pytest','reference/tests','--collect-only','-q'],base_env))
receipts.append(run('review-modules',[sys.executable,'-m','qdw_review.cli','modules'],base_env))
receipts.append(run('installer-help',[sys.executable,'scripts/apply_native_overlay.py','--help'],{'PYTHONDONTWRITEBYTECODE':'1'}))
for r in receipts:
    if r['exit_code']!=0:errors.append(f'process:{r["step_id"]}:{r["exit_code"]}')

# Parse collected test count.
collect=(ROOT/receipts[1]['stdout_path']).read_text(errors='replace')
test_count=sum(int(x) for x in re.findall(r':\s*(\d+)\s*$',collect,re.M))

# Exercise internal review ZIP generation and integrity.
sample=ROOT/'current/SAMPLE_GENERATED_REVIEW_PACK.zip'
env=base_env.copy()
r=run('review-pack',[sys.executable,'-m','qdw_review.cli','pack','current/CURRENT_REVIEW.json','--out',str(sample.relative_to(ROOT))],env)
receipts.append(r)
if r['exit_code']!=0:errors.append('process:review-pack')
review_pack_integrity=None
if sample.exists():
    with zipfile.ZipFile(sample) as z:review_pack_integrity=z.testzip()
    if review_pack_integrity is not None:errors.append('sample_review_pack_crc:'+str(review_pack_integrity))
else:errors.append('sample_review_pack_missing')

# Shell/YAML not executable here; ensure final replacement CI and installer assets exist.
required=[
 'native_overlay/replacements/.github/workflows/ci.yml',
 'native_overlay/replacements/scripts/ci_release.py',
 'native_overlay/src/qdw/review/controller.py',
 'native_overlay/src/qdw/review/service.py',
 'native_overlay/src/qdw/review/pack.py',
 'native_overlay/src/qdw/review/worker.py',
 'native_overlay/src/qdw/proof/verification_service.py',
 'native_overlay/tests/integration/test_v10_real.py',
 'native_overlay/tests/contract/test_mcp_protocol_real.py',
 'native_overlay/tests/runtime/test_container_contract.py',
]
missing_required=[x for x in required if not (ROOT/x).exists()]
if missing_required:errors.append('missing_required:'+','.join(missing_required))

summary={
 'status':'PACK_VALIDATED' if not errors else 'PACK_VALIDATION_FAILED',
 'reviewed_qdw_head':'ab809c8e6b829374199eb49dc71cd6f499e4f7fb',
 'peer_review_counts':cur.get('counts'),
 'stats':{
   'python_files':len(syntax),'syntax_failures':sum(not x['ok'] for x in syntax),
   'json_files':len(json_checks),'json_failures':sum(not x['ok'] for x in json_checks),
   'anti_cheat_findings':len(anti),'production_placeholders':len(placeholder),
   'reviewer_manifests':len(manifests),'formula_reviewer_refs':len(formula_refs),
   'attacks':len(attacks),'current_findings':len(cur_findings),
   'reference_tests_collected':test_count,'process_receipts':len(receipts),
   'process_receipts_passed':sum(r['status']=='PASS' for r in receipts),
   'sample_review_pack_integrity':'PASS' if sample.exists() and review_pack_integrity is None else 'FAIL',
 },
 'process_receipts':receipts,
 'errors':errors,
 'explicitly_not_proven_here':[
   'the upstream QDW 132-test suite was independently executed in this artifact runtime',
   'the upstream QDW Docker container was independently booted in this artifact runtime',
   'a real Hermes worker was invoked here',
   'a GitHub Actions run for the reviewed SHA was independently proven successful',
   'the reviewed upstream SHA is REVIEW_CERTIFIED',
 ]
}
(ROOT/'SYNTAX_CHECK.json').write_text(json.dumps(syntax,indent=2))
(ROOT/'JSON_CHECK.json').write_text(json.dumps(json_checks,indent=2))
(ROOT/'ANTI_CHEAT_CHECK.json').write_text(json.dumps(anti,indent=2))
(ROOT/'VALIDATION_SUMMARY.json').write_text(json.dumps(summary,indent=2))
print(json.dumps(summary,indent=2))
raise SystemExit(0 if not errors else 1)

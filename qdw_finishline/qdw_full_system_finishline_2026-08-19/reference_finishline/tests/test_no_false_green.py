from pathlib import Path
import ast

def test_reference_has_no_local_fake_forge_named_client():
    src=Path(__file__).parents[1]/"src"
    names=[p.name for p in src.rglob("forge_client.py")]
    assert names==[]

def test_reference_tests_do_not_use_legacy_verification_boolean_dict():
    root=Path(__file__).parents[1]
    offenders=[]
    forbidden="pass"+"ed"
    for p in root.rglob("test_*.py"):
        if p.name=="test_no_false_green.py":
            continue
        tree=ast.parse(p.read_text())
        for node in ast.walk(tree):
            if isinstance(node,ast.Dict):
                for key in node.keys:
                    if isinstance(key,ast.Constant) and key.value==forbidden:
                        offenders.append(str(p))
    assert offenders==[]

def test_e2e_claim_requires_real_test_file_in_target_pack():
    target=Path(__file__).parents[2]/"lab/tests/e2e/test_full_federation_v11.py"
    assert target.exists()

from qdw_lab.repo import text

def test_verification_wire_has_no_passed_boolean():
    s=text("qdw-forge","src/qdw_forge/api.py")
    compact="".join(s.split())
    assert "passed:bool" not in compact
    assert "CertificateReference" in s

def test_idempotency_happens_after_authorization():
    s=text("qdw-forge","src/qdw_forge/invocation.py")
    pos_verify=s.find("leases.verify")
    pos_old=s.find("client_request_id")
    assert pos_verify!=-1 and pos_old!=-1 and pos_verify<pos_old, "lease auth must precede idempotency disclosure"

def test_invoke_permission_is_enforced():
    s=text("qdw-forge","src/qdw_forge/invocation.py")+text("qdw-forge","src/qdw_forge/leases.py")
    assert "operation" in s.lower() and "allowed_operations" in s

def test_asset_activation_does_not_rewrite_manifest_hash():
    s=text("qdw-forge","src/qdw_forge/store.py")
    # Correct implementation uses separate activation state and does not update manifest_json/hash in activate().
    block=s[s.find("def activate"):s.find("def candidates")]
    assert "manifest_json" not in block and "manifest_hash" not in block

def test_verification_application_is_idempotent():
    schema=text("qdw-forge","src/qdw_forge/db.py")
    assert "verification_applications" in schema or "applied_certificates" in schema
    assert "certificate_id" in schema

def test_forge_uses_numbered_migrations():
    from qdw_lab.repo import repo
    d=repo("qdw-forge")/"migrations"
    assert d.exists() and list(d.glob("[0-9][0-9][0-9][0-9]_*.sql"))

def test_forgejo_sync_paginates():
    s=text("qdw-forge","src/qdw_forge/forgejo.py")
    assert "page" in s and ("while" in s or "for page" in s)

def test_forgejo_manifest_is_commit_pinned():
    s=text("qdw-forge","src/qdw_forge/forgejo.py")
    assert "commit" in s.lower()
    assert "manifest_digest" in s or "content_hash" in s

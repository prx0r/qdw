import pytest
from qdw_forge.federation import CertificateReference,FederatedSubject,validate_for_invocation

class Inv:
    invocation_id="inv1";output_hash="oh"

def cert(**kw):
    d=dict(issuer_system="qdw",certificate_id="c",certificate_hash="sha256:c",
           subject=FederatedSubject(system="forge",object_type="invocation",object_id="inv1"),
           subject_output_digest="oh",policy_hash="sha256:p",status="VERIFIED")
    d.update(kw);return CertificateReference(**d)

def test_exact_invocation_binding():
    assert validate_for_invocation(cert(),Inv())

def test_wrong_invocation_rejected():
    with pytest.raises(ValueError):
        validate_for_invocation(cert(subject=FederatedSubject(system="forge",object_type="invocation",object_id="other")),Inv())

def test_wrong_output_rejected():
    with pytest.raises(ValueError):validate_for_invocation(cert(subject_output_digest="wrong"),Inv())

def test_no_pass_boolean_in_new_contract():
    assert "passed" not in CertificateReference.model_fields

import pytest
from qdw.federation.contracts import FederatedRef,ExternalInvocationOutcome,VerificationCertificateRef

def outcome():
    return ExternalInvocationOutcome(
      FederatedRef("forge","invocation","i",digest="sha256:i"),
      FederatedRef("forge","capability_asset","a",version="1",digest="sha256:a"),
      "SUCCEEDED_UNVERIFIED",{"ok":True},"sha256:o",.01,None)

def test_wire_certificate_is_exact():
    x=outcome()
    c=VerificationCertificateRef("qdw","c","sha256:c",x.invocation,"sha256:o","sha256:p","VERIFIED")
    assert c.subject.object_id=="i" and c.output_digest=="sha256:o"

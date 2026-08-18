from dataclasses import asdict
from qdw.core.verification.certificate import issue
from qdw.core.core import hash_object
def test_certificate_commits_artifacts():
    c,h=issue("run",["b","a"],["g"],"root")
    assert c.artifact_hashes==("a","b")
    assert h==hash_object(asdict(c))

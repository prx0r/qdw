import pytest
from qdw_review.certificate import ReviewCertificateBuilder

def report(sev=None):
    findings=[] if sev is None else [{
        "rule_id":"X","module_id":"m","severity":sev,"status":"OPEN",
        "title":"x","summary":"x","invariant":"x","evidence":[],"remediation":"x","acceptance_tests":[]
    }]
    return {
        "git_sha":"abc1234","git_dirty":False,"modules":[{"module_id":"m","version":"1","findings":findings}],
        "receipts":[{"status":"PASS"}]
    }

def test_review_certificate_rejects_blocker():
    b=ReviewCertificateBuilder()
    with pytest.raises(ValueError):
        b.issue(report("HIGH"),{"block_at":"HIGH","required_modules":[],"minimum_passing_receipts":0},
                attack_results=[],certifier_worker_id="reviewer")

def test_review_certificate_rejects_same_producer():
    b=ReviewCertificateBuilder()
    with pytest.raises(ValueError):
        b.issue(report(),{"block_at":"HIGH","required_modules":[],"minimum_passing_receipts":0},
                attack_results=[],certifier_worker_id="w",producer_worker_id="w")

def test_review_certificate_binds_attacks():
    b=ReviewCertificateBuilder()
    p={"block_at":"HIGH","required_modules":[],"minimum_passing_receipts":0,"required_attacks":["A01"]}
    with pytest.raises(ValueError):
        b.issue(report(),p,attack_results=[],certifier_worker_id="r")
    c=b.issue(report(),p,attack_results=[{"attack_id":"A01","status":"PASS"}],certifier_worker_id="r")
    assert b.verify_envelope(c)

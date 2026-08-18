"""Release proof cannot be vacuous and verification revalidates subjects."""

import sys

import pytest

from qdw.proof.certificate import BuildCertificateBuilder
from qdw.proof.runner import VerificationRunner


def test_empty_required_command_set_cannot_prove_release(tmp_path):
    runner=VerificationRunner(tmp_path/"runs")
    runner.run("release",[sys.executable,"-c","print('unrelated')"],cwd=tmp_path)
    artifact=tmp_path/"artifact.txt";artifact.write_text("x")
    builder=BuildCertificateBuilder(runner)
    with pytest.raises(ValueError):
        builder.issue(
            task_id="release",acceptance_spec_hash="sha256:real",
            required_commands=[],required_negative_tests=[],
            artifact_paths=[artifact],output_path=tmp_path/"cert.json"
        )

def test_mutated_certified_artifact_invalidates_certificate(tmp_path):
    runner=VerificationRunner(tmp_path/"runs")
    cmd=[sys.executable,"-c","print('verified')"]
    runner.run("release",cmd,cwd=tmp_path)
    artifact=tmp_path/"artifact.txt";artifact.write_text("before")
    builder=BuildCertificateBuilder(runner)
    cert_path=tmp_path/"cert.json"
    builder.issue(
        task_id="release",acceptance_spec_hash="sha256:real",
        required_commands=[cmd],required_negative_tests=[],
        artifact_paths=[artifact],output_path=cert_path
    )
    artifact.write_text("after")
    ok,_=builder.verify_certificate(cert_path)
    assert not ok

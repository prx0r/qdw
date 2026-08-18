from qdw.factories.fixtures.api import APIFactoryFixture

def test_real_api_fixture(tmp_path):
    fixture=APIFactoryFixture()
    artifact=fixture.generate(tmp_path/"good",broken=False)
    result=fixture.verify(artifact)
    assert result.passed
    assert result.status_code==200
    assert result.reason_code=="OK"
    assert len(result.artifact_hash)==64
    assert "app.py" in result.files

def test_broken_api_fixture_rejected(tmp_path):
    fixture=APIFactoryFixture()
    artifact=fixture.generate(tmp_path/"broken",broken=True)
    result=fixture.verify(artifact)
    assert not result.passed
    assert result.reason_code!="OK"

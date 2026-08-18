from qdw.sources.protocol import SourceResult

def test_source_error_not_empty():
    failed=SourceResult.failure("x","forum","timeout")
    empty=SourceResult.success("x","forum",[])
    assert failed.ok is False
    assert failed.error=="timeout"
    assert failed.items==()
    assert empty.ok is True
    assert empty.error is None
    assert empty.items==()
    assert failed != empty

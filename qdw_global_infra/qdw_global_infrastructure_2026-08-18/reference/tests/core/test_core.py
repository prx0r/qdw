from qdw.core.core import canonical_json,hash_object
def test_canonical_order():
    assert canonical_json({"b":1,"a":2})==canonical_json({"a":2,"b":1})
def test_hash_stable():
    assert hash_object({"x":[1,2]})==hash_object({"x":[1,2]})

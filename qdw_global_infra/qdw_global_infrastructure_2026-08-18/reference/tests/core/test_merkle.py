from qdw.core.ledger.merkle import merkle_root,inclusion_path,verify_inclusion
def test_inclusion():
    xs=[b"a",b"b",b"c",b"d",b"e"];root=merkle_root(xs)
    for i,x in enumerate(xs):
        assert verify_inclusion(x,i,len(xs),inclusion_path(xs,i),root)
def test_mutated_leaf_fails():
    xs=[b"a",b"b",b"c"];root=merkle_root(xs)
    assert not verify_inclusion(b"X",1,len(xs),inclusion_path(xs,1),root)

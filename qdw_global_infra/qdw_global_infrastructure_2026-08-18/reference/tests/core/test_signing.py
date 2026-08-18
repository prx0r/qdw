import pytest
cryptography=pytest.importorskip("cryptography")
from qdw.core.ledger.signing import generate_ed25519_keypair,sign_root,verify_root,SignedRoot
def test_sign_verify():
    k=generate_ed25519_keypair();s=sign_root(k,"00"*32)
    assert verify_root(s)
    bad=SignedRoot("11"*32,s.signature_b64,s.public_key_b64)
    assert not verify_root(bad)

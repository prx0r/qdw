from __future__ import annotations
import base64
from dataclasses import dataclass

@dataclass(frozen=True)
class SignedRoot:
    root_hex:str
    signature_b64:str
    public_key_b64:str
    algorithm:str="ed25519"

def generate_ed25519_keypair():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    return Ed25519PrivateKey.generate()

def sign_root(private_key,root_hex:str)->SignedRoot:
    from cryptography.hazmat.primitives.serialization import Encoding,PublicFormat
    sig=private_key.sign(bytes.fromhex(root_hex))
    pub=private_key.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw)
    return SignedRoot(root_hex,base64.b64encode(sig).decode(),base64.b64encode(pub).decode())

def verify_root(s:SignedRoot)->bool:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    try:
        pub=Ed25519PublicKey.from_public_bytes(base64.b64decode(s.public_key_b64))
        pub.verify(base64.b64decode(s.signature_b64),bytes.fromhex(s.root_hex))
        return True
    except Exception:
        return False

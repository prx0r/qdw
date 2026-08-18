"""Compatibility alias. Canonical authority is VerificationService."""
from qdw.proof.verification_service import VerificationService, Receipt
VerificationRunner = VerificationService
CommandReceipt = Receipt
__all__=["VerificationRunner","VerificationService","CommandReceipt","Receipt"]

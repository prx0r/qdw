"""Compatibility alias. No independent verification logic lives here."""
from qdw.proof.verification_service import VerificationService, Receipt
VerificationRunner = VerificationService
CommandReceipt = Receipt
__all__=["VerificationRunner","VerificationService","CommandReceipt","Receipt"]

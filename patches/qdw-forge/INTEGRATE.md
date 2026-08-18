# Forge integration patch

1. Add `federation.py` and `verification_v2.py`.
2. In `api.py`, replace:
   - `VerifyBody(certificate_id, passed)`
   with
   - `VerifyBody(certificate: CertificateReference)`.
3. Construct `InvocationVerificationService` in app state with an injected certificate resolver.
4. Replace `state().invocations.bind_verification(... passed=...)` with `state().verification.bind(...)`.
5. Keep the old endpoint only behind explicit legacy compatibility flag, and never enable it for QDW.
6. Add an invocation contract assertion: if lease pins asset/version, invocation must return the same pair.
7. Expose asset profiles/candidate metadata without making Forge's local `RouteDecision` globally authoritative.

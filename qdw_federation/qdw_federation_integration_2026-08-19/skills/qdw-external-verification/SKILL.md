# External Verification Skill

Use after a Forge or other external invocation.

Executor output cannot assert verification.

Required:
- exact external invocation ref;
- selected asset/version;
- output digest;
- QDW WorkNode/FactoryRun ref;
- verification policy hash;
- independent verifier results.

Issue VerificationCertificateRef bound to the exact invocation/output.
The foreign service may resolve it and project its own VERIFIED/REJECTED state.

Reject:
- certificate for another invocation;
- changed output digest;
- untrusted issuer;
- missing policy hash;
- caller-authored `passed=true`.

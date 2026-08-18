# Current QDW blockers

Release-level self-certification is blocked until at least:

- [ ] certificate script cannot certify empty requirements
- [ ] certificate verification revalidates artifacts/receipts/spec
- [ ] factory activation rejects unrelated gate/certificate evidence
- [ ] product release rejects unknown/unrelated certificates
- [ ] contractor versions immutable
- [ ] applied migrations checksum locked
- [ ] old migration 0002 no longer used for new schema additions
- [ ] state + provenance crash-consistent
- [ ] UNKNOWN economics not converted to 1/0
- [ ] posterior increments atomic
- [ ] persistent RouteRegistry wired
- [ ] QDWSystem composes global services
- [ ] real V10 factory execution E2E
- [ ] clean Docker build + boot + /health

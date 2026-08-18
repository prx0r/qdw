# Reviewer implementation checklist

- [ ] deterministic scanner works offline
- [ ] reviewer manifests immutable
- [ ] reviewer activation requires fixture evidence
- [ ] review run binds exact git SHA
- [ ] findings have stable fingerprints
- [ ] evidence includes content/receipt hashes
- [ ] semantic reviewers cannot self-certify
- [ ] red-team attacks have IDs and receipts
- [ ] suppressions are durable/attributed/expiring
- [ ] producer/certifier independence enforced
- [ ] review certificate binds policy/reviewer/attack sets
- [ ] review transition provenance atomic
- [ ] exact same regression tests run before/after fixes
- [ ] current QDW gets full self-review after integration

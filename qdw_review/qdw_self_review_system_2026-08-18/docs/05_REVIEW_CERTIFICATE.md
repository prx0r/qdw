# Review Certificate

A Review Certificate is separate from a build/factory certificate.

It answers:

> Was this exact repository subject independently reviewed under this exact review policy?

Required bindings:

```text
subject_git_sha
policy_hash
aggregate_report_hash
reviewer_set_hash
attack_set_hash
certifier_worker_id
issued_at
```

Release policy may require both:

```text
BuildCertificate
AND
ReviewCertificate
```

The build certificate proves artifacts/acceptance.
The review certificate proves independent architectural/adversarial scrutiny.

Neither is a blockchain requirement. Both can later be anchored in the existing QDW proof ledger.

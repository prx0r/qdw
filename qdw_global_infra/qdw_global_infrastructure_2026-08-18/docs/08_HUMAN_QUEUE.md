# Human Action Queue

Human/account-bound work must not become an ad-hoc chat pause.

States:

```text
REQUESTED
   ├─ APPROVED → COMPLETED
   ├─ DECLINED
   └─ CANCELLED
```

Every request has an idempotency key.

Examples:

- domain purchase approval
- provide/rotate credential
- accept external platform terms
- approve production release
- verify an email/account
- approve paid API budget
- decide between brand/domain candidates

Factories should continue independent work while a HumanAction is pending.

A human approval is an input to the workflow, not proof that the underlying artifact is technically correct.

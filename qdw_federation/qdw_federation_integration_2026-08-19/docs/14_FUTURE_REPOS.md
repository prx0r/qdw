# Contract for future QDW ecosystem repositories

Every new product should declare one of:

```text
ORACLE      produces observations/advisories
CAPABILITY  exposes invocable work
EXECUTOR    executes a QDW-selected route
SINK        publishes/deploys
INCUBATOR   experimental donor
VIEW        read-only projection
```

And explicitly list:
- canonical state it owns;
- canonical state it must never own;
- idempotency contract;
- failure semantics;
- freshness semantics;
- verification authority;
- cost accounting;
- protocol version;
- side-effect policy.

This prevents the ecosystem from accumulating five hidden schedulers again.

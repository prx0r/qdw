# Dell → QDW resource oracle

Dell has a mature, separate truth domain:

```text
Evidence
  -> Claims
  -> Assertions
  -> Offers
  -> endpoint/model/provider candidates
  -> DecisionService advisory
```

This should power QDW's StackOracle/HotSwap candidate acquisition rather than being reimplemented.

## What QDW caches

QDW stores immutable snapshots, not Dell's mutable truth database:

```text
ExternalSnapshot
 source_system=dell
 fetched_at
 source_revision/API version
 request_hash
 response_hash
 freshness_deadline
 raw artifact ref
```

Then normalized candidates refer back to that snapshot.

## Unknown behavior

Dell explicitly handles unknown hard constraints and unknown cost. Preserve this. Adapter code must not
convert absent cost, context, tool support, regions, automation permission, etc. to false/zero.

## Dell's recommendation

Store it as:

```text
DecisionAdvisory(authority="ADVISORY", adviser="dell")
```

QDW can compare whether HotSwap agreed/disagreed and later learn when Dell's advisory was useful without
making Dell the final route authority.

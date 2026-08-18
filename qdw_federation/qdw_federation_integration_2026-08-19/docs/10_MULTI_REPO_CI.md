# Multi-repo integration CI

Each repo keeps independent CI. Add one federation contract workflow in QDW.

## Matrix

```text
qdw @ pin
forge @ pin
gitgoblin @ pin
dell @ pin
sandbox @ pin (donor/compatibility only)
```

Integration workflow:
1. clone pins into sibling directories;
2. run each repo's own mandatory tests first;
3. launch service fixtures for GitGoblin/Dell/Forge;
4. run federation contract suite;
5. run one V10/V11 QDW flow;
6. archive request/response snapshots + receipts;
7. never update pins automatically on failure.

## Compatibility policy

External APIs use semver-ish protocol version plus capability negotiation.

A breaking integration should fail with:
`INCOMPATIBLE_PROTOCOL`

not silently fall back to a guessed legacy shape.

## Pin advancement

A bot/agent may propose updated pins. It must:
- discover new HEADs;
- compare protocol surface;
- run federation suite;
- output compatibility report;
- update pin PR only after PASS.

No blind "latest main" in production releases.

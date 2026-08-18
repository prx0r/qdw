# Outcomes and Learning

Building a product is not success.

After release, ingest real OutcomeEvents:

- health/uptime
- searches/API calls
- users/activation
- retention
- revenue
- variable cost
- support burden
- errors
- conversion
- data growth
- strategic value proxies

Adapters can pull from PostHog, Plausible, billing systems or QDW-owned telemetry.

Outcome events point to Product IDs. Product IDs point back to Factory Genome, build run, certificate,
idea and opportunity.

This gives QDW legitimate training/replay data:

```text
decision-time features
+ build recipe
+ actual build cost
+ later outcomes
```

Do not train a predictive allocator until enough independent outcome windows exist.

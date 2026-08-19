# QDW as Compute/Economic Operating System

*The vision: QDW prices verified outcomes, not tokens.*

---

## The Core Insight

QDW shouldn't just route to models. It should price **verified outcomes**.

The cost isn't just inference. It's:

```
expected_cost_to_verified_completion =
    inference_cost
  + expected_retry_cost
  + verification_cost
  + repair_cost
  + orchestration_cost
```

## The Key Shift

| Before | After |
|--------|-------|
| "What model should I use?" | "What's the cheapest way to get a verified result?" |
| Cost = $0.005/token | Cost = $4.82 for a verified SaaS MVP |
| Marketplace = model routing | Marketplace = verified implementation contracts |

## How It Works

Suppose you tell QDW: "Build a basic hosted SaaS with authentication, Stripe, dashboard, API and tests."

QDW decomposes it and for each node has historical records:

```
task_cell = frontend/react/dashboard

model: kimi-k2-x
  mean cost: $0.18
  verified success: 81%
  mean retries: 0.31

model: claude-x
  mean cost: $0.71
  verified success: 96%
  mean retries: 0.05
```

QDW calculates:

```
expected_cost_to_verified_completion =
    inference_cost
  + expected_retry_cost
  + verification_cost
  + repair_cost
  + orchestration_cost
```

So perhaps:

```
cheap model:
  $0.18 raw
  $0.34 expected verified completion

expensive model:
  $0.71 raw
  $0.76 expected verified completion
```

Cheap wins.

But for architecture:

```
cheap model:
  $0.12 raw
  $1.42 expected verified completion

frontier model:
  $0.54 raw
  $0.58 expected verified completion
```

Frontier wins.

## The Marketplace

Publish a BUILD REQUEST:

```yaml
artifact: web SaaS MVP
acceptance: 87 frozen requirements
maximum: $10
deadline: 2 hours
required_proof: QDW V0-V10
minimum_reputation: 0.92
```

Executors respond:

```
Factory A: $4.40, P(success): 92%, ETA: 34 min
Factory B: $2.80, P(success): 74%, ETA: 20 min
Agent C:   $6.10, P(success): 97%, ETA: 48 min
```

QDW calculates risk-adjusted expected cost, selects one, Forge leases the capability, executor works, QDW independently verifies.

## The Economic Primitive

The commodity isn't tokens. It's a **verified implementation satisfying contract X**.

```
risk_adjusted_expected_cost = price × (1 / P(success))
```

Factory A: $5 / 0.92 = $5.43 expected
Factory B: $3 / 0.74 = $4.05 expected

Factory B wins despite lower P(success).

## The Moat

> "I have a workflow that converts $2.30 of compute into something people will pay $5 for."

That's operational knowledge. It compounds. Every successful build makes the next one cheaper.

An agent can exploit the entire routing infrastructure internally:

```
fullstack_mvp_factory v17

Internally:
  planner → QDW router → free Kimi / cheap Mimo / OpenRouter promo
                        → expensive reasoning / specialist coding
                        → verifier
```

Factory owner charges $5. Actual inference bill $2.30. Margin $2.70. You save $4.

That creates a real reason for an agent/factory marketplace.

## Moltwork's Role

- Settlement for verified outcomes (not metered tokens)
- Factory revenue tracking
- Cost-per-verified-success accounting
- Reputation systems for factories

## The Architecture

```
QDW (authority)
  ↓
R2-Router (joint model+budget routing)
  ↓
RouteLLM (smart routing)
  ↓
HotSwap (policy: quality floor, free/paid, quota)
  ↓
LiteLLM (execution: 3,040 models, 14 strategies)
  ↓
Dell (intelligence: 44 sources, 604 free models)
  ↓
GitGoblin (frontier intelligence)
  ↓
Forge (capability execution)
  ↓
Moltwork (settlement for verified outcomes)
```

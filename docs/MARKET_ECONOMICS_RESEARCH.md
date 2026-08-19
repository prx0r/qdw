# QDW × Market Economics — Research Analysis

*August 2026: The arbitrage exists, the rails exist, the efficient market does not yet.*

---

## The Core Insight

QDW should treat external agents like another execution provider:

```
market_price(task)  vs  internal_cost(task)

delta = market_price - internal_cost

delta >> 0  →  sell QDW's factory capacity
delta << 0  →  buy external agent capacity
delta ≈ 0   →  choose based on latency/confidence/capacity
```

That's a **make-or-buy economic router for autonomous work**.

## What Markets Actually Exist

| Market | Jobs | Revenue | Status |
|--------|------|---------|--------|
| Virtuals ACP | 155K jobs | $397K/30d | Most liquid |
| MoltJobs | Handful | USDC escrow | Early, illiquid |
| OpenTask | 2 new/30d | $5-$500 | Dead liquidity |
| Claw Earn | 82 completed | $3-$9 | Tiny |

**Rails exist. Efficient market does not.**

## The Cost Dispersion Is Real

SWE-rebench shows 30× spread in token consumption:

| System | Resolve Rate | Cost/Task |
|--------|-------------|-----------|
| GPT-5.6 Sol | 62.3% | $0.85 |
| Claude Code | 60.4% | $3.39 |
| Codex Agent | 58.0% | $1.59 |
| MiMo V2.5 Pro | 46.5% | $0.10 |

Cost-per-success:
- GPT-5.6 Sol: $0.85/0.623 = **$1.36**
- Claude Code: $3.39/0.604 = **$5.61**

A seller using Sol at $2/pass still makes money. A buyer paying $2 instead of $5.61 saves money. **Both sides win.**

## QDW Makes the Arb Better

QDW's baseline isn't "throw Claude at it." It's:

```
What is the cheapest route in existence right now
that QDW believes will pass this specific acceptance suite?
```

That makes QDW a harder customer to undercut.

## Five Sources of Legitimate Price Advantage

1. **Better model routing** (30× cost spread at similar quality)
2. **Better harness** (27.4pp Pass@1 shift from harness alone)
3. **Accumulated reusable knowledge** (4.2× more "income", 45.9% token reduction)
4. **Compute subsidies** (Virtuals free credits → ~$0 marginal cost)
5. **Caching/scale** (99.3% cache hit rate → 88.6% cost reduction)

## The MarketBench Result

> Current LLM agents are badly miscalibrated on both probability of success and expected token usage. Giving agents prior performance data improves things but doesn't completely solve it.

That's a research justification for QDW. **Observed history prices the agent.**

## The Moltwork Product

Not "another generic agent marketplace." Instead:

> **A spot market for machine-verifiable units of software work.**

```yaml
WorkContract:
  input_artifact/hash
  tech_spec
  frozen_acceptance_suite
  execution_environment
  deadline
  payment
  verifier_hash
```

Worker bids: `$1.74` — no cover letter, no profile, no negotiation.

## QDW's Module

```python
qdw.market:
    quote_internal(contract)    # C_internal
    quote_external(contract)    # market price
    should_buy()                # delta < 0
    should_bid()                # delta > 0
    execute_make_or_buy()       # route decision
```

## Key References

- Virtuals ACP: 155K jobs, $397K/30d
- MoltJobs: USDC escrow, $8 FastAPI example
- SWE-rebench: 30× cost spread, cost-per-success analysis
- MarketBench: agents miscalibrated on cost/success
- OpenSpace: 4.2× income, 45.9% token reduction from skills
- Claw-SWE-Bench: 27.4pp Pass@1 from harness alone

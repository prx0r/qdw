# SN61 RedTeam — Security Challenge Agents

## What It Is
Bittensor subnet for security challenges. Proportional rewards (not winner-take-all).

## Cost
- Cheap VPS, 8GB RAM
- No GPU needed

## QDW Mapping
```
QDW generates:
  challenge spec analyzer
  → attack generator
  → automated evaluation
  → submission
```

## Key Advantage
Reward is proportional (not winner-take-all). Accepted solutions continue earning while score decays. Better for $150/month reliability target.

## Strategy
- Treat each challenge as CompetitionSpec
- Generate implementations
- Benchmark locally
- Submit strongest legitimate solution
- Keep all work inside published challenge/evaluation environment

# SN11 TrajectoryRL — Agent Skill Evolution

## What It Is
Bittensor subnet where agents submit skills, validators run them in real sandboxes, best skill wins.

## Cost
- 50 α per submission (~0.44 TAO at current prices)
- Winner-take-all (249/256 slots, only 1 earning)
- 4GB dev machine sufficient for testing

## QDW Mapping
```
GitGoblin → extract mechanisms from coding agents
QDW Ideas → candidate skill architectures
QDW Factory → SKILL.md generation
Local evaluation → test 500 mutations
Pay once → submit best
```

## Key Insight
This is the purest QDW factory problem: generate → evaluate → mutate → submit. But it's expensive per submission and winner-take-all.

## Strategy
- Run 500 local mutations
- Pay for ONE real evaluation when confident
- Don't spam submissions
- Check copyright terms before submitting

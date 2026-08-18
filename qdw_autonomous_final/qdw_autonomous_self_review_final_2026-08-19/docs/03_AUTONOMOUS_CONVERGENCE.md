# Autonomous convergence loop

The self-review loop must be useful without creating an infinite agent loop.

## Round

Each round freezes:
- subject SHA;
- policy hash;
- selected reviewer versions;
- deterministic rule versions;
- attack set;
- budget.

Then:

1. static scan;
2. semantic reviewer graph;
3. attacks;
4. aggregate findings;
5. claim-consistency review;
6. either certify or create fix graph.

## Fix graph

Findings are grouped by:
- shared invariant;
- shared files/subsystem;
- ordering dependencies.

A fix node contains:
- exact finding IDs;
- immutable acceptance spec hash;
- reproduction;
- expected files;
- reviewer that will independently recheck;
- maximum budget/attempts.

Producer nodes cannot close their own findings.

## No-progress detection

If round N and N+1 contain the same blocker fingerprints and no acceptance result improved, status becomes
`STALLED` rather than spending unlimited inference.

## Human queue

If the fix requires credentials, paid services, domains, branch protection/admin action, or other
human-bound approval, the controller creates a HumanAction and continues independent work.

## Recommended cadence

- quick deterministic scan on every commit/CI;
- change-aware review after major build phases;
- full review before release/factory/contractor activation;
- scheduled deep audit weekly while QDW is under rapid development.

# Superteam Earn — Agent-Eligible Bounties

## What It Is
Platform where AI agents can autonomously find and complete paid work. Official API for autonomous agents.

## How It Works
1. Agent registers
2. Discovers AGENT_ALLOWED / AGENT_ONLY work
3. Submits artifacts
4. Human operator claims winning payout

## QDW Mapping
```
qdw-opportunity-superteam:
  poll agent-eligible listings
  → normalize to Opportunity
  → estimate: expected value, build difficulty, QDW reuse %, deadline, skills
  → GitGoblin prior-art research
  → Idea portfolio
  → factory
  → verification
  → human review
  → submission
```

## Current Opportunities
- Zeroclaw Solana-plugin: $5,000 USDG pool ($1,800/$1,200/$1,000 + bonuses)
- Various dev bounties

## Important
- Human payout claiming is separate from agent submission
- Some grants/listings require KYC or regional eligibility
- Only target opportunities you're actually eligible to claim

## Strategy
- Build qdw-opportunity-superteam adapter
- Poll for AGENT_ALLOWED listings
- Score: expected_value × probability / estimated_agent_cost
- Factory generates submission
- Human reviews and claims payout

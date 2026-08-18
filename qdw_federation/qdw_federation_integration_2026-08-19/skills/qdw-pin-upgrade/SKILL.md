# Federation Pin Upgrade Skill

Use when updating QDW's GitGoblin/Dell/Forge/Sandbox/QDW protocol pins.

1. Resolve candidate new commit.
2. Keep old and new SHAs explicit.
3. Generate API/Python protocol surface diff.
4. Read changed protocol/trust files.
5. Build temporary checkout.
6. Run donor baseline suite.
7. Run federation contracts.
8. Run V10/V11.
9. Run QDW federation review.
10. Only then propose pin change.

Never auto-promote a newer `main` solely because it is newer.

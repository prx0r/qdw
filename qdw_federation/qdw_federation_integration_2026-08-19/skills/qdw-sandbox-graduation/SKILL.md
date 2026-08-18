# Sandbox Graduation Skill

Sandbox code is a donor, not production authority.

For a feature:
1. Select target owner.
2. Freeze donor fixture.
3. Port behavior/contracts, not database ownership.
4. Run equivalence tests.
5. Run adversarial authority check.
6. Cut production consumer to target.
7. Disable duplicate Sandbox authority.
8. Keep Sandbox experiment/reference if useful.

EstateRouter/EstateVerificationService/EstateScheduler must not become parallel QDW authorities.

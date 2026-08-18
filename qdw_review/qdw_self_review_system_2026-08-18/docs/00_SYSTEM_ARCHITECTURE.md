# QDW Self-Review Architecture

The review system is not a chatbot prompt. It is a first-class Factory OS workflow.

```text
              git SHA / changed paths / policy
                         |
                         v
                 REVIEW RUN (canonical)
                         |
             +-----------+-----------+
             |                       |
             v                       v
      deterministic scan        semantic reviewers
             |                 (bounded contractors)
             +-----------+-----------+
                         |
                         v
                 typed FINDINGS
            evidence / severity / tests
                         |
                +--------+--------+
                |                 |
                v                 v
         dynamic verifier       RED TEAM
       real process receipts   attack receipts
                |                 |
                +--------+--------+
                         v
                CLAIM CONSISTENCY
             docs/comments vs proof
                         |
                         v
              INDEPENDENT CERTIFIER
                         |
              +----------+----------+
              |                     |
              v                     v
       REVIEW_CERTIFIED       REVIEW_REJECTED
```

## Canonical rules

- Deterministic static checks may create findings directly.
- LLM/agent reviewers may create semantic findings, but they do not create verified PASS evidence.
- Dynamic claims require command receipts.
- A reviewer definition is immutable by version.
- Producer and release certifier are independent where policy requires.
- Findings have stable fingerprints across commits.
- A finding can become FIXED and later REGRESSION; history is never overwritten.
- Suppressions are explicit, attributed and time-bounded.
- Review certificate binds exact Git SHA + policy hash + reviewer set + attack set.
- Review output never replaces normal QDW verification. It aggregates and adversarially examines it.

## Why this reduces external back-and-forth

Before:
```text
agent builds -> user asks ChatGPT -> peer review -> agent fixes -> repeat
```

After:
```text
agent builds
   -> qdw review change-aware
   -> deterministic findings
   -> targeted reviewers
   -> red-team attacks
   -> fix plan
   -> rerun exact frozen tests
   -> independent review certificate
```

External review remains useful for changing the reviewer system itself, but ordinary architecture regression
should become internal infrastructure.

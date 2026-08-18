# Startup Radar + Opportunity Ideation

## Startup Radar

Store events, not a single company score:

- launched
- accelerator batch
- funding
- acquisition
- shutdown/inactive
- hiring
- product shift
- open-source release
- repository acceleration

The current seed adapter uses `yc-oss/api`. Add other legal/public sources through the same source contract.

## Idea generation

Recent research is useful but warns against treating LLM ideation as automatically diverse or correct.
A 2026 product-idea experiment found LLM ideas strong on predicted purchase intent but more similar / less
novel as a pool. Therefore QDW should deliberately reward problem-space diversity and preserve rejected ideas.

Use deterministic opportunity operators first:

```text
PAIN × NEW_CAPABILITY
PAIN × LOWER_COST
EXPENSIVE_API × OPEN_SOURCE_PRIMITIVE
PUBLIC_DATA × NO_CLEAN_API
COUNTRY_GAP × EXISTING_PRODUCT
REPEATED_WORKAROUND × VERIFIABLE_AUTOMATION
OLD_REJECTION × ASSUMPTION_CHANGED
```

LLMs can synthesize names/narratives/architectures after the join; they should not invent the evidence.

## Startup review

DIALECTIC is relevant because it separates factual collection from arguments for/against a startup and
iterative critique. QDW's review pipeline implements the same important separation structurally:

`DISCOVERY → EVIDENCE → ADVERSARIAL → PORTFOLIO → ARCHITECTURE → BUILD_READY`.

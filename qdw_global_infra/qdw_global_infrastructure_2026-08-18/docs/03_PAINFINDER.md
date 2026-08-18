# Painfinder

Painfinder is evidence collection, not an LLM startup-idea prompt.

## Source contract

Each source returns:

```text
SourceResult
  ok
  source_id
  source_family
  items[]
  error
  observed_at
  context
```

Three distinct states:

```text
ERROR       source failed
OK_EMPTY    source worked and returned no results
OK          source worked and returned item(s)
```

All are persistable.

## Candidate source families

- GitHub issues/discussions via Gitgoblin or dedicated adapter
- Hacker News / Ask HN
- Stack Exchange
- public feedback boards/forums
- public blogs/RSS
- properly authorized Reddit/other community adapters
- product feedback systems
- QDW products' own feedback

## Pain model

Store the raw observation first. Then derive:

- problem text
- workaround
- recurrence
- intensity
- willingness-to-pay hint
- machine solvability
- independent verifiability
- source family
- cluster

Do not let one viral post equal 100 independent users.

## OpenCoven inspiration

OpenCoven Feedback already demonstrates an OSS feedback product with automatic duplicate detection,
summaries, external feedback extraction and an MCP server. QDW should borrow those product primitives,
while maintaining its own evidence/provenance model.

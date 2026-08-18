# Idea Genome, Library and Cemetery

## Identity

An idea fingerprint is based on:

- problem key
- solution key
- customer
- product form

Names/domains can change without creating a new underlying idea.

## Relations

Use explicit relations:

- `derived_from`
- `inspired_by`
- `reimplements`
- `same_problem_new_country`
- `same_problem_new_factory`
- `supersedes`
- `analogous_to`

## Cemetery

Never delete a rejected idea.

Store:

- rejection reason
- decision-time assumptions
- revisit triggers
- next review time
- later revival evidence

Example:

```text
Rejected: TTS cost too high
Assumption: cost > target
Trigger: capability=TTS and cost_below=target
```

A Watch trigger can flag the idea for re-evaluation. It must not automatically revive/build it.

## Cross-factory inspiration

`IdeaLibrary.inspiration(target_form)` surfaces unused ideas from other product forms.

An API problem can be reimplemented as an app, agent, directory or connector while keeping the same
problem lineage.

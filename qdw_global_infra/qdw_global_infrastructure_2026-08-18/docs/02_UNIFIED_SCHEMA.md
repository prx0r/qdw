# Unified Schema

The reference code extends the existing Factory OS `schema.sql` rather than creating one database per product.

## World layer

`source_connectors`
→ `observations`
→ `claims`
→ `entities`
↔ `relations`

This is the only layer allowed to state what was observed externally.

## Intelligence layer

`pain_observations`
→ `pain_clusters`

`startup_events`
→ `entities(kind=company)`

`capabilities`
→ `resources`
→ `resource_measurements`

All three use World IDs and evidence.

## Opportunity / Idea layer

`opportunities_global`
→ `opportunity_evidence`

`ideas`
→ `idea_relations`
→ `idea_decisions`
→ `cemetery_entries`

An opportunity freezes the evidence and features available at decision time.
An idea is a reusable solution hypothesis attached to that opportunity/problem.

## Execution layer

Existing Factory OS:

`factory_definitions`
→ `factory_runs`
→ `work_graphs`
→ `work_nodes`
→ `artifacts`
→ `gate_results`
→ `certificates`

Contractors refer directly to `factory_runs` / `work_nodes`.
Human actions can also refer directly to them.

## Product layer

`products`
→ `factory_genomes`
→ `domains`
→ `publications`
→ `outcome_events`

This lets the system ask:

> Which opportunity features, factory version, contractors, routes and stacks produced products
> that later generated real usage/value at what total cost?

without reconstructing history from Markdown.

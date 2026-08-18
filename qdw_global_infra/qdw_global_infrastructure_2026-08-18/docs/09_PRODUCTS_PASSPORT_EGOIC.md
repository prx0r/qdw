# Products, Passports and Egoic

The Product Registry is the durable record. Egoic is only a view.

## Product Passport

Generated from canonical tables:

- originating idea/opportunity
- factory/version
- build run
- certificate
- domains/repository/deployment
- factory genome
- publications
- outcomes

## Factory Genome

Capture the production recipe:

- factory/version
- contractor versions
- route/stack choices
- verification policy
- distribution policy

This supports later questions like:

> Which contractor combination lowers release failures?
> Which stack choices correlate with lower cost?
> Which factory versions produce retained usage?

## Egoic

The reference contains a minimal static portfolio generator. Production can later use a richer frontend,
but it should always be generated from Product Registry data rather than hand-maintained portfolio Markdown.

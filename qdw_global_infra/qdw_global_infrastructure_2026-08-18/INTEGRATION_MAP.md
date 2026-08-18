# Integration map into a real QDW checkout

Copy/adapt these modules into the existing QDW `src/qdw/` tree:

```text
reference/src/qdw/world          -> src/qdw/world
reference/src/qdw/sources        -> src/qdw/sources
reference/src/qdw/intelligence   -> src/qdw/intelligence
reference/src/qdw/ideas          -> src/qdw/ideas
reference/src/qdw/human          -> src/qdw/human
reference/src/qdw/contractors    -> src/qdw/contractors
reference/src/qdw/products       -> src/qdw/products
reference/src/qdw/publishing     -> src/qdw/publishing
reference/src/qdw/watch          -> src/qdw/watch
reference/src/qdw/catalog        -> src/qdw/catalog
reference/src/qdw/proof          -> src/qdw/proof
reference/src/qdw/system.py      -> merge into existing composition root
```

Do **not** blindly replace `src/qdw/core`. The copy in this pack exists so the reference implementation
can run independently and so old Factory OS tests can be replayed. The real QDW should retain its current
validated core and apply the global schema as its next migration.

Copy:
- `manifests/contractors/`
- `manifests/distributions/`
- `schemas/`
- relevant tests

Gitgoblin: implement only the `GitgoblinClient` adapter against the separate Gitgoblin product.

# QDW federation finish-line lab

This lab is intentionally independent from the five source repositories.

## Environments

### 1. Source-regression environment

Requires only cloned repos.

```bash
export QDW_WORKTREES=$PWD/worktrees
pytest lab/tests/source -q
```

Against the reviewed current heads this suite is expected to be RED in known places. After repair it must be green.

### 2. Deterministic protocol environment

Starts local deterministic Forgejo/capability/certificate fixtures plus the real cloned service apps.

No public network or API credits are required.

### 3. Full sibling-service V11

Required environment variables:

```text
QDW_URL
FORGE_URL
GITGOBLIN_URL
DELL_URL
FORGEJO_URL
```

The test uses only public service protocols. It is forbidden to import `qdw_forge` into QDW's process or to access
another service's SQLite file.

## Why a separate package?

Tests inside QDW can accidentally import QDW's own fake clients and pass. This package lives outside every source
repository and treats each service as hostile/independent.

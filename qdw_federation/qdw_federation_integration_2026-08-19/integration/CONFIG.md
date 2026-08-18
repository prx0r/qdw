# Configuration

Recommended QDW settings:

```text
QDW_GITGOBLIN_URL=http://127.0.0.1:8111
QDW_DELL_URL=http://127.0.0.1:8112
QDW_FORGE_URL=http://127.0.0.1:8113

QDW_GITGOBLIN_PROTOCOL=qdw-federation-observation/1
QDW_DELL_PROTOCOL=qdw-federation-resource/1
QDW_FORGE_PROTOCOL=qdw-federation-capability/1

QDW_DELL_STALE_SECONDS=3600
QDW_GITGOBLIN_STALE_SECONDS=21600
QDW_FORGE_STALE_SECONDS=300
```

Credentials:
- use environment/secret provider;
- never store tokens in WorkNode payloads;
- never serialize lease tokens into public artifacts;
- redact Authorization headers from receipts.

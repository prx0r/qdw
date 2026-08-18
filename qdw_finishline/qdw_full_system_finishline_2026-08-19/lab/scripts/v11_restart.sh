#!/usr/bin/env bash
set -euo pipefail
: "${QDW_URL:?}"
: "${QDW_RESTART_COMMAND:?command to restart only QDW while preserving data}"
AID="restart-$(python - <<'PY'
import uuid;print(uuid.uuid4().hex)
PY
)"
BODY=$(printf '{"attempt_id":"%s","capability":"fixture.echo","arguments":{"restart":true},"max_spend_usd":1,"debug_stop_after":"SUCCEEDED_UNVERIFIED"}' "$AID")
curl -fsS -H 'content-type: application/json' -d "$BODY" "$QDW_URL/v1/federation/execute" > /tmp/qdw-before-restart.json
python - <<'PY' /tmp/qdw-before-restart.json
import json,sys
x=json.load(open(sys.argv[1]));assert x["state"]=="SUCCEEDED_UNVERIFIED",x
PY
bash -lc "$QDW_RESTART_COMMAND"
for _ in $(seq 1 60); do
  curl -fsS "$QDW_URL/health" >/dev/null && break
  sleep 1
done
curl -fsS -H 'content-type: application/json' -d "{\"attempt_id\":\"$AID\"}" "$QDW_URL/v1/federation/resume" > /tmp/qdw-after-restart.json
python - <<'PY' /tmp/qdw-before-restart.json /tmp/qdw-after-restart.json
import json,sys
a=json.load(open(sys.argv[1]));b=json.load(open(sys.argv[2]))
assert b["state"]=="COMMITTED",b
assert b["external_invocation_id"]==a["external_invocation_id"],(a,b)
assert b["cost_event_id"] and b["learning_event_id"],b
PY
echo "V11 restart recovery PASS: $AID"

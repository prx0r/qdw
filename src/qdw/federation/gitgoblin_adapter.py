"""GitGoblin → QDW federation adapter.

Normalizes GitGoblin observation batches into QDW ExternalSnapshot.
Converts snapshots to SourceResult for QDW WorldStore ingestion.
"""

from __future__ import annotations

from qdw.core import hash_object, utc_now
from qdw.sources.protocol import SourceResult
from .contracts import ExternalSnapshot, ExternalStatus


class GitGoblinFederationAdapter:
    system_id = "gitgoblin"
    protocol_version = "qdw-federation-observation/1"
    adapter_version = "1.0.0"

    def normalize(self, raw: dict, request: dict | None = None) -> ExternalSnapshot:
        schema = raw.get("schema_version")
        if schema != self.protocol_version:
            return ExternalSnapshot(
                "gitgoblin", "frontier_observations", str(schema or "unknown"),
                hash_object(request or {}), hash_object(raw),
                ExternalStatus.INCOMPATIBLE_PROTOCOL,
                utc_now(), {"observations": [], "opportunity_proposals": []},
                adapter_version=self.adapter_version,
                warnings=(f"expected {self.protocol_version}, got {schema}",),
            )
        observations = list(raw.get("observations") or [])
        proposals = list(raw.get("opportunity_proposals") or [])
        status = ExternalStatus.OK if observations or proposals else ExternalStatus.OK_EMPTY
        return ExternalSnapshot(
            "gitgoblin", "frontier_observations", schema,
            hash_object(request or {}), hash_object(raw),
            status, str(raw.get("generated_at") or utc_now()),
            {"cursor": raw.get("cursor"), "batch_digest": raw.get("batch_digest"),
             "observations": observations, "opportunity_proposals": proposals},
            source_revision=raw.get("source_revision"),
            adapter_version=self.adapter_version,
        )

    def to_source_result(self, snapshot: ExternalSnapshot) -> SourceResult:
        if snapshot.status in {
            ExternalStatus.UNAVAILABLE, ExternalStatus.FAILED,
            ExternalStatus.INCOMPATIBLE_PROTOCOL, ExternalStatus.UNAUTHORIZED,
        }:
            return SourceResult.failure(
                "federation:gitgoblin", "technical_frontier", snapshot.status.value,
                observed_at=snapshot.fetched_at,
                context={"snapshot_digest": snapshot.response_digest, "warnings": list(snapshot.warnings)},
            )
        items = []
        for o in snapshot.normalized.get("observations", []):
            ref = o.get("external_ref") or {}
            items.append({
                "id": ref.get("object_id"),
                "external_id": ref.get("object_id"),
                "federated_ref": ref,
                "entity_key": o.get("entity_key"),
                "metric": o.get("metric"),
                "value": o.get("value"),
                "unit": o.get("unit"),
                "dimensions": o.get("dimensions") or {},
                "evidence": {
                    "source_system": "gitgoblin",
                    "authority": "OBSERVATION",
                    "content_digest": o.get("evidence_digest"),
                    "confidence": o.get("confidence"),
                    "source_family": o.get("source_family"),
                },
            })
        return SourceResult.success(
            "federation:gitgoblin", "technical_frontier", items,
            observed_at=snapshot.fetched_at,
            context={"snapshot_digest": snapshot.response_digest,
                     "cursor": snapshot.normalized.get("cursor"),
                     "batch_digest": snapshot.normalized.get("batch_digest")},
        )

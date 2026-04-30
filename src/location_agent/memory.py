from __future__ import annotations

import json
import uuid
from dataclasses import replace
from pathlib import Path
from typing import Any

from location_agent.models import (
    DEFAULT_GUESS_THRESHOLD,
    DEFAULT_OUTLIER_FACTOR,
    DEFAULT_TOLERANCE,
    SCHEMA_VERSION,
    VALID_CONCEPT_KINDS,
    ConceptNode,
    EvidenceRecord,
    GraphEdge,
    LabelNameError,
    LabelNode,
    LocationModel,
    LocationRecord,
    NormalizedObservation,
    ObservationBundle,
    RenameRecord,
    SensorBinding,
    SensorObservation,
    distance_to_confidence,
    label_lookup_key,
    normalize_label_name,
    reinforced_confidence,
    utc_now_iso,
    validate_provenance_source,
    validate_relation,
)


class LabelConflictError(ValueError):
    """Raised when a canonical label or alias is already owned by another label node."""


class LabelLookupError(ValueError):
    """Raised when a canonical label or alias cannot be resolved."""


class MemoryStore:
    """Persistent memory store backed by a single JSON file.

    The stable location identity is the ``location_id``. Labels, concepts,
    graph edges, and sensor bindings hang off that location identity.
    """

    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data = self._load_or_initialize()

    # -- public properties -----------------------------------------------

    @property
    def confidence_policy(self) -> dict[str, Any]:
        return dict(self._data["confidence_policy"])

    @property
    def guess_threshold(self) -> float:
        return float(self._data["confidence_policy"]["guess_threshold"])

    @property
    def tolerance(self) -> float:
        return float(self._data["confidence_policy"]["tolerance"])

    @property
    def outlier_factor(self) -> float:
        return float(self._data["confidence_policy"].get("outlier_factor", DEFAULT_OUTLIER_FACTOR))

    @property
    def data(self) -> dict[str, Any]:
        return self._data

    # -- query -----------------------------------------------------------

    def find_nearest(
        self,
        observation: NormalizedObservation,
    ) -> tuple[LocationModel | None, float]:
        """Find the nearest scalar-backed location model by distance to its learned span."""
        best_model: LocationModel | None = None
        best_confidence = 0.0
        tolerance = self.tolerance

        for raw_model in self._data["location_models"].values():
            model = LocationModel.from_dict(raw_model)
            if model.prototype is None:
                continue
            distance = model.distance_to_value(observation.value)
            base_confidence = distance_to_confidence(distance, tolerance)
            confidence = reinforced_confidence(base_confidence, model.correct_count)
            if confidence > best_confidence:
                best_confidence = confidence
                best_model = model

        return best_model, best_confidence

    def find_near_collision(
        self,
        observation: NormalizedObservation,
        *,
        exclude_location_id: str | None = None,
    ) -> LocationModel | None:
        """Return an existing model whose learned scalar span is within tolerance."""
        tolerance = self.tolerance
        for raw_model in self._data["location_models"].values():
            model = LocationModel.from_dict(raw_model)
            if model.location_id == exclude_location_id or model.prototype is None:
                continue
            if model.distance_to_value(observation.value) <= tolerance:
                return model
        return None

    def lookup_by_id(self, location_id: str) -> LocationModel | None:
        raw_model = self._data["location_models"].get(location_id)
        if raw_model is None:
            return None
        return LocationModel.from_dict(raw_model)

    def get_label_node(self, label_id: str) -> LabelNode | None:
        raw_label = self._data["label_nodes"].get(label_id)
        if raw_label is None:
            return None
        return LabelNode.from_dict(raw_label)

    def get_concept_node(self, concept_id: str) -> ConceptNode | None:
        raw_concept = self._data["concept_nodes"].get(concept_id)
        if raw_concept is None:
            return None
        return ConceptNode.from_dict(raw_concept)

    def lookup_by_label_name(self, name: str) -> tuple[LocationModel, LabelNode] | None:
        label_id = self._name_index().get(label_lookup_key(name))
        if label_id is None:
            return None
        return self._require_model_and_label(label_id)

    def lookup_sensor_binding(
        self,
        fingerprint: str,
    ) -> tuple[SensorBinding, LocationModel, LabelNode] | None:
        for raw_binding in self._data["sensor_bindings"].values():
            binding = SensorBinding.from_dict(raw_binding)
            if binding.fingerprint != fingerprint:
                continue
            model = self.lookup_by_id(binding.location_id)
            if model is None:
                continue
            label = self._require_label_node(model.label_id)
            return binding, model, label
        return None

    def inspect_models(self) -> list[dict[str, Any]]:
        results = []
        for raw_model in self._data["location_models"].values():
            results.append(self.snapshot_location(LocationModel.from_dict(raw_model)))
        results.sort(key=lambda model: str(model["canonical_name"]).casefold())
        return results

    def snapshot_location(self, model: LocationModel | str) -> dict[str, Any]:
        current: LocationModel | None
        if isinstance(model, LocationModel):
            current = model
        else:
            current = self.lookup_by_id(self._coerce_location_id(model))
        if current is None:
            raise KeyError("location model not found")
        label_node = self._require_label_node(current.label_id)
        relations = self.location_relations(current.location_id)
        return {
            "location_id": current.location_id,
            "label_id": label_node.label_id,
            "label": label_node.canonical_name,
            "canonical_name": label_node.canonical_name,
            "aliases": list(label_node.aliases),
            "rename_history": [entry.to_dict() for entry in label_node.rename_history],
            "prototype": current.prototype,
            "spread": current.spread,
            "span_min": current.observation_bounds()[0],
            "span_max": current.observation_bounds()[1],
            "observation_count": current.observation_count,
            "guess_count": current.guess_count,
            "correct_count": current.correct_count,
            "incorrect_count": current.incorrect_count,
            "first_seen_at": current.first_seen_at,
            "last_seen_at": current.last_seen_at,
            "provenance_source": current.provenance_source,
            "provenance_detail": current.provenance_detail,
            "active_context": self.active_context_names(current.location_id),
            "contains": relations["contains"],
            "contained_by": relations["contained_by"],
            "overlaps": relations["overlaps"],
            "concepts": self.location_concepts(current.location_id),
            "sensor_binding_count": self._sensor_binding_count(current.location_id),
        }

    def active_context_names(self, location_ref: LocationModel | str) -> list[str]:
        location_id = self._coerce_location_id(location_ref)
        names: list[str] = []
        for active_id in self._active_context_ids(location_id):
            model = self.lookup_by_id(active_id)
            if model is None:
                continue
            label = self._require_label_node(model.label_id)
            names.append(label.canonical_name)
        return names

    def location_concepts(self, location_ref: LocationModel | str) -> list[str]:
        location_id = self._coerce_location_id(location_ref)
        concepts: list[str] = []
        for raw_edge in self._data["graph_edges"].values():
            edge = GraphEdge.from_dict(raw_edge)
            if (
                edge.source_node_type == "location"
                and edge.target_node_type == "concept"
                and edge.source_node_id == location_id
            ):
                concept = self.get_concept_node(edge.target_node_id)
                if concept is not None:
                    concepts.append(concept.concept_name)
        return sorted(set(concepts), key=str.casefold)

    def location_relations(self, location_ref: LocationModel | str) -> dict[str, list[str]]:
        location_id = self._coerce_location_id(location_ref)
        relations: dict[str, list[str]] = {
            "contains": [],
            "contained_by": [],
            "overlaps": [],
        }
        for edge in self._iter_location_relation_edges():
            if edge.relation_kind == "contains":
                if edge.source_node_id == location_id:
                    relations["contains"].append(self._location_name(edge.target_node_id))
                elif edge.target_node_id == location_id:
                    relations["contained_by"].append(self._location_name(edge.source_node_id))
                continue
            if edge.relation_kind == "overlaps":
                if edge.source_node_id == location_id:
                    relations["overlaps"].append(self._location_name(edge.target_node_id))
                elif edge.target_node_id == location_id:
                    relations["overlaps"].append(self._location_name(edge.source_node_id))

        for relation_kind, names in relations.items():
            relations[relation_kind] = sorted(set(names), key=str.casefold)
        return relations

    def is_outlier(self, model: LocationModel, value: float) -> bool:
        if model.prototype is None:
            return False
        threshold = self.outlier_factor * max(model.spread, self.tolerance)
        return model.distance_to_value(value) > threshold

    # -- reset -----------------------------------------------------------

    def reset_memory(self) -> int:
        count = len(self._data.get("location_models", {}))
        self._data = self._empty_payload()
        self._save()
        return count

    # -- mutations -------------------------------------------------------

    def create_location(
        self,
        label: str,
        *,
        location_provenance_source: str = "user",
        location_provenance_detail: str = "manual_location",
        label_provenance_source: str = "user",
        label_provenance_detail: str = "manual_label",
    ) -> tuple[None, LocationModel]:
        canonical_name = self._ensure_name_available(label)
        timestamp = utc_now_iso()
        label_node = LabelNode(
            label_id=f"label-{uuid.uuid4().hex[:12]}",
            canonical_name=canonical_name,
            aliases=(),
            rename_history=(),
            created_at=timestamp,
            updated_at=timestamp,
            provenance_source=validate_provenance_source(label_provenance_source),
            provenance_detail=label_provenance_detail,
        )
        model = LocationModel.empty(
            location_id=f"loc-{uuid.uuid4().hex[:12]}",
            label_id=label_node.label_id,
            provenance_source=location_provenance_source,
            provenance_detail=location_provenance_detail,
        )
        self._store_label_node(label_node)
        self._store_location_model(model)
        self._append_evidence(
            owner_node_id=label_node.label_id,
            owner_node_type="label",
            source_kind=label_node.provenance_source,
            channel="label_created",
            value_text=canonical_name,
        )
        self._save()
        return None, model

    def learn_location(
        self,
        observation: NormalizedObservation,
        label: str,
    ) -> tuple[None, LocationModel]:
        _, model = self.create_location(
            label,
            location_provenance_source="user",
            location_provenance_detail="scalar_observation",
            label_provenance_source="user",
            label_provenance_detail="manual_label",
        )
        updated = model.with_merged_observation(observation.value)
        self._store_location_model(updated)
        self._append_evidence(
            owner_node_id=updated.location_id,
            owner_node_type="location",
            source_kind="user",
            channel="scalar_observation",
            value_text=normalize_label_name(label),
            observation_value=observation.value,
        )
        self._save()
        return None, updated

    def reinforce_named_location(
        self,
        observation: NormalizedObservation,
        name: str,
    ) -> tuple[LocationModel, LocationModel]:
        current_model, _ = self._require_named_location(name)
        updated = current_model.with_merged_observation(observation.value)
        self._store_location_model(updated)
        self._append_evidence(
            owner_node_id=updated.location_id,
            owner_node_type="location",
            source_kind="user",
            channel="label_reuse",
            value_text=normalize_label_name(name),
            observation_value=observation.value,
        )
        self._save()
        return current_model, updated

    def record_correct_guess(
        self,
        observation: NormalizedObservation,
        matched_model: LocationModel | None = None,
    ) -> tuple[LocationModel, LocationModel]:
        if matched_model is None:
            raise KeyError("matched_model is required in Phase 4")
        current = matched_model
        merged = current.with_merged_observation(observation.value)
        updated = replace(
            merged,
            guess_count=current.guess_count + 1,
            correct_count=current.correct_count + 1,
        )
        self._store_location_model(updated)
        self._append_evidence(
            owner_node_id=updated.location_id,
            owner_node_type="location",
            source_kind="user",
            channel="guess_confirmation",
            observation_value=observation.value,
        )
        self._save()
        return current, updated

    def merge_observation(
        self,
        model: LocationModel,
        value: float,
        *,
        source_kind: str = "user",
        channel: str = "scalar_merge",
    ) -> tuple[LocationModel, LocationModel]:
        updated = model.with_merged_observation(value)
        self._store_location_model(updated)
        self._append_evidence(
            owner_node_id=updated.location_id,
            owner_node_type="location",
            source_kind=source_kind,
            channel=channel,
            observation_value=value,
        )
        self._save()
        return model, updated

    def correct_location(
        self,
        observation: NormalizedObservation,
        new_label: str,
        matched_model: LocationModel | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        if matched_model is None:
            raise KeyError("matched_model is required in Phase 4")
        current_model = matched_model
        old_snapshot = self.snapshot_location(current_model)
        current_label = self._require_label_node(current_model.label_id)
        updated_label = self._rename_label_node(current_label, new_label)
        merged = current_model.with_merged_observation(observation.value)
        updated_model = replace(
            merged,
            guess_count=current_model.guess_count + 1,
            incorrect_count=current_model.incorrect_count + 1,
        )
        self._store_label_node(updated_label)
        self._store_location_model(updated_model)
        self._append_evidence(
            owner_node_id=updated_model.location_id,
            owner_node_type="location",
            source_kind="user",
            channel="label_correction",
            value_text=normalize_label_name(new_label),
            observation_value=observation.value,
        )
        self._save()
        return old_snapshot, self.snapshot_location(updated_model)

    def rename_label(
        self,
        existing_name: str,
        new_name: str,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        current_model, current_label = self._require_named_location(existing_name)
        old_snapshot = self.snapshot_location(current_model)
        updated_label = self._rename_label_node(current_label, new_name)
        self._store_label_node(updated_label)
        self._append_evidence(
            owner_node_id=updated_label.label_id,
            owner_node_type="label",
            source_kind="user",
            channel="label_rename",
            value_text=normalize_label_name(new_name),
        )
        self._save()
        return old_snapshot, self.snapshot_location(current_model.location_id)

    def add_alias(
        self,
        existing_name: str,
        alias: str,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        current_model, current_label = self._require_named_location(existing_name)
        old_snapshot = self.snapshot_location(current_model)
        normalized_alias = self._ensure_name_available(alias, owner_label_id=current_label.label_id)
        if normalized_alias.casefold() == current_label.canonical_name.casefold():
            return old_snapshot, old_snapshot
        updated_label = current_label.with_alias(normalized_alias)
        self._store_label_node(updated_label)
        self._append_evidence(
            owner_node_id=updated_label.label_id,
            owner_node_type="label",
            source_kind="user",
            channel="label_alias",
            value_text=normalized_alias,
        )
        self._save()
        return old_snapshot, self.snapshot_location(current_model.location_id)

    def link_locations(
        self,
        parent_name: str,
        child_name: str,
        *,
        relation_kind: str = "contains",
        provenance_source: str = "user",
        provenance_detail: str = "manual_location_relation",
    ) -> tuple[GraphEdge | None, bool]:
        parent_model, parent_label = self._require_named_location(parent_name)
        child_model, child_label = self._require_named_location(child_name)
        if parent_model.location_id == child_model.location_id:
            return None, False

        if relation_kind == "contains" and self._would_create_containment_cycle(
            child_location_id=child_model.location_id,
            parent_location_id=parent_model.location_id,
        ):
            raise ValueError(
                f"cannot create containment cycle: "
                f'"{child_label.canonical_name}" already transitively contains '
                f'"{parent_label.canonical_name}"'
            )

        source_model = parent_model
        target_model = child_model
        source_name = parent_label.canonical_name
        target_name = child_label.canonical_name
        if relation_kind == "overlaps" and target_model.location_id < source_model.location_id:
            source_model, target_model = target_model, source_model
            source_name, target_name = target_name, source_name

        existing = self._find_graph_edge(
            source_node_id=source_model.location_id,
            source_node_type="location",
            target_node_id=target_model.location_id,
            target_node_type="location",
            relation_kind=relation_kind,
        )
        if existing is not None:
            return existing, False

        timestamp = utc_now_iso()
        edge = GraphEdge(
            edge_id=f"edge-{uuid.uuid4().hex[:12]}",
            source_node_id=source_model.location_id,
            source_node_type="location",
            target_node_id=target_model.location_id,
            target_node_type="location",
            relation_kind=relation_kind,
            created_at=timestamp,
            updated_at=timestamp,
            provenance_source=validate_provenance_source(provenance_source),
            provenance_detail=provenance_detail,
        )
        self._store_graph_edge(edge)
        relation_text = (
            f"{source_name}<->{target_name}"
            if relation_kind == "overlaps"
            else f"{source_name}->{target_name}"
        )
        self._append_evidence(
            owner_node_id=edge.edge_id,
            owner_node_type="edge",
            source_kind=edge.provenance_source,
            channel="location_relation",
            value_text=relation_text,
        )
        self._save()
        return edge, True

    def attach_concept(
        self,
        location_name: str,
        concept_name: str,
        *,
        relation_kind: str = "context_label",
        provenance_source: str = "user",
        provenance_detail: str = "manual_concept",
    ) -> tuple[ConceptNode, GraphEdge]:
        location_model, _ = self._require_named_location(location_name)
        concept = self._ensure_concept_node(
            concept_name,
            provenance_source=provenance_source,
            provenance_detail=provenance_detail,
        )
        existing = self._find_graph_edge(
            source_node_id=location_model.location_id,
            source_node_type="location",
            target_node_id=concept.concept_id,
            target_node_type="concept",
            relation_kind=relation_kind,
        )
        if existing is not None:
            edge = replace(existing, updated_at=utc_now_iso())
        else:
            timestamp = utc_now_iso()
            edge = GraphEdge(
                edge_id=f"edge-{uuid.uuid4().hex[:12]}",
                source_node_id=location_model.location_id,
                source_node_type="location",
                target_node_id=concept.concept_id,
                target_node_type="concept",
                relation_kind=relation_kind,
                created_at=timestamp,
                updated_at=timestamp,
                provenance_source=validate_provenance_source(provenance_source),
                provenance_detail=provenance_detail,
            )
        self._store_graph_edge(edge)
        self._append_evidence(
            owner_node_id=edge.edge_id,
            owner_node_type="edge",
            source_kind=edge.provenance_source,
            channel="location_concept",
            value_text=f"{normalize_label_name(location_name)}->{concept.concept_name}",
        )
        self._save()
        return concept, edge

    # -- concept CRUD ----------------------------------------------------

    def create_concept(
        self,
        name: str,
        concept_kind: str = "named",
        *,
        provenance_source: str = "user",
        provenance_detail: str = "manual_concept",
    ) -> ConceptNode:
        concept = self._ensure_concept_node(
            name,
            concept_kind=concept_kind,
            provenance_source=provenance_source,
            provenance_detail=provenance_detail,
        )
        self._save()
        return concept

    def lookup_concept_by_name(self, name: str) -> ConceptNode | None:
        concept_id = self._concept_index().get(label_lookup_key(name))
        if concept_id is None:
            return None
        return self.get_concept_node(concept_id)

    def alias_concept(self, concept_name: str, new_alias: str) -> ConceptNode:
        concept = self.lookup_concept_by_name(concept_name)
        if concept is None:
            raise LabelLookupError(f'concept not found: "{concept_name}"')
        normalized_alias = normalize_label_name(new_alias)
        existing_owner = self._concept_index().get(label_lookup_key(normalized_alias))
        if existing_owner is not None and existing_owner != concept.concept_id:
            raise LabelConflictError(f'concept alias "{normalized_alias}" is already in use')
        if label_lookup_key(normalized_alias) in {label_lookup_key(n) for n in concept.all_names()}:
            return concept
        updated = replace(
            concept,
            aliases=concept.aliases + (normalized_alias,),
            updated_at=utc_now_iso(),
        )
        self._store_concept_node(updated)
        self._save()
        return updated

    def link_concepts(
        self,
        source_name: str,
        target_name: str,
        relation_kind: str,
        *,
        provenance_source: str = "user",
        provenance_detail: str = "manual_concept_relation",
    ) -> tuple[GraphEdge, bool]:
        source_concept = self.lookup_concept_by_name(source_name)
        if source_concept is None:
            raise LabelLookupError(f'concept not found: "{source_name}"')
        target_concept = self.lookup_concept_by_name(target_name)
        if target_concept is None:
            raise LabelLookupError(f'concept not found: "{target_name}"')
        if source_concept.concept_id == target_concept.concept_id:
            raise ValueError("cannot link a concept to itself")
        validate_relation(relation_kind, "concept", "concept")
        existing = self._find_graph_edge(
            source_node_id=source_concept.concept_id,
            source_node_type="concept",
            target_node_id=target_concept.concept_id,
            target_node_type="concept",
            relation_kind=relation_kind,
        )
        if existing is not None:
            return existing, False
        timestamp = utc_now_iso()
        edge = GraphEdge(
            edge_id=f"edge-{uuid.uuid4().hex[:12]}",
            source_node_id=source_concept.concept_id,
            source_node_type="concept",
            target_node_id=target_concept.concept_id,
            target_node_type="concept",
            relation_kind=relation_kind,
            created_at=timestamp,
            updated_at=timestamp,
            provenance_source=validate_provenance_source(provenance_source),
            provenance_detail=provenance_detail,
        )
        self._store_graph_edge(edge)
        self._append_evidence(
            owner_node_id=edge.edge_id,
            owner_node_type="edge",
            source_kind=edge.provenance_source,
            channel="concept_relation",
            value_text=f"{source_concept.concept_name} -{relation_kind}-> {target_concept.concept_name}",
        )
        self._save()
        return edge, True

    def concept_relations(self, concept_ref: ConceptNode | str) -> dict[str, list[str]]:
        if isinstance(concept_ref, ConceptNode):
            concept_id = concept_ref.concept_id
        else:
            concept = self.lookup_concept_by_name(concept_ref)
            if concept is None:
                raise LabelLookupError(f'concept not found: "{concept_ref}"')
            concept_id = concept.concept_id
        relations: dict[str, list[str]] = {
            "supports": [],
            "supported_by": [],
            "composes": [],
            "composed_by": [],
            "supports_hypothesis": [],
            "hypothesis_supported_by": [],
        }
        for raw_edge in self._data["graph_edges"].values():
            edge = GraphEdge.from_dict(raw_edge)
            if edge.source_node_type != "concept" or edge.target_node_type != "concept":
                continue
            if edge.source_node_id == concept_id:
                target = self.get_concept_node(edge.target_node_id)
                name = target.concept_name if target else edge.target_node_id
                if edge.relation_kind == "supports":
                    relations["supports"].append(name)
                elif edge.relation_kind == "composes":
                    relations["composes"].append(name)
                elif edge.relation_kind == "supports_hypothesis":
                    relations["supports_hypothesis"].append(name)
            elif edge.target_node_id == concept_id:
                source = self.get_concept_node(edge.source_node_id)
                name = source.concept_name if source else edge.source_node_id
                if edge.relation_kind == "supports":
                    relations["supported_by"].append(name)
                elif edge.relation_kind == "composes":
                    relations["composed_by"].append(name)
                elif edge.relation_kind == "supports_hypothesis":
                    relations["hypothesis_supported_by"].append(name)
        for key in relations:
            relations[key] = sorted(set(relations[key]), key=str.casefold)
        return relations

    def inspect_concepts(self) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for raw_concept in self._data["concept_nodes"].values():
            concept = ConceptNode.from_dict(raw_concept)
            rels = self.concept_relations(concept)
            result.append(
                {
                    "concept_id": concept.concept_id,
                    "concept_name": concept.concept_name,
                    "concept_kind": concept.concept_kind,
                    "aliases": list(concept.aliases),
                    "provenance_source": concept.provenance_source,
                    **rels,
                }
            )
        result.sort(key=lambda c: str(c["concept_name"]).casefold())
        return result

    # -- sensor binding --------------------------------------------------

    def bind_sensor_observation(
        self,
        sensor_observation: SensorObservation,
        label: str,
    ) -> tuple[dict[str, Any] | None, dict[str, Any], bool]:
        resolved = self.lookup_by_label_name(label)
        created_new_location = False
        if resolved is None:
            _, target_model = self.create_location(
                label,
                location_provenance_source="sensor",
                location_provenance_detail="sensor_path",
                label_provenance_source="user",
                label_provenance_detail="sensor_label",
            )
            created_new_location = True
        else:
            target_model, _ = resolved
            target_model = target_model.with_last_seen()
            self._store_location_model(target_model)

        existing_binding = self.lookup_sensor_binding(sensor_observation.fingerprint)
        old_snapshot = (
            None if existing_binding is None else self.snapshot_location(existing_binding[1])
        )
        if existing_binding is None:
            timestamp = utc_now_iso()
            binding = SensorBinding(
                sensor_id=f"sensor-{uuid.uuid4().hex[:12]}",
                fingerprint=sensor_observation.fingerprint,
                media_kind=sensor_observation.media_kind,
                media_path=sensor_observation.resolved_path,
                location_id=target_model.location_id,
                created_at=timestamp,
                updated_at=timestamp,
                provenance_source="sensor",
                provenance_detail="sensor_path",
            )
        else:
            binding = existing_binding[0].with_location(
                target_model.location_id,
                sensor_observation.resolved_path,
            )
        self._store_sensor_binding(binding)
        self._append_evidence(
            owner_node_id=target_model.location_id,
            owner_node_type="location",
            source_kind="sensor",
            channel="sensor_path",
            value_text=normalize_label_name(label),
            sensor_fingerprint=sensor_observation.fingerprint,
            media_kind=sensor_observation.media_kind,
            media_path=sensor_observation.resolved_path,
        )
        self._append_evidence(
            owner_node_id=target_model.label_id,
            owner_node_type="label",
            source_kind="user",
            channel="sensor_label_confirmation",
            value_text=normalize_label_name(label),
        )
        self._save()
        return old_snapshot, self.snapshot_location(target_model.location_id), created_new_location

    # -- observation bundle storage --------------------------------------

    def store_bundle(self, bundle: ObservationBundle) -> None:
        """Persist an ``ObservationBundle`` keyed by ``bundle_id``."""
        self._data["observation_bundles"][bundle.bundle_id] = bundle.to_dict()
        self._save()

    def get_bundle(self, bundle_id: str) -> ObservationBundle | None:
        raw = self._data["observation_bundles"].get(bundle_id)
        if raw is None:
            return None
        return ObservationBundle.from_dict(raw)

    def bind_sensor_bundle(
        self,
        bundle: ObservationBundle,
        sensor_observation: SensorObservation,
        label: str,
    ) -> tuple[dict[str, Any] | None, dict[str, Any], bool]:
        """Bind a sensor observation via its bundle, persisting both the bundle and binding."""
        self.store_bundle(bundle)
        return self.bind_sensor_observation(sensor_observation, label)

    # -- persistence internals -------------------------------------------

    def _load_or_initialize(self) -> dict[str, Any]:
        if not self.path.exists():
            payload = self._empty_payload()
            self._write_payload(payload)
            return payload

        raw = self.path.read_text(encoding="utf-8")
        if not raw.strip():
            payload = self._empty_payload()
            self._write_payload(payload)
            return payload

        payload = json.loads(raw)
        payload.setdefault("schema_version", 1)
        payload.setdefault("confidence_policy", self._default_confidence_policy())
        payload.setdefault("created_at", utc_now_iso())
        payload.setdefault("updated_at", payload["created_at"])

        version = int(payload.get("schema_version", 1))

        if version < 2:
            policy = payload["confidence_policy"]
            policy["kind"] = "distance"
            policy["tolerance"] = DEFAULT_TOLERANCE
            policy["guess_threshold"] = DEFAULT_GUESS_THRESHOLD
            payload["schema_version"] = 2
            version = 2

        if version < 3:
            old_locations = payload.get("locations_by_observation", {})
            models: dict[str, Any] = {}
            for raw_record in old_locations.values():
                record = LocationRecord.from_dict(raw_record)
                models[record.location_id] = {
                    "location_id": record.location_id,
                    "label": record.label,
                    "prototype": record.observation_value,
                    "observation_values": [record.observation_value],
                    "observation_count": record.observation_count,
                    "spread": 0.0,
                    "guess_count": record.guess_count,
                    "correct_count": record.correct_count,
                    "incorrect_count": record.incorrect_count,
                    "first_seen_at": record.first_seen_at,
                    "last_seen_at": record.last_seen_at,
                }
            payload["location_models"] = models
            payload.pop("locations_by_observation", None)
            payload["confidence_policy"].setdefault("outlier_factor", DEFAULT_OUTLIER_FACTOR)
            payload["schema_version"] = 3
            version = 3

        if version < 4:
            migrated_models: dict[str, Any] = {}
            label_nodes: dict[str, Any] = {}
            used_name_keys: set[str] = set()
            for raw_model in payload.get("location_models", {}).values():
                raw_name = str(raw_model.get("label", "")).strip()
                if not raw_name:
                    raw_name = f"unnamed-{raw_model['location_id']}"
                canonical_name, rename_history = self._disambiguate_migrated_name(
                    raw_name, used_name_keys
                )
                label_id = f"label-{uuid.uuid4().hex[:12]}"
                created_at = str(raw_model.get("first_seen_at", payload["created_at"]))
                updated_at = str(raw_model.get("last_seen_at", created_at))
                label_nodes[label_id] = {
                    "label_id": label_id,
                    "canonical_name": canonical_name,
                    "aliases": [],
                    "rename_history": [entry.to_dict() for entry in rename_history],
                    "created_at": created_at,
                    "updated_at": updated_at,
                }
                migrated = dict(raw_model)
                migrated.pop("label", None)
                migrated["label_id"] = label_id
                migrated_models[str(migrated["location_id"])] = migrated

            payload["location_models"] = migrated_models
            payload["label_nodes"] = label_nodes
            payload["schema_version"] = 4
            version = 4

        if version < 5:
            for raw_label in payload.get("label_nodes", {}).values():
                raw_label.setdefault("provenance_source", "user")
                raw_label.setdefault("provenance_detail", "migrated_label")
            for raw_model in payload.get("location_models", {}).values():
                raw_model.setdefault("prototype", raw_model.get("prototype"))
                raw_model.setdefault("observation_values", raw_model.get("observation_values", []))
                raw_model.setdefault(
                    "observation_count",
                    len(raw_model.get("observation_values", [])),
                )
                raw_model.setdefault("provenance_source", "user")
                raw_model.setdefault("provenance_detail", "migrated_scalar_observation")
            payload.setdefault("concept_nodes", {})
            payload.setdefault("graph_edges", {})
            payload.setdefault("sensor_bindings", {})
            payload.setdefault("evidence_records", {})
            payload["schema_version"] = 5
            version = 5

        if version < 6:
            for raw_concept in payload.get("concept_nodes", {}).values():
                raw_concept.setdefault("concept_kind", "named")
            payload["schema_version"] = 6
            version = 6

        if version < 7:
            payload.setdefault("observation_bundles", {})
            payload["schema_version"] = 7
            version = 7

        payload.setdefault("location_models", {})
        payload.setdefault("label_nodes", {})
        payload.setdefault("concept_nodes", {})
        payload.setdefault("graph_edges", {})
        payload.setdefault("sensor_bindings", {})
        payload.setdefault("evidence_records", {})
        payload.setdefault("observation_bundles", {})
        payload["confidence_policy"].setdefault("outlier_factor", DEFAULT_OUTLIER_FACTOR)
        payload["schema_version"] = version

        self._data = payload
        self._name_index()
        self._concept_index()
        self._write_payload(payload)
        return payload

    def _empty_payload(self) -> dict[str, Any]:
        timestamp = utc_now_iso()
        return {
            "schema_version": SCHEMA_VERSION,
            "created_at": timestamp,
            "updated_at": timestamp,
            "confidence_policy": self._default_confidence_policy(),
            "location_models": {},
            "label_nodes": {},
            "concept_nodes": {},
            "graph_edges": {},
            "sensor_bindings": {},
            "evidence_records": {},
            "observation_bundles": {},
        }

    def _default_confidence_policy(self) -> dict[str, Any]:
        return {
            "kind": "distance",
            "tolerance": DEFAULT_TOLERANCE,
            "guess_threshold": DEFAULT_GUESS_THRESHOLD,
            "normalization_decimals": 6,
            "outlier_factor": DEFAULT_OUTLIER_FACTOR,
        }

    def _save(self) -> None:
        self._data["updated_at"] = utc_now_iso()
        self._write_payload(self._data)

    def _write_payload(self, payload: dict[str, Any]) -> None:
        temporary_path = self.path.with_suffix(self.path.suffix + ".tmp")
        serialized = json.dumps(payload, indent=2, sort_keys=True)
        temporary_path.write_text(f"{serialized}\n", encoding="utf-8")
        temporary_path.replace(self.path)

    # -- node internals --------------------------------------------------

    def _store_location_model(self, model: LocationModel) -> None:
        self._data["location_models"][model.location_id] = model.to_dict()

    def _store_label_node(self, label_node: LabelNode) -> None:
        self._data["label_nodes"][label_node.label_id] = label_node.to_dict()

    def _store_concept_node(self, concept_node: ConceptNode) -> None:
        self._data["concept_nodes"][concept_node.concept_id] = concept_node.to_dict()

    def _store_graph_edge(self, edge: GraphEdge) -> None:
        validate_relation(edge.relation_kind, edge.source_node_type, edge.target_node_type)
        self._data["graph_edges"][edge.edge_id] = edge.to_dict()

    def _store_sensor_binding(self, binding: SensorBinding) -> None:
        self._data["sensor_bindings"][binding.sensor_id] = binding.to_dict()

    def _append_evidence(
        self,
        *,
        owner_node_id: str,
        owner_node_type: str,
        source_kind: str,
        channel: str,
        value_text: str | None = None,
        observation_value: float | None = None,
        sensor_fingerprint: str | None = None,
        media_kind: str | None = None,
        media_path: str | None = None,
    ) -> EvidenceRecord:
        evidence = EvidenceRecord(
            evidence_id=f"evidence-{uuid.uuid4().hex[:12]}",
            owner_node_id=owner_node_id,
            owner_node_type=owner_node_type,
            source_kind=validate_provenance_source(source_kind),
            channel=channel,
            value_text=value_text,
            observation_value=observation_value,
            sensor_fingerprint=sensor_fingerprint,
            media_kind=media_kind,
            media_path=media_path,
            created_at=utc_now_iso(),
        )
        self._data["evidence_records"][evidence.evidence_id] = evidence.to_dict()
        return evidence

    def _require_label_node(self, label_id: str) -> LabelNode:
        label_node = self.get_label_node(label_id)
        if label_node is None:
            raise KeyError(f"label node not found: {label_id}")
        return label_node

    def _require_model_for_label(self, label_id: str) -> LocationModel:
        for raw_model in self._data["location_models"].values():
            if str(raw_model["label_id"]) == label_id:
                return LocationModel.from_dict(raw_model)
        raise KeyError(f"location model not found for label: {label_id}")

    def _require_model_and_label(self, label_id: str) -> tuple[LocationModel, LabelNode]:
        return self._require_model_for_label(label_id), self._require_label_node(label_id)

    def _require_named_location(self, name: str) -> tuple[LocationModel, LabelNode]:
        resolved = self.lookup_by_label_name(name)
        if resolved is None:
            raise LabelLookupError(f'label "{normalize_label_name(name)}" was not found')
        return resolved

    def _ensure_name_available(
        self,
        name: str,
        *,
        owner_label_id: str | None = None,
    ) -> str:
        normalized = normalize_label_name(name)
        owner = self._name_index().get(label_lookup_key(normalized))
        if owner is not None and owner != owner_label_id:
            raise LabelConflictError(f'label "{normalized}" is already in use')
        return normalized

    def _rename_label_node(self, label_node: LabelNode, new_name: str) -> LabelNode:
        normalized = self._ensure_name_available(new_name, owner_label_id=label_node.label_id)
        return label_node.with_renamed_canonical(normalized)

    def _name_index(self) -> dict[str, str]:
        index: dict[str, str] = {}
        for raw_label in self._data.get("label_nodes", {}).values():
            label_node = LabelNode.from_dict(raw_label)
            for name in label_node.all_names():
                key = label_lookup_key(name)
                owner = index.get(key)
                if owner is not None and owner != label_node.label_id:
                    raise ValueError(f'duplicate active label name detected: "{name}"')
                index[key] = label_node.label_id
        return index

    def _concept_index(self) -> dict[str, str]:
        index: dict[str, str] = {}
        for raw_concept in self._data.get("concept_nodes", {}).values():
            concept_node = ConceptNode.from_dict(raw_concept)
            for name in concept_node.all_names():
                key = label_lookup_key(name)
                owner = index.get(key)
                if owner is not None and owner != concept_node.concept_id:
                    raise ValueError(f'duplicate concept name detected: "{name}"')
                index[key] = concept_node.concept_id
        return index

    def _ensure_concept_node(
        self,
        concept_name: str,
        *,
        concept_kind: str = "named",
        provenance_source: str,
        provenance_detail: str,
    ) -> ConceptNode:
        if concept_kind not in VALID_CONCEPT_KINDS:
            raise ValueError(f"invalid concept_kind: {concept_kind!r}")
        concept_id = self._concept_index().get(label_lookup_key(concept_name))
        if concept_id is not None:
            concept = self.get_concept_node(concept_id)
            if concept is None:
                raise KeyError(f"concept node not found: {concept_id}")
            return concept
        timestamp = utc_now_iso()
        concept = ConceptNode(
            concept_id=f"concept-{uuid.uuid4().hex[:12]}",
            concept_name=normalize_label_name(concept_name),
            concept_kind=concept_kind,
            aliases=(),
            created_at=timestamp,
            updated_at=timestamp,
            provenance_source=validate_provenance_source(provenance_source),
            provenance_detail=provenance_detail,
        )
        self._store_concept_node(concept)
        self._append_evidence(
            owner_node_id=concept.concept_id,
            owner_node_type="concept",
            source_kind=concept.provenance_source,
            channel="concept_created",
            value_text=concept.concept_name,
        )
        return concept

    def _coerce_location_id(self, location_ref: LocationModel | str) -> str:
        if isinstance(location_ref, LocationModel):
            return location_ref.location_id
        if location_ref in self._data["location_models"]:
            return location_ref
        model, _ = self._require_named_location(location_ref)
        return model.location_id

    def _active_context_ids(self, location_id: str) -> list[str]:
        ordered: list[str] = [location_id]
        seen = {location_id}
        frontier = [location_id]

        while frontier:
            current_id = frontier.pop(0)
            for edge in self._iter_location_relation_edges():
                if (
                    edge.relation_kind == "contains"
                    and edge.target_node_id == current_id
                    and edge.source_node_id not in seen
                ):
                    seen.add(edge.source_node_id)
                    ordered.append(edge.source_node_id)
                    frontier.append(edge.source_node_id)
                if edge.relation_kind != "overlaps":
                    continue
                other_id = None
                if edge.source_node_id == current_id:
                    other_id = edge.target_node_id
                elif edge.target_node_id == current_id:
                    other_id = edge.source_node_id
                if other_id is not None and other_id not in seen:
                    seen.add(other_id)
                    ordered.append(other_id)
                    frontier.append(other_id)
        return ordered

    def _sensor_binding_count(self, location_id: str) -> int:
        count = 0
        for raw_binding in self._data["sensor_bindings"].values():
            binding = SensorBinding.from_dict(raw_binding)
            if binding.location_id == location_id:
                count += 1
        return count

    def _find_graph_edge(
        self,
        *,
        source_node_id: str,
        source_node_type: str,
        target_node_id: str,
        target_node_type: str,
        relation_kind: str,
    ) -> GraphEdge | None:
        for raw_edge in self._data["graph_edges"].values():
            edge = GraphEdge.from_dict(raw_edge)
            if (
                edge.source_node_id == source_node_id
                and edge.source_node_type == source_node_type
                and edge.target_node_id == target_node_id
                and edge.target_node_type == target_node_type
                and edge.relation_kind == relation_kind
            ):
                return edge
        return None

    def _iter_location_relation_edges(self) -> list[GraphEdge]:
        edges: list[GraphEdge] = []
        for raw_edge in self._data["graph_edges"].values():
            edge = GraphEdge.from_dict(raw_edge)
            if edge.source_node_type != "location" or edge.target_node_type != "location":
                continue
            edges.append(edge)
        return edges

    def _would_create_containment_cycle(
        self,
        child_location_id: str,
        parent_location_id: str,
    ) -> bool:
        """Return True if making *parent* contain *child* would create a cycle.

        A cycle exists when *child* already transitively contains *parent*
        through existing ``contains`` edges.  We walk upward from *parent*
        through reverse ``contains`` edges (i.e. edges where *parent* is the
        target / contained node) and check whether *child* is reachable as an
        ancestor.
        """
        visited: set[str] = set()
        stack = [parent_location_id]
        while stack:
            current = stack.pop()
            if current == child_location_id:
                return True
            if current in visited:
                continue
            visited.add(current)
            for edge in self._iter_location_relation_edges():
                if edge.relation_kind == "contains" and edge.target_node_id == current:
                    stack.append(edge.source_node_id)
        return False

    def _location_name(self, location_id: str) -> str:
        model = self.lookup_by_id(location_id)
        if model is None:
            raise KeyError(f"location model not found: {location_id}")
        label_node = self._require_label_node(model.label_id)
        return label_node.canonical_name

    def _disambiguate_migrated_name(
        self,
        raw_name: str,
        used_name_keys: set[str],
    ) -> tuple[str, tuple[RenameRecord, ...]]:
        try:
            base_name = normalize_label_name(raw_name)
        except LabelNameError:
            base_name = "unnamed"

        candidate = base_name
        suffix = 2
        while candidate.casefold() in used_name_keys:
            candidate = f"{base_name} ({suffix})"
            suffix += 1

        used_name_keys.add(candidate.casefold())
        if candidate == base_name:
            return candidate, ()

        migration_time = utc_now_iso()
        return candidate, (
            RenameRecord(
                old_name=base_name,
                new_name=candidate,
                renamed_at=migration_time,
            ),
        )

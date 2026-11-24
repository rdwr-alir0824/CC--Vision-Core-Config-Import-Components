"""Local input adapters for the offline controller workflow; no product I/O."""

import hashlib
from dataclasses import dataclass
from pathlib import Path

from ._contract_validation import ContractReader
from ._json import load_json
from .artifacts import ConfigurationArtifact, parse_artifact
from .controller_access_policy import DeviceAccessAcknowledgement, _evidence
from .controller_comparison import ControllerComparisonRule
from .controller_exports import adapt_flat_export, adapt_tree_response
from .controller_objects import (
    ControllerInventory, SourceObjectReference, TreeName, _reference, _tree,
    parse_controller_artifact, validate_controller_credentials,
)
from .controller_reconciliation import DeviceReconciliationAssociation, reconcile_controller_devices
from .profiles import DestinationProfile, SourceProfile


def local_path(value: str | Path, base: Path) -> Path:
    reader = ContractReader("offline-workflow")
    text = reader.text(str(value), "$")
    path = Path(text)
    if text.startswith(("\\\\", "//")) or "://" in text or (path.drive and not path.is_absolute()):
        reader.fail("nonlocal_input", "$", "Use a local path, not a URL, UNC, or drive-relative path.")
    return path if path.is_absolute() else base / path


def write_local_export(path_value: str, serialized: str) -> None:
    path = local_path(path_value, Path.cwd())
    reader = ContractReader("master-export")
    created = False
    try:
        with path.open("x", encoding="utf-8") as output:
            created = True
            output.write(serialized)
    except FileExistsError:
        reader.fail("output_exists", "$", "Export output already exists; choose a new file.")
    except (OSError, ValueError, UnicodeError):
        if created:
            try:
                path.unlink()
            except OSError:
                reader.fail("output_cleanup_failed", "$", "Export failed and its partial output could not be removed.")
        reader.fail("output_unwritable", "$", "Cannot write the local export output.")


def _array(value: object, reader: ContractReader) -> list[object]:
    if not isinstance(value, list):
        reader.fail("invalid_type", "$", "Expected an explicit array.")
    return list(value)


def _versioned(value: object, fields: set[str], reader: ContractReader) -> dict[str, object]:
    data = reader.mapping(value, "$", fields | {"schema_version"})
    if type(data.get("schema_version")) is not int or data["schema_version"] != 1:
        reader.fail("unsupported_schema", "$", "Only integer workflow schema version 1 is supported.")
    for key in sorted(fields):
        reader.required(data, key, "$")
    return data


def _acknowledgement(value: object, reader: ContractReader) -> DeviceAccessAcknowledgement:
    fields = {
        "device", "source_artifact_sha256", "access_sha256", "evidence_reference", "policy_version", "scope",
    }
    data = reader.mapping(value, "$", fields)
    for key in sorted(fields):
        reader.required(data, key, "$")
    if data["scope"] != "offline-planning-only":
        reader.fail("invalid_acknowledgement", "$", "Only offline-planning acknowledgement is supported.")
    result = DeviceAccessAcknowledgement(
        _reference(data["device"], reader, "$"),
        reader.checksum(data["source_artifact_sha256"], "$"),
        reader.checksum(data["access_sha256"], "$"),
        reader.text(data["evidence_reference"], "$"),
        reader.text(data["policy_version"], "$"),
    )
    result.to_dict()
    return result


@dataclass(frozen=True, repr=False)
class PlanningDeclarations:
    mappings: object
    complete_trees: tuple[TreeName, ...]
    semantics: tuple[SourceObjectReference, ...]
    rules: tuple[ControllerComparisonRule, ...]
    acknowledgements: tuple[DeviceAccessAcknowledgement, ...]


class OfflineInputs:
    def __init__(self, request: str | Path) -> None:
        self.request = local_path(request, Path.cwd())
        self.base = self.request.absolute().parent
        self.reader = ContractReader("offline-workflow")
        self.bindings: list[dict[str, str]] = []
        self.artifacts: dict[str, ConfigurationArtifact] = {}

    def _retain_artifact(self, role: str, artifact: ConfigurationArtifact) -> None:
        validate_controller_credentials(artifact)
        self.artifacts[role] = artifact

    def read(self, value: object, slot: str | None, *, base: Path | None = None) -> object:
        name = self.reader.text(value, "$")
        path = local_path(name, self.base if base is None else base)
        try:
            raw = path.read_bytes()
        except (OSError, ValueError):
            raw = None
        if raw is None:
            self.reader.fail("input_unreadable", "$", "Cannot read a required local input.")
        if slot is not None:
            self.bindings.append({"slot": slot, "sha256": hashlib.sha256(raw).hexdigest()})
        try:
            text = raw.decode("utf-8")
        except UnicodeError:
            text = None
        if text is None:
            self.reader.fail("invalid_encoding", "$", "Inputs must be UTF-8 text.")
        try:
            return load_json(text)
        except (ValueError, RecursionError):
            pass
        self.reader.fail("invalid_json", "$", "Inputs require strict JSON with unique member names.")

    def manifest(self) -> dict[str, object]:
        data = _versioned(
            self.read(str(self.request.absolute()), "manifest"),
            {"scope", "source", "destination", "mappings", "acknowledgements", "policy", "completeness"},
            self.reader,
        )
        if data["scope"] != "offline-controller-planning":
            self.reader.fail("invalid_scope", "$", "Only offline controller planning is supported.")
        return data

    def side(self, value: object, role: str) -> ControllerInventory:
        reader = self.reader
        data = reader.mapping(value, "$", {"controller_id", "profile", "input", "reconciliation"})
        for key in ("controller_id", "profile", "input", "reconciliation"):
            reader.required(data, key, "$")
        controller_id = reader.text(data["controller_id"], "$")
        profile_data = self.read(data["profile"], role + "-profile")
        profile = SourceProfile.from_dict(profile_data) if role == "source" else DestinationProfile.from_dict(profile_data)
        if profile.product != "cyber-controller" or profile.version != "0.0-test":
            reader.fail("unsupported_context", "$", "Only synthetic Cyber Controller inputs are enabled.")
        spec = reader.mapping(data["input"], "$", {"format", "path", "tree", "exported_at", "root"})
        payload = self.read(reader.required(spec, "path", "$"), role + "-input")
        kind = reader.required(spec, "format", "$")
        if kind == "artifact":
            reader.mapping(spec, "$", {"format", "path"})
            artifact = parse_artifact(payload)
        elif kind in ("tree", "flat"):
            tree = _tree(reader.required(spec, "tree", "$"), reader, "$")
            exported_at = reader.text(reader.required(spec, "exported_at", "$"), "$")
            if kind == "tree":
                reader.mapping(spec, "$", {"format", "path", "tree", "exported_at"})
                exported = adapt_tree_response(
                    payload, controller_id=controller_id, tree=tree,
                    version=profile.version, exported_at=exported_at,
                )
            else:
                root = self.read(reader.required(spec, "root", "$"), role + "-root")
                exported = adapt_flat_export(
                    payload, root_response=root, controller_id=controller_id,
                    tree=tree, version=profile.version, exported_at=exported_at,
                )
            artifact = exported.artifact
        else:
            reader.fail("unsupported_format", "$", "Expected artifact, tree, or flat input.")
        self._retain_artifact(role, artifact)
        if artifact.source.product != profile.product or artifact.source.version != profile.version:
            reader.fail("context_mismatch", "$", "Artifact and declared profile contexts must agree.")
        if data["reconciliation"] is not None:
            reconciliation = reader.mapping(
                data["reconciliation"], "$", {"details", "accesses", "associations"},
            )
            details = self.read(reader.required(reconciliation, "details", "$"), role + "-details")
            accesses = self.read(reader.required(reconciliation, "accesses", "$"), role + "-accesses")
            raw = self.read(reader.required(reconciliation, "associations", "$"), role + "-associations")
            associations: list[DeviceReconciliationAssociation] = []
            for value in _array(raw, reader):
                row = reader.mapping(value, "$", {"source", "detail_record", "access_record", "acknowledgement"})
                for key in ("source", "detail_record", "access_record", "acknowledgement"):
                    reader.required(row, key, "$")
                associations.append(DeviceReconciliationAssociation(
                    _reference(row["source"], reader, "$"),
                    reader.reference(row["detail_record"], "$"),
                    None if row["access_record"] is None else reader.reference(row["access_record"], "$"),
                    None if row["acknowledgement"] is None else _acknowledgement(row["acknowledgement"], reader),
                ))
            artifact = reconcile_controller_devices(artifact, details, accesses, tuple(associations)).artifact
            self._retain_artifact(role, artifact)
        inventory = parse_controller_artifact(artifact.to_dict())
        if any(item.reference.controller_id != controller_id for item in inventory.objects):
            reader.fail("invalid_controller_identity", "$", "Inventory and declared controller identities must agree.")
        return inventory

    def declarations(self, manifest: dict[str, object]) -> PlanningDeclarations:
        reader = self.reader
        mappings = self.read(manifest["mappings"], "mappings")
        acknowledgements = tuple(
            _acknowledgement(item, reader)
            for item in _array(self.read(manifest["acknowledgements"], "acknowledgements"), reader)
        )
        policy = _versioned(
            self.read(manifest["policy"], "policy"),
            {"policy_id", "evidence_reference", "semantics_known_for", "comparison_rules"}, reader,
        )
        if policy["policy_id"] != "acknowledged-normalized-exact-v2":
            reader.fail("unsupported_policy", "$", "Expected the supported explicit controller comparison policy.")
        _evidence(policy["evidence_reference"])
        semantics = tuple(_reference(item, reader, "$") for item in _array(policy["semantics_known_for"], reader))
        rules: list[ControllerComparisonRule] = []
        for value in _array(policy["comparison_rules"], reader):
            rule = next((item for item in ControllerComparisonRule if value == item.value), None)
            if rule is None:
                reader.fail("invalid_comparison_rule", "$", "Only supported validated comparison rules are allowed.")
            rules.append(rule)
        completeness = _versioned(self.read(manifest["completeness"], "completeness"), {"trees"}, reader)
        trees: list[TreeName] = []
        for value in _array(completeness["trees"], reader):
            row = reader.mapping(value, "$", {"tree", "evidence_reference"})
            trees.append(_tree(reader.required(row, "tree", "$"), reader, "$"))
            _evidence(reader.required(row, "evidence_reference", "$"))
        return PlanningDeclarations(mappings, tuple(trees), semantics, tuple(rules), acknowledgements)

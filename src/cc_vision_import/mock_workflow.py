"""Explicitly synthetic read-to-plan integration; no execution or HTTP backend."""

from collections.abc import Callable
from dataclasses import dataclass, field

from ._contract_validation import ContractReader
from .artifacts import ConfigurationArtifact, validate_artifact
from .authentication import (
    AuthenticationRequest, CredentialReference, SecretResolver, SessionRole,
)
from .capabilities import ReadCapability, capabilities_for, require_capability
from .contracts import ContractValidationError
from .plans import ActionKind, MigrationPlan, create_plan
from .product_clients import CyberControllerClient, VisionClient
from .profiles import DestinationProfile, SourceProfile
from .sessions import SessionBackend, SessionManager
from .transport import TransportConfig


@dataclass(frozen=True)
class MockWorkflowSummary:
    object_count: int
    action_count: int
    blocked_actions: int
    conflict_actions: int
    plan_status: str
    stage: str = "offline-candidate"
    mock_only: bool = True
    compatibility_verified: bool = False
    writes_executed: int = 0


@dataclass(frozen=True)
class MockWorkflowResult:
    artifact: ConfigurationArtifact = field(repr=False)
    plan: MigrationPlan = field(repr=False)

    def summary(self) -> MockWorkflowSummary:
        return MockWorkflowSummary(
            len(self.artifact.objects), len(self.plan.actions),
            sum(item.kind == ActionKind.BLOCKED for item in self.plan.actions),
            sum(item.kind == ActionKind.CONFLICT for item in self.plan.actions),
            self.plan.validation.status,
        )


def _validated[T](action: Callable[[], T]) -> T:
    try:
        return action()
    except ContractValidationError as error:
        result = error.result
    # Existing parsers can chain URL errors containing supplied port text.
    raise ContractValidationError(result)


def build_mock_plan(
    source_declaration: object, destination_declaration: object, *,
    operation: ReadCapability, planning_request: object, exported_at: str,
    backend_factory: Callable[[], SessionBackend], resolver: SecretResolver,
    connect_timeout: float, read_timeout: float,
) -> MockWorkflowResult:
    """Use only injected simulated sessions and explicit synthetic mapping inputs."""
    reader = ContractReader("mock-workflow")
    source = _validated(lambda: SourceProfile.from_dict(source_declaration))
    destination = _validated(lambda: DestinationProfile.from_dict(destination_declaration))
    require_capability(source.product, source.version, operation, mock_only=True)
    capabilities_for(destination.product, destination.version, mock_only=True)
    if source.secret_ref is None or destination.secret_ref is None:
        reader.fail("missing_reference", "$", "Both simulated sessions require explicit credential references.")
    source_config = TransportConfig(
        base_url=source.base_url, connect_timeout=connect_timeout, read_timeout=read_timeout,
    )
    destination_config = TransportConfig(
        base_url=destination.base_url, connect_timeout=connect_timeout, read_timeout=read_timeout,
    )
    with SessionManager(backend_factory, resolver, mock_only=True) as manager:
        for role, profile, config in (
            (SessionRole.SOURCE, source, source_config),
            (SessionRole.DESTINATION, destination, destination_config),
        ):
            reference = source.secret_ref if role == SessionRole.SOURCE else destination.secret_ref
            assert reference is not None
            manager.initialize(
                AuthenticationRequest(
                    role, profile.product, profile.version, CredentialReference(reference),
                ),
                config,
            )
            manager.authenticate(role)
        if source.product == "vision":
            result = VisionClient(manager, SessionRole.SOURCE, source.version).list_ldap_permissions()
        else:
            client = CyberControllerClient(manager, SessionRole.SOURCE, source.version)
            result = (
                client.export_physical_tree() if operation == ReadCapability.PHYSICAL_TREE
                else client.export_organization_tree()
            )
        artifact = result.to_artifact(exported_at=exported_at)
        validation = validate_artifact(artifact.to_dict())
        if validation.status != "valid":
            raise ContractValidationError(validation)
        plan = _validated(lambda: create_plan(artifact.to_json().encode("utf-8"), planning_request))
        if (
            plan.destination.product != destination.product
            or plan.destination.version != destination.version
            or plan.destination.base_url.rstrip("/") != destination.base_url.rstrip("/")
        ):
            reader.fail("context_mismatch", "$.destination", "Plan destination must match the simulated destination profile.")
        return MockWorkflowResult(artifact, plan)

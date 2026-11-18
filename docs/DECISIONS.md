# Architecture Decision Register

Date: 2026-11-18

## Approval rules

The project owner approved the **architectural direction of ADR-001 through
ADR-009, including amendments, on 2026-11-17**, as recorded in
[PROGRESS.md](PROGRESS.md). Architectural approval does not authorize all
proposed implementations or certify product compatibility. Original proposal
wording below is retained as design context; approval statuses reflect the
accepted direction, not completion of every described feature.

The owner separately accepted **CCV-003-A/B/C's implemented mock-only scope on
2026-11-17**, under the conditions recorded below. The read-only legacy boundary,
no secret disclosure, and no live operations without separate authorization
remain in force. Further milestones require separate authorization.

The owner also accepted **CCV-004-A's completed offline-only scope on
2026-11-17**, including Option 1 duplicate-name handling. Its Category B
CREATE-planning limitation was accepted as planned CCV-004-B scope; that A
decision did not authorize B implementation. B was subsequently separately
authorized and its implemented offline-only scope was owner-accepted on
**2026-11-18**, including the serialization-fidelity correction. See the
separate dated acceptance records below.

The owner separately accepted **CCV-004-C1's implemented offline-only scope on
2026-11-18** after technical review. This includes legacy export adapters and
their artifact/comparison/candidate-plan integration, not real export/import
execution, live compatibility, or authorization to begin C2.

The owner separately accepted **CCV-004-C2's completed offline-only scope on
2026-11-18**, including both HIGH-severity safety corrections. This includes
reconciliation, bound universal acknowledgements, protected provenance, and safe
controller-specific planning, not live compatibility, execution, production
configuration changes, or authorization to begin C3.

| ID | Proposed decision | Approval status | Related milestone |
| --- | --- | --- | --- |
| ADR-001 | Modular Python master CLI with explicit module registry | Architectural direction approved by owner, 2026-11-17 | CCV-002, CCV-007 |
| ADR-002 | Product-specific clients over shared transport and explicit sessions | Direction approved; implemented CCV-003 mock-only scope accepted, 2026-11-17 | CCV-003 |
| ADR-003 | Versioned artifacts, destination mappings, and plan integrity | Direction approved; A offline scope accepted, 2026-11-17; B/C1 integration and C2 reconciliation/provenance/planning integrity accepted offline-only, 2026-11-18 | CCV-002, CCV-004 |
| ADR-004 | Separate offline planning, online preflight, approval, apply, and verification | Direction approved, 2026-11-17; B and C2 offline planning/safety gates accepted, 2026-11-18; live/apply stages not authorized | CCV-002, CCV-007 |
| ADR-005 | Preserve semantics; block ambiguous or unsafe transformations | Direction approved; A preservation/Option 1 accepted, 2026-11-17; B/C1 fidelity controls and C2 qualified associations/acknowledgements/validated exclusions accepted offline-only, 2026-11-18 | CCV-004 through CCV-006 |
| ADR-006 | Capability/evidence gating by product and version | Direction approved; synthetic isolation accepted, 2026-11-17; real qualification pending | CCV-003, CCV-008 |
| ADR-007 | Secure transport and externalized secrets with redacted reporting | Direction approved; implemented CCV-003 mock-only controls accepted, 2026-11-17 | CCV-002, CCV-003 |
| ADR-008 | Initial utility exclusions and offline-first verification | Direction approved; CCV-003 offline acceptance recorded, 2026-11-17; live qualification pending | CCV-001 through CCV-008 |
| ADR-009 | Default import conflict handling and journal-based partial-import recovery | Architectural direction approved by owner, 2026-11-17; execution/journal implementation deferred | CCV-004 through CCV-007 |

## Owner implementation acceptance - CCV-003, 2026-11-17

**Owner:** project owner, by explicit decision in the project conversation.
**Decision:** accept completion of CCV-003-A, CCV-003-B, and CCV-003-C for
their implemented **mock-only** scope. This is an implementation acceptance
record under the existing ADRs, not a new production-compatibility decision.

Accepted scope:

- Shared injected transport and security/error/retry contracts.
- Distinct mocked product authentication strategies, injected secret resolution,
  separate source/destination sessions, expiration and local cleanup, including
  the reviewed cleanup correction.
- Three source-observed reads and a synthetic artifact/mapping/offline-plan
  integration with redacted reporting. `0.0-test` remains development/test-only,
  requires explicitly declared mock backends, and is separate from the empty
  production capability catalogue. No real product/version is enabled.

Accepted evidence: **130 automated tests passed**, **zero guarded network
attempts**, no blocking defects identified in final technical review, and
synthetic capabilities isolated from production. Final review command:
`python -B -m unittest discover -s tests -v`; 130 passes in 37.927 seconds.
See [E-012](PROGRESS.md#e-012---ccv-003-owner-acceptance-2026-11-17).
These are existing review results, not tests rerun for this documentation update.

Conditions: live compatibility and qualification remain **pending**. This
acceptance authorizes no live API requests, production connectivity, real
migration execution, external configuration changes, or claims of verified
Vision/Cyber Controller compatibility. Response schemas and identity/semantic
assertions remain synthetic/unverified; the nominal mock marker is a trusted
developer assertion, not a sandbox. No concrete HTTP/production secret backend,
destination preflight, apply/verification/journaling implementation, or CCV-004
is accepted as implemented or authorized to begin. Broader roadmap scope remains
deferred. No application code or Git operations are part of this decision record.

## Owner implementation acceptance - CCV-004-A, 2026-11-17

**Owner:** project owner, by explicit decision in the project conversation.
**Decision:** accept **CCV-004-A for its completed offline-only scope** under
ADR-003/ADR-005. This later, separate acceptance supersedes the earlier
CCV-003 record's exclusion of A only for the scope stated here; it does not
accept the remainder of CCV-004 as implemented.

Accepted scope and evidence:

- Normalized controller object/hierarchy/source-reference contracts and
  separate Physical/Organization identities.
- Source objects and unknown configuration fields preserved. Option 1 retains
  duplicate-name objects in artifacts, reports same-type sibling-name ambiguity
  separately, and permits explicit qualified mappings to resolve those objects.
  Names alone never establish destination identity.
- Explicit controller/tree/type/stable-ID mappings against separately supplied
  destination inventories, hierarchy/dependency checks, no automatic source-ID
  reuse, and no legacy script modifications.
- **166 automated tests passed**, **zero guarded network attempts**.
  Accepted E-014 command: `python -B -m unittest discover -s tests -v`,
  source on `PYTHONPATH`; exit `0`, **38.012 seconds**. These are existing
  verification results, not tests rerun for this documentation update.
  See [E-015](PROGRESS.md#e-015---ccv-004-a-owner-acceptance-2026-11-17).

**CREATE-planning assessment: Category B**, accepted by the owner:
minor controller-specific contract extensions are required and belong to
**planned CCV-004-B scope**. This is not a blocker to A acceptance or a claim
that controller CREATE planning is already implemented.

Source inventory validity does not require destination mappings. Generic
contracts already represent missing destinations and dependencies, but A's
strict controller resolver requires existing destination objects. The smallest
planned extension is a controller-specific planning validator alongside that
resolver, not relaxation of existing-target resolution:

- Distinguish an explicitly established missing object from unresolved or
  ambiguous identity.
- Permit non-root CREATE candidates to depend on an explicitly mapped existing
  destination parent or another parent CREATE candidate.
- Leave destination IDs unassigned until actual destination creation; use
  logical mapping/dependency references, never fabricated or copied source IDs.
- Require existing destination roots to be explicitly resolved.

**Conditions:** no live API compatibility, real controller schema validation,
destination preflight, or production import functionality is claimed. Synthetic
fixtures and supplied inventories establish local contract consistency, not
verified real product identity, completeness, credential portability, or
compatibility. Live qualification remains pending.

CCV-004-B implementation remains **not authorized and not started**. No live
requests, real migrations, concrete backend, external configuration changes,
application-code changes, or Git operations follow from this acceptance.

The paragraph above records the boundary of the 2026-11-17 A decision.
The later B authorization and acceptance below supersede that boundary only for
B's explicitly stated offline scope.

## Owner implementation acceptance - CCV-004-B, 2026-11-18

**Owner:** project owner, by explicit decision in the project conversation.
**Decision:** accept **CCV-004-B for its implemented offline-only scope** under
ADR-003/ADR-004/ADR-005, including the reviewed serialization-fidelity correction.
This is implementation acceptance, not live product qualification or migration
execution authorization.

Accepted capabilities:

- Offline semantic comparison with CREATE/SKIP/CONFLICT/BLOCKED classification.
- Explicit per-object comparison-policy acknowledgement; conservative handling
  of unknown semantics and unresolved credentials.
- Explicit missing-object planning and parent dependency validation, including
  planned parents, independently resolved existing roots, and no fabricated
  destination IDs. The strict existing-target resolver remains unchanged.
- Deterministic integrity-bound schema-2 controller plans, recorded policy/
  evidence, and redacted reporting.
- Order-sensitive controller configuration preserved through the standard
  artifact serialization path; unrelated generic sorted-key serialization
  compatibility maintained.

Accepted evidence: **220 automated tests passed**, **zero guarded network
attempts**, the confirmed false-SKIP serialization defect corrected, and
**no blocking defects remain in the reviewed scope**, as stated by the owner.
The E-018 verification command was
`python -B -m unittest discover -s tests -v`, with source on `PYTHONPATH`;
exit `0`, **77.180 seconds**. These are existing verification results, not tests
rerun for this documentation-only acceptance update.
See [E-019](PROGRESS.md#e-019---ccv-004-b-owner-acceptance-2026-11-18)
and the linked implementation evidence.

Conditions and limitations:

- Historical ordering lost through earlier serialization cannot be reconstructed.
- Previously bound artifact hashes cannot be reused for reserialized data;
  retain exact bound inputs or regenerate and reverify affected candidates.
- Product-specific comparison semantics remain unverified against live
  controllers. Policy acknowledgement is for offline comparison only.
- Destination completeness is an offline assertion, not live preflight evidence.
- No real migration execution, configuration writes, live connectivity, API
  requests, or claims of verified Vision/Cyber Controller compatibility follow
  from this acceptance. Broader controller/credential scope remains unaccepted.

CCV-004-C remains **not authorized and not started**. No application-code
changes or Git operations are part of this acceptance record.

That statement records the boundary of the earlier B acceptance. The separate
C1 authorization and acceptance below supersede it only for C1's stated scope.

## Owner implementation acceptance - CCV-004-C1, 2026-11-18

**Owner:** project owner, by explicit decision in the project conversation.
**Decision:** accept **CCV-004-C1 for its implemented offline-only scope**
under the existing artifact, fidelity, and operation-gating ADRs. This is
implementation acceptance, not live API/schema qualification.

Accepted functionality:

- Recursive Cyber Controller export adapters.
- Flat export adapters requiring explicit source-root/controller/tree context.
- Hierarchy and source-native provenance preservation.
- Versioned artifact generation and order-preserving controller serialization.
- Offline comparison integration and deterministic candidate-plan generation.

Accepted evidence:

- **244 automated tests passed** and **five additional guarded review probes
  passed**.
- **Zero guarded network attempts**.
- No confirmed acceptance-blocking defects.
- Configuration preservation verified; incomplete exports fail safely.
- Legacy scripts remain unchanged.

The final read-only review ran
`python -B -m unittest discover -s tests -v`, source on `PYTHONPATH`;
244 passes, exit `0`, **41.198 seconds**. Five additional read-only guarded
probes passed in **0.229 seconds**, covering incomplete flat access, generic
planning of invalid artifacts, independent destination identities/cross-tree
rejection, serialization/integrity, and copy/report safety.
See [E-021](PROGRESS.md#e-021---ccv-004-c1-owner-acceptance-2026-11-18).
These are existing review results, not tests rerun for this documentation update.

Limitations:

- Real API schemas remain unverified.
- Nonempty device access does not establish completeness.
- Credential portability remains unverified.
- No live product compatibility is claimed.
- No real export/import execution is authorized.

Physical/Organization identities, explicit destination mappings, incomplete-
artifact rejection, secret protection, and the synthetic-only capability
boundary remain unchanged. No live connectivity, configuration writes, new
production capabilities, or broader controller/credential implementation follows
from this acceptance.

CCV-004-C2 remains **not authorized and not started**. Only this register and the
progress tracker are updated; no application code or Git operations are involved.

## Owner policy decision - CCV-004-C2 access acknowledgement, 2026-11-18

The preceding C1 acceptance boundary is historical. The owner separately
authorized offline-only C2 and approved **Option 1**: explicit per-device offline
acknowledgement and a protected opaque evidence reference before access
configuration becomes eligible for migration planning. In the subsequent scope
clarification, the owner selected **all controller devices carrying access
configuration**, including direct C1/A/B inputs, not only C2-reconciled devices.

The acknowledgement must bind qualified identity, relevant source snapshot,
device-access data, and policy version. Changed access invalidates it. Missing,
mismatched, or stale declarations block affected controller planning operations;
structurally incomplete data stays available as protected diagnostic artifacts.
No acknowledgement overrides malformed hierarchy, conflicting identities,
missing required fields, unsafe credentials, or unresolved sensitive references.

Evidence references must be opaque local catalogue identifiers, not credentials,
session tokens, addresses, or raw configuration. Structural validation, offline
acknowledgement, official schema verification, and live compatibility remain
separate. Acknowledgement establishes neither access completeness nor credential
portability and never authorizes actual imports.

Implementation/evidence: [E-023](PROGRESS.md#e-023---ccv-004-c2-bound-access-acknowledgement-policy-2026-11-18).
This historical record approves policy, not implementation. C2 implementation
acceptance was pending at that checkpoint; the separate owner acceptance below
supersedes that pending status only for the completed offline scope. C3 and live
work remain unauthorized and not started.

## Owner implementation acceptance - CCV-004-C2, 2026-11-18

**Owner:** project owner, by explicit decision in the project conversation.
**Decision:** accept **CCV-004-C2 for its completed offline-only scope**, including
both HIGH-severity safety corrections, under the existing artifact, identity,
semantics, and operation-gating ADRs. This is implementation acceptance, not live
product qualification or execution authorization.

Accepted evidence:

- **291 automated tests passed**.
- **Zero guarded network attempts**.
- No remaining confirmed acceptance blockers.
- Both HIGH-severity findings corrected and verified.

Accepted functionality:

- Explicit device-detail/access reconciliation.
- Qualified one-to-one identity associations.
- Universal device-access acknowledgement enforcement.
- Stale acknowledgement rejection.
- Protected source provenance.
- Safe integration with controller-specific planning.
- Explicit rejection of generic controller planning.
- Validated comparison exclusions.

The accepted safety corrections require explicitly resolved existing destination
roots, prevent forbidden root CREATE through generic planning/verification, and
preserve unknown root/site configuration during comparison. Forged root CREATE
plans remain rejected even after hashes are recomputed. Comparison exclusions
apply only under the supported validated provenance rules.

Accepted command: `python -B -m unittest discover -s tests -q`,
with `PYTHONPATH=src`; **291 passes in 88.461 seconds**, exit 0.
See [E-025](PROGRESS.md#e-025---ccv-004-c2-acceptance-blocking-planning-corrections-2026-11-18)
for implementation/test evidence and
[E-026](PROGRESS.md#e-026---ccv-004-c2-owner-acceptance-2026-11-18)
for this owner decision. These are existing results, not tests rerun for the
documentation update. Guarded network assertions are not OS-level isolation.

Mandatory limitations:

- No live product compatibility is established.
- Access completeness and credential portability remain unverified.
- Acknowledgement authorizes offline planning only.
- No real import execution is authorized.
- Previously generated generic controller plans must be regenerated using
  controller-specific APIs.
- No production configuration changes are authorized.

This acceptance supersedes earlier C2 implementation-acceptance-pending labels
only for the completed offline scope. It does not authorize broader CCV-004 work,
API requests, real HTTP/secret backends, Git operations, or CCV-004-C3.
C3 remains **unauthorized and not started**. Only this register and the progress
tracker are updated; no application code or tests are changed.

## ADR-001 - Modular Python controller

**Decision proposed:** One master CLI orchestrates independently testable migration
modules through an explicit registry. Do not implement a monolithic script or
dynamic plugin loader initially.

**Rationale:** Existing scripts duplicate login/configuration logic and lack a
master workflow. A small registry supports the known domains without premature
plugin infrastructure.

**Consequences:** Shared contracts must be agreed early. Modules remain separable,
but orchestration and reporting become consistent. CLI library, package name,
Python baseline, and exact layout remain undecided.

**Approval status:** Architectural direction approved by the project owner,
2026-11-17; future implementation remains separately scoped.

## ADR-002 - Separate products, shared transport

**Decision proposed:** Separate Vision and Cyber Controller clients share HTTP
transport mechanics, not assumed endpoint compatibility. A session manager owns
each authenticated connection for its complete lifetime.

**Rationale:** Shared path prefixes and legacy naming do not establish identical
schemas or authentication requirements. Legacy session ownership is inconsistent.

**Consequences:** Some adapters may look similar until evidence justifies sharing.
Authentication/logout behavior is product/version-specific. Unknown logout paths
remain unknown; closing local sessions does not prove remote logout.

**Approval status:** Direction approved by the project owner, 2026-11-17;
implemented CCV-003 mock-only scope accepted on that date. Live compatibility
and qualification remain pending.

## ADR-003 - Versioned artifacts and identity mapping

**Decision proposed:** Use a versioned normalized JSON envelope with explicit
legacy adapters and destination identity maps. Source IDs remain provenance.
Give every plan an ID, schema version, and SHA-256 digest of deterministically
serialized approval-relevant content. Bind the exact source artifact checksum,
destination identity/product/version, object mappings, dependencies, planned
actions/changes, conflict policy, and destination preconditions to that digest.

**Rationale:** Legacy exports combine source IDs, parent names, and device access.
Reusing IDs or resolving by an ambiguous name can target the wrong object.

**Consequences:** Legacy files need validation/adaptation, not blind reuse.
Tree-qualified hierarchy and device identity rules need review. Sanitized sample
schemas and product versions are prerequisites. Secret fields require separate
policy; normalization must not silently lose meaningful settings.
Approval records bind the plan ID/digest and permitted actions. A profile name
alone is not destination identity. Changed inputs invalidate approval; verify
checksums and preconditions before apply/resume. Digests do not authenticate their
author, so plan/approval/journal storage needs access protection. Plans contain
secret references/version identifiers, not resolved secrets; unversioned secret
values cannot be claimed to have verified integrity.

**Approval status:** Architectural direction approved by the project owner,
2026-11-17; acceptance of offline contracts does not authorize real migrations.

## ADR-004 - Explicit operation and approval gates

**Decision proposed:** Keep export, offline validation/transformation, offline
candidate planning, online destination preflight, approval, apply, and post-import
verification distinct. Offline planning performs no network requests; destination
snapshots only support provisional comparisons. Separately authorized online
preflight performs reads to confirm identity, mappings, capabilities, conflicts,
and current-state preconditions without configuration writes.

Finalize the plan digest after preflight and bind approval to that exact plan.
Recheck relevant state before writes; drift requires replanning and approval.
An online preflight dry-run must be explicit, not an implicit part of offline work.

**Rationale:** Backup/export is not import approval; dry-run must not mutate
configuration. HTTP acceptance is not completed migration.

**Consequences:** More explicit operator steps, safer failure handling, and
testable boundaries. Async completion requires an evidenced mechanism; otherwise
the result stays accepted/unverified. Neither offline planning nor online
preflight is import approval. No transactional rollback promise; recovery follows
ADR-009.

**Approval status:** Architectural direction approved by the project owner,
2026-11-17; online preflight, approval/apply, and post-import execution remain
unimplemented and unauthorized.

## ADR-005 - Preserve configuration and authorization intent

**Decision proposed:** Fail affected operations on unresolved parents, destination
IDs, LDAP role/scope mappings, unsupported fields, or uncertain task references.
Require explicit transformations rather than silent substitutions.

**Rationale:** Legacy root fallback, source-ID reuse, forced device locking, and
all-scope LDAP retry can change semantics or authorization.

**Consequences:** Unsafe legacy behavior is intentionally not preserved in the
proposed design; useful migration capabilities remain the goal. Imports may block
until mappings are provided. Any intentional scope, locking, hierarchy, or
activation change must be visible in the plan and separately approved.

**Approval status:** Architectural direction approved by the project owner,
2026-11-17; domain implementation requires separate scope and evidence.

## ADR-006 - Product/version capability and evidence gates

**Decision proposed:** Track source-observed, officially documented, mock-tested,
and live-tested evidence independently for each capability and product/version.
Unknown capabilities cannot silently fall back to another product's client.

**Rationale:** The current API inventory is static evidence only; scheduler paths
are absent and no supported-version matrix is available.

**Consequences:** Coverage will initially be incomplete and explicit. Official
documentation does not substitute for local implementation tests; mock tests do
not certify live compatibility. Lab qualification requires separate authorization.

**Approval status:** Direction approved by the project owner, 2026-11-17;
implemented synthetic capability isolation accepted within CCV-003. Real
product/version compatibility and live qualification remain pending.

## ADR-007 - Secure connections, secrets, and reporting

**Decision proposed:** Default to verified TLS, bounded timeouts, secret references,
separate source/destination credentials, and redacted structured logs/results.
Avoid automatic write retries, including after authentication renewal.

**Rationale:** Legacy code suppresses TLS warnings, omits timeouts, and prints
secrets/session identifiers. Lost responses can make write outcomes uncertain.

**Consequences:** Trusted CA configuration and a secret-provider policy are needed.
Some legacy exports may require manual handling or re-entry of credentials.
Reports must avoid raw payloads and operational identifiers by default. Recovery
requires reconciliation before retry; sensitive artifacts need access/retention
rules. Secret backend, storage protection, and exception procedures remain open.

**Approval status:** Direction approved by the project owner, 2026-11-17;
implemented mock-only controls accepted within CCV-003. Production backend,
secret-provider selection, and operational qualification remain open.

## ADR-008 - Initial scope and staged qualification

**Decision proposed:** Start with controller objects/access, credential
transformation, LDAP permissions, and scheduled tasks. Keep document-store
restoration and Docker/cron helpers out of the initial application. Use offline
tests first, then separately approved lab qualification.

**Rationale:** Auxiliary utilities have different risk/ownership boundaries and
do not establish Vision/CC migration requirements. Authorization was
documentation-only at proposal time; the later mock-only acceptance above does
not authorize domain migration implementation or live qualification.

**Consequences:** Inventory coverage is broader than implementation scope.
Deployment and document restoration require later explicit scope decisions.
Offline evidence cannot justify production-readiness claims.

**Approval status:** Direction approved by the project owner, 2026-11-17;
CCV-003 mock-only completion accepted. Live qualification remains pending.

## ADR-009 - Import conflict and recovery policy

**Decision proposed:** Apply these defaults after identity resolution and
destination comparison:

- Create missing objects only under an approved import plan.
- Skip semantically identical objects and record comparison evidence.
- Report differences without modifying existing objects by default.
- Block ambiguous identities, uncertain equivalence, unresolved mappings, and
  affected dependent writes.
- Retain destination-only objects. Never delete or overwrite without separate
  explicit approval bound to the exact objects/actions/changes in a revised
  plan and an evidence-backed capability. Default import approval is insufficient.

Preserve partial-import progress in a durable, append-only structured result
journal. Bind entries to the plan ID/digest, destination, object/action/attempt,
dependencies, timestamps, outcomes, and verification/reconciliation evidence.
Persist intent before dispatch and outcome afterward; omit secrets/raw payloads
and protect sensitive identifiers. Failure to journal intent blocks the write;
journaling failure after dispatch stops further writes and exposes an uncertain
outcome.

Resume through authorized destination reconciliation, not wholesale replay.
Recheck dependencies and reconcile uncertain writes before any retry. Confirmed
intended state means no replay; confirmed safe non-completion permits a proposed
retry only with valid approval and fresh preconditions. Absence alone does not
prove failure while asynchronous work may remain pending. Differences or unknown
state block retry pending resolution. Plan changes require renewed approval;
recovery does not authorize rollback, deletion, or compensating overwrites.

**Rationale:** Name matches do not establish equivalence, and partial failure or
lost responses can leave successful changes on the destination. Blind retry can
duplicate objects or overwrite configuration; blanket rollback can damage
pre-existing state.

**Consequences:** Operators receive explicit difference/blocking reports instead
of automatic replacement. Durable journal storage and destination read-back
capabilities are prerequisites for resumable imports. Accepted/unverified and
indeterminate states remain distinct from verified completion. Recovery may
require manual resolution where evidence is insufficient. Journal schema,
durability/access controls, and retention need implementation design and approval.

**Approval status:** Architectural direction approved by the project owner,
2026-11-17; apply/reconciliation and durable journal implementation remain
deferred and require separate authorization.

## Open decisions requiring owner input

| Topic | Missing decision/evidence | Blocks |
| --- | --- | --- |
| Compatibility | Real supported products/versions, migration directions, official references; synthetic mocks are not qualification | Real-version enablement and qualification claims |
| Runtime/tooling | Development baseline is Python 3.13.14/Windows/standard library; broader runtime/OS support and packaging remain open | Broader support/distribution, not the accepted offline implementation |
| Identity | Tree-qualified site/device matching and same-device behavior across trees | Safe create/update plans |
| Secrets/artifacts | Provider, masking/encryption portability, permitted artifact contents, retention | Credential/access migration |
| Plan integrity | Destination identity evidence, deterministic serialization, protected approval binding, and secret reference versioning | Trustworthy apply/resume gates |
| Conflicts/recovery | ADR-009 direction approved; journal durability/access/retention and reconciliation evidence remain open | Safe partial-import recovery |
| LDAP | Destination role/group/policy mapping and device-lock intent | Authorization-preserving imports |
| Scheduler | Sanitized API paths, task schemas/types, timezone and activation policy | Scheduler contracts |
| Scope | Utility exclusions/direction approved; future domain or utility implementation needs separate authorization | Future scope expansion, not accepted CCV-001/CCV-003 scope |
| Qualification | Lab ownership, authorization process, product/version test coverage | Live testing and release readiness |

Preserve the accepted CCV-003 mock-only checkpoint. No CCV-004, real backend,
live qualification, or migration implementation begins without separate
authorization. See [PROGRESS.md](PROGRESS.md) for the persistent stop/checkpoint.

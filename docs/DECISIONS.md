# Architecture Decision Register

Date: 2026-11-17

## Approval rules

All ADRs below are **Proposed — pending owner approval**, not accepted decisions.
Authorization to write documentation does not approve the application design.
The read-only legacy boundary, no live operations without approval, no secret
disclosure are existing constraints, not new proposals awaiting approval. This
amendment authorizes changes only to [ARCHITECTURE.md](ARCHITECTURE.md) and this
register; it does not authorize implementation.

For approval, record the owner, date, accepted scope or amendments, and any
conditions. No approving owner/date is recorded yet.

| ID | Proposed decision | Approval status | Related milestone |
| --- | --- | --- | --- |
| ADR-001 | Modular Python master CLI with explicit module registry | Proposed; pending owner | CCV-002, CCV-007 |
| ADR-002 | Product-specific clients over shared transport and explicit sessions | Proposed; pending owner | CCV-003 |
| ADR-003 | Versioned artifacts, destination mappings, and plan integrity | Proposed — pending owner approval | CCV-002, CCV-004 |
| ADR-004 | Separate offline planning, online preflight, approval, apply, and verification | Proposed — pending owner approval | CCV-002, CCV-007 |
| ADR-005 | Preserve semantics; block ambiguous or unsafe transformations | Proposed; pending owner | CCV-004 through CCV-006 |
| ADR-006 | Capability/evidence gating by product and version | Proposed; pending owner | CCV-003, CCV-008 |
| ADR-007 | Secure transport and externalized secrets with redacted reporting | Proposed; pending owner | CCV-002, CCV-003 |
| ADR-008 | Initial utility exclusions and offline-first verification | Proposed; pending owner | CCV-001 through CCV-008 |
| ADR-009 | Default import conflict handling and journal-based partial-import recovery | Proposed — pending owner approval | CCV-004 through CCV-007 |

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

**Approval status:** Proposed; owner/date pending.

## ADR-002 - Separate products, shared transport

**Decision proposed:** Separate Vision and Cyber Controller clients share HTTP
transport mechanics, not assumed endpoint compatibility. A session manager owns
each authenticated connection for its complete lifetime.

**Rationale:** Shared path prefixes and legacy naming do not establish identical
schemas or authentication requirements. Legacy session ownership is inconsistent.

**Consequences:** Some adapters may look similar until evidence justifies sharing.
Authentication/logout behavior is product/version-specific. Unknown logout paths
remain unknown; closing local sessions does not prove remote logout.

**Approval status:** Proposed; owner/date pending.

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

**Approval status:** Proposed — pending owner approval. Owner/date pending.

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

**Approval status:** Proposed — pending owner approval. Owner/date pending.

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

**Approval status:** Proposed; owner/date pending.

## ADR-006 - Product/version capability and evidence gates

**Decision proposed:** Track source-observed, officially documented, mock-tested,
and live-tested evidence independently for each capability and product/version.
Unknown capabilities cannot silently fall back to another product's client.

**Rationale:** The current API inventory is static evidence only; scheduler paths
are absent and no supported-version matrix is available.

**Consequences:** Coverage will initially be incomplete and explicit. Official
documentation does not substitute for local implementation tests; mock tests do
not certify live compatibility. Lab qualification requires separate authorization.

**Approval status:** Proposed; owner/date pending.

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

**Approval status:** Proposed; owner/date pending.

## ADR-008 - Initial scope and staged qualification

**Decision proposed:** Start with controller objects/access, credential
transformation, LDAP permissions, and scheduled tasks. Keep document-store
restoration and Docker/cron helpers out of the initial application. Use offline
tests first, then separately approved lab qualification.

**Rationale:** Auxiliary utilities have different risk/ownership boundaries and
do not establish Vision/CC migration requirements. Current authorization is
documentation-only.

**Consequences:** Inventory coverage is broader than implementation scope.
Deployment and document restoration require later explicit scope decisions.
Offline evidence cannot justify production-readiness claims.

**Approval status:** Proposed; owner/date pending.

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

**Approval status:** Proposed — pending owner approval. Owner/date pending.

## Open decisions requiring owner input

| Topic | Missing decision/evidence | Blocks |
| --- | --- | --- |
| Compatibility | Supported products, versions, migration directions, official references | Client contracts and qualification claims |
| Runtime/tooling | Python minimum, supported OS, packaging, CLI/test/dependency choices | CCV-002 implementation |
| Identity | Tree-qualified site/device matching and same-device behavior across trees | Safe create/update plans |
| Secrets/artifacts | Provider, masking/encryption portability, permitted artifact contents, retention | Credential/access migration |
| Plan integrity | Destination identity evidence, deterministic serialization, protected approval binding, and secret reference versioning | Trustworthy apply/resume gates |
| Conflicts/recovery | Accept ADR-009 defaults; journal durability/access/retention and reconciliation evidence | Safe partial-import recovery |
| LDAP | Destination role/group/policy mapping and device-lock intent | Authorization-preserving imports |
| Scheduler | Sanitized API paths, task schemas/types, timezone and activation policy | Scheduler contracts |
| Scope | Accept proposed utility exclusions and milestone boundaries | Final CCV-001 acceptance |
| Qualification | Lab ownership, authorization process, product/version test coverage | Live testing and release readiness |

The next action is architecture review, not implementation. See
[PROGRESS.md](PROGRESS.md) for the persistent stop/checkpoint.

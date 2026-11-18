# Development Roadmap

Date: 2026-11-18
Status: **CCV-001 architectural baseline approved; CCV-002 completion confirmed
by the owner; CCV-003-A/B/C implemented mock-only scope owner-accepted on
2026-11-17. CCV-004-A/B/C1/C2 completed offline scopes are owner-accepted.
Separately authorized CCV-004-C3 controller-only offline orchestration is
implemented and offline-verified; its owner acceptance is pending.**
Broader/future milestones remain proposed/not authorized. Live product
compatibility and qualification are explicitly pending.

Priorities: P0 = foundation/safety gate; P1 = initial migration functionality;
P2 = release-readiness expansion. Ordering does not authorize implementation.
Each milestone requires explicit authorization and separate implementation and
verification tracking in [PROGRESS.md](PROGRESS.md).

CCV-000 static discovery is complete. It is the prerequisite to CCV-001, not a
runtime or API certification.

## Milestones

| ID | Milestone | Priority | Dependencies | Current state |
| --- | --- | --- | --- | --- |
| CCV-001 | Project Foundation | P0 | CCV-000 | Static baseline and architectural direction owner-approved, 2026-11-17; deferred evidence remains in tracker. |
| CCV-002 | Application skeleton, profiles, and offline contracts | P0 | CCV-001 approval; runtime/tooling decisions | A/B/C implemented and offline-verified; parent completion/local commit confirmed by owner, not inspected here. |
| CCV-003 | Shared transport, product clients, sessions, and mocked read-to-plan slice | P0 | CCV-002; source evidence; explicit synthetic version/backend restrictions | Implemented mock-only A/B/C scope owner-accepted, 2026-11-17; 130 tests, zero guarded attempts, no blocking review defects; live qualification pending. |
| CCV-004 | Controller objects, device access, credential transformation | P1 | CCV-002, CCV-003; identity and secret-policy decisions | A/B/C1/C2 accepted offline-only; C3 separately authorized 2026-11-18, implemented/offline-verified with 312 passing tests and zero guarded attempts; C3 owner acceptance pending. Broader credential/apply work remains unauthorized. |
| CCV-005 | LDAP permission migration | P1 | CCV-002, CCV-003; approved destination reference mappings | Not started; not authorized. |
| CCV-006 | Scheduled-task migration | P1 | CCV-002, CCV-003; resolved paths and task-type contracts | Not started; not authorized. |
| CCV-007 | Integrated orchestration, comparison, and reporting | P0 | CCV-003 mocked slice; readiness-verified subset of CCV-004/005/006 approved for integration | Not started; not authorized. |
| CCV-008 | Compatibility qualification and release readiness | P2 | CCV-007; separately authorized lab access and acceptance scope | Not started; not authorized. |
| CCV-009 | API discovery and automation expansion workstream | P1 | CCV-001 approval; explicit discovery scope and evidence-access authorization | Not started; not authorized. |

Milestone numbers identify workstreams, not a rigid execution order. CCV-009 is
proposed to run alongside approved development after the CCV-001 gate, not wait
until CCV-008. Its findings may supply readiness evidence without requiring the
entire discovery workstream to finish before a module starts.

## Readiness-driven sequencing and early workflow

Status: **Architectural direction approved on 2026-11-17**; each implementation
slice still requires separate authorization. CCV-003 acceptance is limited to
the narrower implemented scope below.

Keep detailed sequencing within and across CCV-004/005/006 flexible until each
selected slice has verified API/schema readiness: approved source/documentation
evidence, identified product/version limits, validated synthetic schema fixtures,
identity/dependency rules, and explicit unresolved-capability boundaries. This
readiness does not imply live compatibility. Record the evidence and obtain
approval for the selected scope before implementation.

Shared artifact/plan/result contracts were implemented in CCV-002. The narrower
CCV-003 authorization and acceptance connect simulated sessions and three
source-observed reads to versioned artifacts, explicit mappings, offline
candidate planning, integrity checks, cleanup, and a redacted summary.
All backend responses and credentials are synthetic; no real backend or write
path exists. Synthetic contracts are not evidence of vendor compatibility.

The original broader proposal to model online preflight, approval, apply,
post-import verification, partial-import reconciliation, and durable journaling
is **deferred**, not part of CCV-003's accepted implementation. Those stages
require separate scope/authorization even if a future proposal remains mocked.

CCV-007 extends that slice across the readiness-verified modules approved for
integration; it need not wait for every proposed domain. Deferred modules and
coverage gaps remain explicit. CCV-008 qualifies only the owner-approved release
scope, not every planned capability. Runtime plans still enforce actual
dependencies and mappings, including pre-existing destination objects.

## CCV-001 - Project Foundation

Deliverables: the six authorized project documents, evidence-qualified API
inventory, proposed architecture/decisions, and persistent checkpoint.

Acceptance:
- Inventory accounts for all 22 scripts and identifies nine apparent duplicate
  pairs. Byte equality has not yet been established through hashing for this
  acceptance baseline; record hash verification as pending, not verified equality.
- API count distinguishes 12 concrete operations from four unresolved references.
- Architecture separates products, sessions, domains, plan/apply, and verification.
- Roadmap covers CCV-001 through CCV-009 with dependencies, readiness gates,
  manual-gap tracking, and measurable acceptance criteria.
- Tracker distinguishes implementation, verification, approval, and future work.
- Only authorized documents change; no scripts, APIs, Git operations, or external
  configuration changes are executed.
- Owner reviews architecture, scope, and open decisions. Approval is recorded
  explicitly before closing the milestone or starting CCV-002.

Risks: source intent mistaken for support; unresolved scope; premature approval
claims. Mitigation: label evidence and proposals; retain owner review gate.

## CCV-002 - Application skeleton, profiles, and offline contracts

Proposed deliverables: minimal separate application/package entry point, source
and destination profile schema, typed/versioned artifact, mapping, plan, and result
contracts, and offline test harness. No production migration implementation.

Acceptance:
- Approved Python baseline, dependency/tooling choices, and project layout recorded.
- CLI can select a domain and offline validation action without network access.
- Offline candidate planning is distinct from online destination preflight;
  destination snapshots are local inputs and do not prove current state.
- Invalid/missing product, version, profile, artifact, and mapping input produces
  explicit errors and a failing exit status.
- Synthetic valid/invalid artifacts and schema-version mismatch have focused tests.
- Offline validation and planning tests must instrument the shared transport and
  guard lower-level network entry points, fail on attempted access, and assert
  **zero network calls/attempts**, not merely zero successful connections or zero
  writes. Cover valid, invalid, missing-input, and error paths; include a local
  destination-snapshot planning case. No authentication, DNS lookup, or preflight
  may be triggered implicitly.
- Use synthetic fixtures only; no secrets are committed.

Risks: overengineering and incompatible contracts. Keep a small explicit module
registry; review contracts against legacy shapes before broad implementation.

## CCV-003 - Transport, clients, and authentication

**Status: implemented mock-only scope accepted by the project owner on
2026-11-17.** Acceptance covers A/B/C as implemented, not the original broader
apply/verification/journaling proposal.

Accepted deliverables:
- **CCV-003-A:** injected HTTP transport foundation, secure configuration/TLS
  defaults, mandatory connection/read timeouts, safe URLs/header/error handling,
  bounded explicit GET retries, and no automatic write replay.
- **CCV-003-B:** distinct source-observed product authentication strategies,
  injected secret resolution, independent source/destination sessions,
  expiration/local cleanup, sanitized failures, and the reviewed initialization
  cleanup correction. No automatic authentication renewal or invented logout.
- **CCV-003-C:** separate Cyber Controller Physical/Organization and Vision LDAP
  read interfaces, strict product/version/backend gates, and a synthetic
  declaration/session/read/artifact/validation/mapping/offline-plan/summary
  workflow using existing application contracts.
- Synthetic `0.0-test` declarations remain separate from the empty production
  capability catalogue and usable only through explicitly declared mock
  backends. Default production lookup rejects synthetic and unapproved real
  versions; a future ordinary HTTP adapter gains no synthetic permissions.

Accepted evidence:
- Final technical review: **no blocking defects identified**.
- `python -B -m unittest discover -s tests -v`: **130 tests passed** in
  **37.927 seconds**, with the source directory on `PYTHONPATH`.
- **Zero guarded network attempts** across 15 socket/DNS/HTTP/URL guards,
  including invalid/error paths. This proves guarded Python-level offline
  behavior, not OS-level isolation or real product compatibility.
- Owner explicitly accepted the passing tests, zero guarded attempts,
  nonblocking technical review, and synthetic/production isolation.
- See [E-012](PROGRESS.md#e-012---ccv-003-owner-acceptance-2026-11-17) and the
  [decision register](DECISIONS.md#owner-implementation-acceptance---ccv-003-2026-11-17).
  These are existing review results; tests were not rerun for this
  documentation-only acceptance recording.

Remaining limits and gates:
- Live Vision/Cyber Controller compatibility and qualification remain
  **pending**; no real product/version is enabled or certified.
- The nominal mock-backend declaration is a trusted developer assertion, not a
  sandbox. No concrete HTTP backend or production secret provider exists.
- Response shapes, destination identity/comparison, and semantic declarations
  remain synthetic/unverified. Cyber Controller authentication retains its
  source-observed HTTP-200-only limitation.
- No destination inventory/preflight, product transformation, real migration
  execution, approval/apply implementation, post-import verification, durable
  journal, or partial-import recovery is implemented by this accepted slice.
  Original broader mocked-stage proposals remain deferred.
- Acceptance authorizes no live API requests, production connectivity, real
  migration execution, external configuration changes, or claims of verified
  Vision/CC compatibility. CCV-004 and further work require separate approval.

Risks: product/version differences, expired sessions, and unknown logout/async
semantics. No generic compatibility fallback or invented endpoint.

## CCV-004 - Controller objects and credentials

Implemented/accepted slices: A object/mapping contracts; B comparison, safe
CREATE planning and order-preserving artifacts; C1 legacy representation
adapters; C2 explicit detail/access reconciliation and universal bound
acknowledgement. Their acceptance does not authorize credential transformation,
production writes, or broader CCV-004 execution.

### CCV-004-C3 - Master offline controller migration orchestration

**Authorization:** explicit owner approval on 2026-11-18 for this bounded
offline-only slice. **Status:** implemented/offline-verified; technical review
and owner acceptance pending. Dependencies: accepted A/B/C1/C2 and existing
CLI/profile/artifact/plan contracts.

Deliverables:

- Reusable local-manifest orchestration over existing normalization, adapters,
  reconciliation, validation, acknowledgement, comparison and controller planning.
- Minimal `plan --request` CLI, optional protected `--record`, and retained-input
  `--verify`, with redacted JSON reports and meaningful exit codes.
- Explicit versioned manifests and integrity-bound local input declarations.
- A complete synthetic demonstration with all four classifications and nested
  CREATE dependencies, plus guarded end-to-end failure/regression cases.

Verification: all 291 prior cases retained plus 21 new tests, 312 passing;
zero guarded network attempts. Demonstration: 8 objects, CREATE=3, SKIP=3,
CONFLICT=1, BLOCKED=1; its exit 1 is intentional. See E-027 in
[PROGRESS.md](PROGRESS.md) for actual commands/results, and
[ARCHITECTURE.md](ARCHITECTURE.md#master-offline-controller-workflow---ccv-004-c3)
for CLI/manifest usage.

Scope boundaries:

- Controller planning only; no generic controller bypass, root CREATE, implicit
  identity matching, acknowledgement generation, or unsafe comparison exclusion.
- No live API/export/import, real backend, configuration write, apply command,
  credential transformation, new dependency, legacy change, or Git operation.
- Local evidence/declarations remain offline assertions, not live completeness,
  compatibility, credential portability, or execution approval.
- This is not authorization for cross-domain CCV-007, other migration domains,
  qualification, or the next milestone.

Next action: review C3 and seek owner acceptance; stop before further development
without separate authorization.

### Broader CCV-004 proposal - not authorized by C3

Proposed deliverables: Physical/Organization export and adapters; hierarchy and
destination identity mapping; device-access validation; offline credential
transformation; explicit create/update planning and guarded apply.

Acceptance:
- Synthetic nested sites and devices preserve intended hierarchy in both trees.
- Duplicate names, missing parents, cyclic hierarchy, and uncertain device matches
  block affected writes; no silent root fallback.
- Update plans use resolved destination IDs, never source IDs as substitutes.
- Credential transformations do not log secrets or mutate unrelated input data;
  incomplete mappings produce explicit failures.
- Tests distinguish accepted, completed, and verified outcomes; no invented
  async-status endpoint is used.

Risks: encrypted/masked secrets, duplicate devices across trees, partial writes,
and response-shape differences. Resolve field fidelity and secret policy first.

## CCV-005 - LDAP permissions

Proposed deliverables: export/compare/plan/import with destination role/group/policy
mapping and explicit device-lock intent.

Acceptance:
- Offline tests cover create, identical existing entry, conflicting existing
  entry, missing references, rejected scope, and partial failure.
- No rejected scope becomes an all-scope permission automatically.
- Device-lock settings are not silently forced.
- Duplicate detection distinguishes semantic equivalence from matching group
  attribute alone; unresolved references block import.

Risks: privilege expansion and unintended authorization changes. Require an
approved mapping/validation policy before enabling writes.

## CCV-006 - Scheduled tasks

Proposed deliverables: evidenced paths, task-type adapters, validation,
comparison, export/import, and explicit duplicate policy.

Acceptance:
- Sanitized path references are resolved and documented per product/version.
- Supported task types, server-managed fields, timezone, activation, and required
  object references have approved contracts.
- Tests cover malformed task lists, conflicting names, missing dependencies,
  approved field stripping, and per-task failures.
- No unknown payload shape is treated as an empty successful listing.

Risks: unavailable configuration, task-specific payloads, unintended schedule
activation, and nonportable references. Unknown task types remain blocked.

## CCV-007 - Integrated orchestration and reporting

Proposed deliverables: extend the CCV-003 mocked workflow to the readiness-verified
modules approved for integration, with dependency plans, comparison, approval
binding, recovery journals, and redacted reports.

Acceptance:
- Synthetic integration tests exercise export, offline validation, dry-run,
  explicit approval, apply, and post-import comparison.
- Offline validation/planning makes zero network calls; separately selected
  online preflight/dry-run makes zero configuration-changing requests.
- Changed plans/inputs invalidate approval; failed prerequisites block dependents.
- Partial/indeterminate outcomes appear in both machine and human reports and
  cannot produce an overall verified-success result.
- Logs/reports contain no fixture secrets, cookies, or raw sensitive payloads.

Risks: unsafe continuation, stale plans, and misleading success summaries.
Recheck assumptions at apply time; maintain per-object outcomes.

## CCV-008 - Qualification and release readiness

Proposed deliverables: approved product/version compatibility matrix, operator
instructions, recovery limitations, and a release-readiness report.

Acceptance:
- Offline regressions pass for all approved modules and supported artifact versions.
- Each claimed live-supported operation has separately authorized lab evidence
  for its product/version and meaningful post-write verification.
- Untested combinations remain explicitly unsupported/unverified.
- Operators review secrets/retention policy, partial-failure recovery, and known
  exclusions; production readiness requires owner acceptance.

Risks: unavailable lab access, vendor differences, and unsupported recovery.
Never equate a mocked pass with live compatibility or promise automatic rollback.

## CCV-009 - API discovery and automation expansion

Status: **Proposed — pending owner approval**; not started.

Proposed deliverables: a continuously maintained manual-configuration gap and
automation-opportunity register in this roadmap, linked to operation evidence in
[API_MATRIX.md](API_MATRIX.md) and task status in [PROGRESS.md](PROGRESS.md).
Discovery does not authorize implementation, scope expansion, or live requests.

Each gap record must include an ID, manual activity, proposed automation benefit,
product/version, API/schema evidence, dependencies, risk, priority, approval,
implementation/verification status, blocker, and next action. Use "unknown" for
missing information rather than inventing endpoints or claiming no API exists.

Initial candidates are hypotheses, not confirmed operator procedures or supported
automation:

| Gap ID | Manual gap / opportunity to investigate | Evidence and readiness gap | Priority / risk | Next action |
| --- | --- | --- | --- | --- |
| GAP-001 | Resolve site hierarchy and destination device identity mappings | Legacy name lookups and source-ID reuse observed; safe matching contract unknown | P0 / wrong target or hierarchy | Confirm operator workflow and destination identity/schema evidence |
| GAP-002 | Map LDAP roles, groups, policies, and device-lock intent | Permission import observed; reference-discovery capabilities unestablished | P0 / privilege expansion | Obtain approved reference schemas; preserve scope |
| GAP-003 | Map scheduler references, task activation, and timezone | Configuration-supplied paths and task schemas unavailable | P1 / unintended task execution | Obtain sanitized path configuration and representative schemas |
| GAP-004 | Verify asynchronous completion and reduce manual post-import checking | HTTP acceptance observed; completion/read-back coverage incomplete | P0 / false success or duplicate retry | Identify evidenced status/read-back mechanisms per operation |
| GAP-005 | Safely transform or re-enter device-access credentials | Offline transformation observed; secret portability unknown | P1 / secret exposure or unusable access | Confirm supported credential handling without collecting secrets |
| GAP-006 | Identify remaining manual product configuration and supported APIs | Operator inventory and vendor coverage incomplete; no additional endpoints asserted | P1 / unbounded scope | Collect approved operator gap list and prioritize evidence review |

For all initial candidates: product/version is unknown; approval is
**Proposed — pending owner approval**; implementation and verification are
**not started**. Dependencies are CCV-001 approval, scoped discovery authorization,
and approved operator/vendor evidence. Those missing inputs are current blockers.
No candidate authorizes document restoration or deployment-helper integration.

Acceptance:
- Validate the manual activity with the owner before calling it a confirmed gap.
- Record each opportunity and distinguish source-observed, officially documented,
  mock-tested, and live-tested evidence by product/version.
- For a proposed automation slice, record schema/identity/dependency readiness,
  safety constraints, acceptance criteria, and a separate approval decision.
- Explicitly record unknown, unsupported, or still-manual areas with reasons and
  next actions. Do not equate missing evidence with vendor non-support.
- Update readiness-based sequencing only through approved scope changes.
- Keep discovery offline/static unless separate authorization permits live
  investigation; never invent endpoints or expose operational data.

Risks: undocumented/version-specific behavior, scope creep, sensitive operator
data, and unsafe attempts to automate authorization or recovery. Mitigate through
evidence-qualified records, sanitized inputs, and explicit approval gates.

## Immediate next action

Preserve the owner-accepted CCV-003-A/B/C mock-only checkpoint and its 130-test,
zero-guarded-attempt evidence. Await separate authorization before CCV-004 or
any further implementation. Supported real versions, approved API/schema
evidence, live compatibility, and qualification remain open gates; no live
requests, production connectivity, real migration execution, or external
configuration changes are authorized by this acceptance.

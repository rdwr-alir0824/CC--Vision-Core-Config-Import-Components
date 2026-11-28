# Development Roadmap

## Active roadmap - approved legacy-first redesign, 2026-11-27

The simple legacy-first application is independent of the experimental
milestones below. Those records and implementations remain preserved.

| Task | Scope | Dependencies | Approval / current status |
| --- | --- | --- | --- |
| CCV-LF-1A | New client/config/files, compatible shared reuse, focused offline tests, documentation | Approved legacy-first design; original scripts and reusable HTTP/TLS/JSON code | Owner-approved; checkpoint c0d6b98854cc9ede3a398a476005ce2a494c6e3a. Offline/mocked only. |
| CCV-LF-1B | Generic Physical/Organization Site/Device export only | Approved 1A foundation; original downloader | Closure passed offline; checkpoint 0ee1b142fbcf07fc593f249b02f8713c50f5db2c. No live verification. |
| CCV-LF-1C | Independent Site/Device import only | Passing/committed 1B closure; original uploader | Closure passed; checkpoint b7ba305279c39d030cd2f3f77a137dd0795e9942. Offline only. |
| CCV-LF-1D | Thin master CLI over approved export/import | Passing/committed 1C closure; existing foundation | Closure passed; local checkpoint/tag authorized. 134 focused; 925 full tests, 923 passed/two accepted environment skips. |
| CCV-LF-1E preparation | Linux deployment and fresh lab qualification instructions only | Offline-qualified 1D checkpoint; separate execution approval | Preparation authorized. No deployment, live qualification or new domains authorized. |
| Future optional credentials | CLI/HTTP/HTTPS/SNMPv3 JSON edits and separately approved Device updates | Portable exports; approved destination lookup/update behavior | Deferred. |
| Future LDAP | Independent export/import functions, preserving authorization semantics | Original LDAP behavior; explicit scope approval | Deferred; no implementation. |
| Future Scheduler | Independent export/import functions | Concrete configured endpoints and task behavior; explicit approval | Deferred; no implementation. |

Phase 1B acceptance: generic recursive Physical/Organization exports, one
authenticated source session, original fields plus source_root metadata,
containment-derived parents with source Site-by-ID name fallback, complete
copied deviceAccess with its own ormID removed, separate runtime filenames,
credential warning, explicit independent tree errors and session cleanup.
No retries or historical qualification artifacts. Synthetic fixtures vary
IDs, hierarchy names, model types and management addresses.

Implemented Phase 1C: independently load these portable files, explicitly map the
source root to the selected destination root, resolve destination parents and
identities, create Sites before Devices using minimal legacy POST payloads,
and return SUCCESS/SKIPPED/FAILED without source-ID reuse or root fallback.
Structural validation precedes login. Creation requires bounded hierarchy
readback, not HTTP acceptance; uncertain writes are not automatically repeated.
Import approval is separate from any future master menu or live-call permission.

Each phase has its own owner review gate. No journals, recovery/resume engines,
capability registries, databases, deployment changes or unrelated features.
Offline test success does not authorize live calls or certify product versions.
See [current progress](PROGRESS.md#ccv-lf-1d---thin-master-cli).

## Proposed Phase 1E - bounded live qualification

Proposal only; obtain explicit owner approval before any live request.

1. Approve exact source/destination products, versions, lab addresses/accounts,
   permitted source reads and destination creates, selected trees/roots, TLS
   policy and protected output paths. Prefer verified TLS/trusted certificates.
   Do not put operational credentials or exports in Git.
2. Prepare small, generic isolated lab hierarchies with nested Sites, direct-root
   and nested Devices. Review destination inventory/IP conflicts and establish
   an operator-controlled backup/manual cleanup plan; no automatic rollback.
3. Launch the documented CLI with --allow-live only after authorization. Export
   selected trees into protected files; inspect completeness/parent relationships
   without printing credentials. Confirm any replacement explicitly.
4. Import one approved file/tree at a time. Review source root/counts and actual
   discovered destination root; explicitly confirm both stages. Verify created
   names/types/IPs/placement and independent destination IDs using GUI or approved
   existing GET endpoints. Check supported credential usability separately using
   approved methods; do not assume masked/encrypted secrets are portable.
5. On an approved repeat, correctly existing objects should skip. Review conflicts
   and failed branches without automatic updates/moves/deletes. Stop on uncertain
   creation, timeout or delayed completion; inspect destination manually before
   considering any separately approved repeat. Do not expand readback speculatively.
6. Record product/version-specific live evidence in API_MATRIX and PROGRESS,
   distinguishing source-observed, documented, mocked and live-tested behavior.
   Keep secrets and sensitive operational outputs outside repository reports.

No utility-server deployment, customer-specific behavior, credential
transformation, Device update, LDAP/Scheduler or experimental-engine changes.

Date: 2026-11-19
Status: **CCV-001 architectural baseline approved; CCV-002 completion confirmed
by the owner; CCV-003-A/B/C implemented mock-only scope owner-accepted on
2026-11-17. CCV-004-A/B/C1/C2 completed offline scopes are owner-accepted.
CCV-004-C3's completed offline-only scope is owner-accepted on 2026-11-18
(E-030/E-031: 321 tests passed, zero guarded attempts).
CCV-009-A static product compatibility/API discovery is owner-accepted
(E-033). CCV-009-B offline documentation/schema qualification is separately
authorized; E-035's technical review supported bounded offline tests.
E-036 implements those subsets: 350 tests pass (321 existing + 29 new).
E-037 records B owner acceptance with non-blocking observations, offline only.
CCV-010-A's concrete, explicitly injected standard-library HTTPS backend is
owner-accepted for offline scope (E-040, 2026-11-19), following E-039's four
corrections: 394 passing tests remain historical evidence, not rerun here.
Actual network dispatch remains untested. CCV-010-B now has authorization for
planning/documentation only: the [laboratory plan](LAB_QUALIFICATION_PLAN.md)
defines pending gates and candidate operations, not execution permission.
No gate has passed; laboratory activation and execution remain unauthorized.
Complete schema/runtime qualification remains blocked by provenance conflicts
and incomplete contracts; production remains default-deny.**
Broader/future implementation remains proposed/not authorized. Live product
compatibility and qualification are explicitly pending.

**2026-11-19 C overlay:** separately authorized CCV-010-C implements bounded
response bodies, explicit destination/operation authorization and shared
monotonic deadline accounting. Following source-based review and owner-selected
"Fix all issues", E-044 corrects chunk-delimiter validation and initial expiry
classification: **425 offline tests pass** (394 baseline + 29 C regressions +
two correction regressions). **Hard DNS cancellation is blocked; hard whole-operation interruption
remains unqualified.** Built-in HTTPS dispatch now fails closed before DNS.
The injected factory is an offline-double seam only. Full C technical acceptance
is withheld pending a separately reviewed runtime design; no owner acceptance
is recorded. See [E-043](PROGRESS.md#e-043---ccv-010-c-offline-http-safety-hardening-2026-11-19)
and [E-044 corrections](PROGRESS.md#e-044---ccv-010-c-review-and-authorized-corrections-2026-11-19),
plus the [architecture overlay](ARCHITECTURE.md#ccv-010-c-safety-overlay---2026-11-19).
B's planning acceptance and all NOT PASSED Gates A-D are unchanged.

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
| CCV-004 | Controller objects, device access, credential transformation | P1 | CCV-002, CCV-003; identity and secret-policy decisions | A/B/C1/C2/C3 completed offline scopes owner-accepted; C3 latest correction E-030: 321 tests, zero guarded attempts; E-031 acceptance. Broader credential/apply work remains unauthorized. |
| CCV-005 | LDAP permission migration | P1 | CCV-002, CCV-003; approved destination reference mappings | Not started; not authorized. |
| CCV-006 | Scheduled-task migration | P1 | CCV-002, CCV-003; resolved paths and task-type contracts | Not started; not authorized. |
| CCV-007 | Integrated orchestration, comparison, and reporting | P0 | CCV-003 mocked slice; readiness-verified subset of CCV-004/005/006 approved for integration | Not started; not authorized. |
| CCV-008 | Compatibility qualification and release readiness | P2 | CCV-007; separately authorized lab access and acceptance scope | Not started; not authorized. |
| CCV-009 | API discovery and automation expansion workstream | P1 | CCV-001 approval; explicit discovery scope and evidence-access authorization | A and B accepted for completed static/offline scopes (E-033/E-037). Broader implementation, lab work and activation unauthorized. |
| CCV-009-A | Product compatibility and API discovery | P1 | Accepted offline C3; owner target/direction declaration; existing sources/contracts | Owner-accepted static scope, E-032/E-033. Vision 5.4.x and CC 10.10.x remain unqualified targets, not supported releases. |
| CCV-009-B | Version-pinned API evidence and offline schema qualification | P1 | Accepted A; E-035/E-036 and independent review | Owner-accepted with non-blocking observations on 2026-11-18 (E-037), bounded offline scope only; 350 tests plus review probes accepted; CC provenance/schema gaps unresolved; no production/runtime qualification. |
| CCV-010-A | Concrete HTTP backend and offline compliance | P0 | Accepted CCV-009-B; E-038/E-039; independent follow-up and explicit owner decision | OWNER ACCEPTED - offline scope, 2026-11-19 (E-040); 394 historical passing tests; no actual dispatch or production activation. |
| CCV-010-B | Read-only laboratory qualification planning | P1 | Accepted CCV-010-A; exact evidence/builds; backend safety; separate lab and execution approvals | Planning/documentation only; plan prepared (E-041). Gates A-D not passed; lab activation/execution unauthorized; no application implementation. |
| CCV-010-C | HTTP backend safety hardening | P0 | Accepted A offline scope; B safety prerequisites; separate C offline-development authorization | Implemented/offline-tested body limits and exact operation scope; shared deadline accounting verified; DNS cancellation blocked and hard runtime interruption unqualified. E-043 review followed by authorized E-044 corrections: 425 passes, zero guarded attempts. Built-in dispatch denied; full C technical acceptance withheld; no owner acceptance or lab permission. |

Milestone numbers identify workstreams, not a rigid execution order. CCV-009 is
able to run alongside approved development after the CCV-001 gate, not wait
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
All backend responses and credentials in that slice are synthetic; no real backend
or write path was part of C. CCV-010-A subsequently adds the explicit adapter,
not an online CLI or migration write path. Synthetic contracts are not evidence
of vendor compatibility.

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
  acceptance baseline. Subsequently reconfirmed in CCV-009-A/E-032: 22 files,
  13 byte-distinct implementations and nine duplicate copies; this does not
  retroactively change the historical acceptance evidence.
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
  sandbox. At C's checkpoint no concrete HTTP backend or production secret
  provider existed. CCV-010-A adds an ordinary adapter, not mock permissions
  or a production secret provider.
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
offline-only slice. **Status:** completed scope owner-accepted on 2026-11-18;
E-030 is the latest correction evidence and E-031 records acceptance.
Dependencies: accepted A/B/C1/C2 and existing
CLI/profile/artifact/plan contracts.

Deliverables:

- Reusable local-manifest orchestration over existing normalization, adapters,
  reconciliation, validation, acknowledgement, comparison and controller planning.
- Minimal `plan --request` CLI, optional protected `--record`, and retained-input
  `--verify`, with redacted JSON reports and meaningful exit codes.
- Explicit versioned manifests and integrity-bound local input declarations.
- A complete synthetic demonstration with all four classifications and nested
  CREATE dependencies, plus guarded end-to-end failure/regression cases.

Initial verification: 312 passing tests. Accepted correction checkpoint:
**321 tests passed, zero guarded network attempts**, no remaining confirmed
acceptance blockers. These are historical C3 results, not tests rerun for
CCV-009-A and not product compatibility evidence.
Demonstration: 8 objects, CREATE=3, SKIP=3,
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
- Retained records remain plaintext; permissions/protected storage are operator
  responsibilities. Cleanup cannot guarantee deletion when permissions prevent
  it; explicit cleanup-failure reporting and operator inspection remain required.
- This is not authorization for cross-domain CCV-007, other migration domains,
  qualification, or the next milestone.

Next action: preserve accepted C3 and all limitations during the separately
authorized CCV-009-A documentation-only discovery. No application extension is
authorized.

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

Status: **CCV-009-A's static discovery scope is owner-accepted; CCV-009-B is
authorized on 2026-11-18 for offline documentation/schema qualification only**.
B's partial report is delivered for technical review; broader CCV-009
implementation, live discovery and capability activation remain unauthorized.

Deliverables: product/version/role/direction API evidence in
[API_MATRIX.md](API_MATRIX.md), compatibility limitations, the manual-automation
gap register and prioritized discovery backlog below, and E-032/status in
[PROGRESS.md](PROGRESS.md). A's inventory found no approved vendor documentation;
the owner subsequently supplied the two local PDFs reviewed in B/E-035.
Documented operations do not enable production capabilities.

### CCV-009-A targets, scope and readiness

- **A:** APSolute Vision 5.4.x source to Cyber Controller 10.10.x destination.
- **B:** Cyber Controller 10.10.x source to Cyber Controller 10.10.x destination.
- Families are based on owner-reported testing, not application compatibility
  certification. Exact source/destination patches/builds and operation-level
  evidence have not been supplied.
- Legacy versions remain unknown. Object API intent is Cyber Controller;
  LDAP/scheduler intent is Vision. Shared paths do not establish shared behavior.
- The production capability catalogue remains empty. Only existing synthetic
  `0.0-test` declarations exist; C3 is not a real-version Vision migration client.
- Completed static scope: 22 files / 13 distinct implementations / nine duplicate
  copies, 16 logical operation records, 12 concrete method/path pairs across ten
  path templates, plus four unresolved scheduler references within those 16
  records. Login has two product-specific evidence rows, not a thirteenth pair.
- Documentation discovery does not establish access completeness, full backup
  coverage, safe credential portability, real API behavior or import authority.

Each gap record must include an ID, manual activity, proposed automation benefit,
product/version, API/schema evidence, dependencies, risk, priority, approval,
implementation/verification status, blocker, and next action. Use "unknown" for
missing information rather than inventing endpoints or claiming no API exists.

### Manual migration automation gap analysis

These are **discovery candidates, not owner-confirmed manual procedures**. For
every row: A permits this static analysis only; proposed automation is **not
approved, not implemented and not product-verified**. The existing offline
contracts supply reusable safety primitives, not newly supported product APIs.
V54 = Vision 5.4.x target; C1010 = Cyber Controller 10.10.x target. Exact builds
remain unknown in every row. DISC references below are prerequisites/next actions,
not authorizations.

| Gap ID | Manual activity candidate and automation benefit | Product/version, role and direction | API/schema evidence and implementation boundary | Dependencies / blocker | Priority / safety risk | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| GAP-001 | Rebuild sites/organizations and place devices; reduce repetitive hierarchy entry | V54 source A; C1010 source B and destination A/B | CC API-02 through API-09 intent; C3 offline mapping/nested CREATE already exists; Vision tree API/schema missing | DISC-01/03/04/06; qualified roots, parent mappings, destination completeness | P0 / wrong hierarchy, root fallback, source-ID reuse | Obtain per-build hierarchy/identity contracts; validate operator workflow; never use name/IP guessing |
| GAP-002 | Recreate LDAP permissions and map roles/groups/policies; reduce manual permission entry | V54 source A; C1010 source B and destination A/B | Vision API-10/11 only; Vision-destination write is outside A/B; no CC LDAP contract | DISC-01/02/07; CC paths and reference/lock semantics missing | P0 / privilege expansion or forced device locking | Establish CC reference APIs and exact scope-preserving mapping; no all-scope fallback |
| GAP-003 | Recreate scheduled operations and dependencies; avoid repeated task entry | V54 source A; C1010 source B and destination A/B | CFG-01 through CFG-04; literal paths/task-type schemas missing; no CC evidence | DISC-01/02/08; task references, timezone and activation policy | P1 / unintended scheduled execution | Obtain sanitized API section and vendor task schemas; require explicit activation intent |
| GAP-004 | Manually verify operation completion; automate supported status/read-back checks later | C1010 destination A/B; source declarations independent | API-07/08/09 accept HTTP 200; async header not completion evidence; no polling path observed | DISC-04/06/09; completion/error/idempotency/recovery contracts | P0 / false success, uncertain writes, duplicate replay | Identify documented completion mechanism without inventing a polling endpoint |
| GAP-005 | Re-enter or safely remap access credentials; reduce manual secret handling without retaining values | V54 source A; C1010 source B and destination A/B | Local credential-transform helper and CC API-06/08/09; C3 rejects raw credentials and gates acknowledged access | DISC-03/04/05; provider/portability/masking policy unresolved | P0 / secret exposure, invalid device access, bypassed acknowledgement | Classify supported credential representations without collecting credentials; retain fail-closed behavior |
| GAP-006 | Inventory other manual product management activities; prioritize bounded automation | V54 source A; C1010 both roles B and destination A | No additional official capabilities available; owner procedure inventory missing | DISC-01/10; approved vendor references and owner workflow validation | P2 / invented API coverage and unbounded scope | Ask owner to validate a sanitized activity list in a separately authorized evidence slice |
| GAP-007 | Join device details/access to tree exports; reduce manual reconciliation | V54 source A; C1010 source B and destination A/B | CC API-06 first-IP-match legacy merge is unsafe; C2 explicit qualified association already exists offline | DISC-03/04/05; native detail identity, full access schema, completeness evidence | P0 / wrong-device merge, dropped fields, stale acknowledgement | Qualify native IDs/tree/controller provenance and ambiguity/error behavior |
| GAP-008 | Capture configuration exports/backups and pre-change recovery evidence; reduce manual backup steps | V54 source A; C1010 source B and destination A/B | Partial legacy JSON exports only; no full product backup/restore API established; API-12 excluded | DISC-01/09; documented coverage, protected storage, restore/recovery procedure | P1; recovery is a gate before future writes / incomplete backup, false rollback assurance | Distinguish partial object exports from full backup; verify recovery prerequisites separately |
| GAP-009 | Compare source/destination configuration and prepare dependency plans; reduce manual diff/checklists | V54 source A; C1010 source B and destination A/B | C3 loss-preserving ordered offline comparison/planning exists for synthetic CC only; real schemas unknown | DISC-03/04/05/07/08 by selected domain; no inferred transforms | P0 / false SKIP, silent field loss, unsafe exclusions | Map version-pinned schemas into existing contracts; unknown semantics remain BLOCKED |
| GAP-010 | Repeat authentication/version/inventory preparation; make declarations and capture evidence consistent | V54 source A; C1010 source B and destination A/B | API-01 variants and unresolved CFG login/logout; no version-discovery endpoint observed | DISC-01/02/04; exact builds, RBAC, TLS, pagination/error semantics | P0 / cross-product assumptions, unsafe sessions, incomplete inventory | Qualify declarations/authentication independently; do not activate or connect clients |

### Prioritized API discovery backlog

All items are **planned evidence/lab questions**, not execution authorization.
CCV-009-A authorizes recording/prioritizing them only. Official references,
sanitized schema fixtures and any laboratory results must retain separate
evidence classifications. Later lab work requires explicit lab access,
per-operation permission and additional write authorization where applicable;
no production changes are proposed as discovery tests.

| ID / priority | Capability and relevant evidence | Product/role/direction | Prerequisites | Additional evidence / later laboratory question | Readiness / next action |
| --- | --- | --- | --- | --- | --- |
| DISC-01 / P0 | Version and documentation provenance for every operation | V54 source A; C1010 source B/destination A/B | Owner-provided approved references and sanitized testing inventory | Exact independent builds/patches; vendor title/revision/sections; which operations were owner-tested, when and how? | Missing DOC-V54, DOC-CC1010, TEST-OWNER; acquire/review only after separate authorization |
| DISC-02 / P0 | Auth/session/TLS/RBAC; API-01-C/V, CFG-01/02 | V54 source A; C1010 both roles | DISC-01; sanitized CFG-SCHED paths for Vision scheduler auth | Basic plus JSON or JSON/cookie/CSRF requirements? Expiry/logout/error semantics, least privileges, trusted CA and bounded timeouts? | Source intent only; qualify distinct per-product strategies without requesting credentials |
| DISC-03 / P0 | Vision source export/tree/site/device/access contracts, paths unknown | V54 source A only | DISC-01 | Which documented operations preserve roots, both trees, native identity, unknown configuration and access provenance? What is full inventory/completeness evidence? | Critical A blocker; never substitute CC API-02 through API-06 |
| DISC-04 / P0 | CC inventory/detail schema and identity; API-02 through API-06 | C1010 source B/destination A/B | DISC-01; DISC-02 before any future lab reads | Full schema, root classes/IDs, tree scoping, detail association, duplicate names/IPs, pagination/filtering, errors and full-inventory proof? | Source-observed plus three synthetic reads across products; obtain CC schemas and distinct role/build cases |
| DISC-05 / P0 | Device access/secret representation and acknowledgement compatibility; API-06/08/09 | V54 source A; C1010 source B/destination A/B | DISC-03 for Vision; DISC-04 for CC; owner secret policy | Which fields are portable, masked, encrypted or server-owned? What supported reference/re-entry approach avoids raw-secret artifacts? | No credential collection; preserve existing credential rejection, provenance and bound acknowledgement |
| DISC-06 / P0 | Site/device create/update, completion/read-back, idempotency; API-07/08/09 | C1010 destination A/B | DISC-02/04/05; qualified source schema for selected direction; recovery evidence DISC-09 before future writes | Required fields/types, destination ID binding, PUT replace/merge, async result/error model and uncertain-write reconciliation? | No executor exists; docs/specification first; lab mutations require separate explicit authorization |
| DISC-07 / P1 | LDAP listing, permission/reference operations; API-10/11 are Vision-only | V54 source A; C1010 source B/destination A/B | DISC-01/02; owner scope/device-lock policy | Exact CC endpoints and both products' role/group/policy schemas, scope equivalence, duplicate identity and read-back? | CC equivalents absent; Vision destination POST does not qualify CC; retain GAP-002 P0 safety gate |
| DISC-08 / P1 | Scheduler paths/task types; CFG-01 through CFG-04 | V54 source A; C1010 source B/destination A/B | DISC-01/02; sanitized path evidence; owner task inventory | Literal per-product paths, task schemas, reference IDs, server-owned fields, timezone, activation, task completion? | Unresolved; do not assume conventional endpoints, strip unknown fields or activate schedules |
| DISC-09 / P1 | Partial export coverage, full backup/recovery and post-change comparison | V54 source A; C1010 source B/destination A/B | DISC-01; owner recovery requirements | Is there a documented backup/export API, what does it omit, and what supported restore/read-back procedure exists? | No full backup endpoint established; recovery evidence becomes P0 gate before later writes; no API-12 integration |
| DISC-10 / P2 | Other management/manual activities, scope validation | V54/C1010 roles as owner subsequently confirms | DISC-01; sanitized owner-validated manual procedure list | Which additional documented operations reduce approved manual work? Dependencies, risk, supported versions and evidence per candidate? | No new endpoints asserted; Docker/cron and document-store restoration remain excluded pending separate scope decisions |

### CCV-009-B - Version-pinned API evidence and offline schema qualification

**Authorized offline-only on 2026-11-18. E-035 technical review supported bounded
offline tests; E-036 implementation delivered. Complete schema/runtime
qualification remains blocked. No owner
acceptance recorded.** Authorization supersedes A's historical B-not-authorized
checkpoint only for the supplied bounded scope.

Results: the owner-provided Vision 5.4.9 (April 2025) and CC 10.10.7-labelled
(September 2026) PDFs each document **five of 12 legacy pairs**; seven are in
neither reference. CC's active metadata title says **10.10.6**, contradicting
its cover/overview; no version applicability is silently inferred.
The [B vendor analysis](API_MATRIX.md#ccv-009-b---approved-vendor-reference-analysis)
records exact provenance/pages, all existing operation records, all four still
unresolved scheduler INI bindings, partial lookup/access schemas, unresolved
DevicePojo/UserPojo and example/model contradictions, documented async lifecycle,
independent direction blockers and the historical proposed tests.
The [E-036 overlay](API_MATRIX.md#ccv-009-b---implemented-offline-subsets---e-036)
now records isolated exact-evidence bindings, login examples, SitePojo/selected
Device/DeviceSetup/40-field DeviceAccess subsets and in-memory async traces.
It reuses artifact/credential validation, preserving unknown JSON/order/native
identity and explicit null/enum/credential uncertainty. Only the new
api-schema-evidence artifact domain joins order-preserving serialization.
Plan construction/parsing explicitly rejects that evidence-only domain.
No capability, client, authentication strategy, transport or dependency changed.

Acceptance disposition: approved-document inventory and evidence analysis are
delivered; the separately authorized bounded implementation passes **350 tests
in 48.098s (321 existing freshly rerun + 29 new)** on Python 3.13.14.
New tests measured **0 guarded attempts across 435 observations (29 x 15)**;
this is not OS isolation or a new aggregate counter for other suite cases.
Syntax/per-file diagnostics are clean. Complete schema validation still needs
authoritative clarification. See [E-036](PROGRESS.md#e-036---ccv-009-b-offline-subset-qualification-2026-11-18);
E-035/E-034 retain their original documentation-only verification boundaries.

The subsequent independent review and E-037 owner acceptance accept only B's
completed bounded offline implementation; its four permanent-regression
recommendations remain accepted non-blocking follow-ups, not A scope.
Remaining qualification gates: vendor clarification of C's metadata/version
applicability and schema contradictions, independently declared actual source/
destination builds, missing tree/site-create/PUT/LDAP/task contracts, sanitized
CFG-SCHED paths and TEST-OWNER provenance. DOC-V54/DOC-CC1010 availability is
now satisfied by the supplied PDFs, not full schema qualification. Do not retrieve
restricted material or start another milestone. Live clients/backend,
authentication, lab work, capability activation and migration execution remain
outside B authorization.

Acceptance:
- Validate the manual activity with the owner before calling it a confirmed gap.
- Record each opportunity and distinguish source-observed, officially documented,
  owner-reported, mock-tested, and separately authorized live-tested evidence by
  product/version.
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

## CCV-010-B - Read-only laboratory qualification planning

Authorization is limited to local static review and documentation. The
[laboratory qualification plan](LAB_QUALIFICATION_PLAN.md) defines independent
Vision/CC build and target checklists, the smallest candidate login/site-by-ID
read/local-close sequence, conditional explicitly approved remote logout,
authentication/session/schema qualification, evidence retention and stop rules.
No actual laboratory details or secrets are supplied, no candidate is approved,
and no laboratory execution or owner acceptance is recorded.

Gate A requires exact operation/build evidence and C provenance clarification.
Gate B requires enforced DNS/total-duration/body-size bounds, reviewed lab-only
allowlisting/authentication integration and bounded local/remote cleanup.
Gate C requires laboratory/data/security approvals; Gate D requires a separate
owner decision for the exact procedure after A/B/C. All are **NOT PASSED**.
The three unresolved backend resource controls are activation blockers; none is
waived or implemented by this documentation task.

Verification is static documentation checking only (E-041). The accepted
394-test result remains historical; application tests are not rerun.

## Immediate next action

Stop after delivering CCV-010-B's plan. Preserve E-038/E-039/E-040 and all prior
offline safety/evidence boundaries. Resolve the plan's missing build, provenance,
authentication, resource-control, remote-session and storage prerequisites only
under separately scoped authorization. Do not implement controls or execute a
test from this plan. Production remains default-deny; lab connectivity,
authentication, API requests, migration execution and configuration changes
remain unauthorized. No subsequent milestone or gate approval is inferred.

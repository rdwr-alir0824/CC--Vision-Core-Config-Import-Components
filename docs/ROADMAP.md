# Development Roadmap

Date: 2026-11-17  
Status: **Proposed — pending owner approval**; only CCV-001 documentation
amendments are authorized.

Priorities: P0 = foundation/safety gate; P1 = initial migration functionality;
P2 = release-readiness expansion. Ordering does not authorize implementation.
Each milestone requires explicit authorization and separate implementation and
verification tracking in [PROGRESS.md](PROGRESS.md).

CCV-000 static discovery is complete. It is the prerequisite to CCV-001, not a
runtime or API certification.

## Milestones

| ID | Milestone | Priority | Dependencies | Current state |
| --- | --- | --- | --- | --- |
| CCV-001 | Project Foundation | P0 | CCV-000 | In progress; review amendments documented, owner approval pending. |
| CCV-002 | Application skeleton, profiles, and offline contracts | P0 | CCV-001 approval; runtime/tooling decisions | Not started; not authorized. |
| CCV-003 | Shared transport, product clients, sessions, and mocked migration slice | P0 | CCV-002; approved evidence for selected client operations | Not started; not authorized. |
| CCV-004 | Controller objects, device access, credential transformation | P1 | CCV-002, CCV-003; identity and secret-policy decisions | Not started; not authorized. |
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

Status: **Proposed — pending owner approval**.

Keep detailed sequencing within and across CCV-004/005/006 flexible until each
selected slice has verified API/schema readiness: approved source/documentation
evidence, identified product/version limits, validated synthetic schema fixtures,
identity/dependency rules, and explicit unresolved-capability boundaries. This
readiness does not imply live compatibility. Record the evidence and obtain
approval for the selected scope before implementation.

Shared artifact/plan/result contracts begin in CCV-002. CCV-003 introduces a
minimal mocked end-to-end migration workflow for one readiness-selected domain
slice, rather than delaying all workflow feedback until CCV-007. Mocked service
responses exercise export, offline validation/planning, online-preflight logic,
approval, create/skip/conflict handling, apply, verification, and journaling.
All requests remain intercepted; "online" here describes the modeled stage,
not permission for actual network access. No real credentials or writes are used.
Synthetic contracts must not be presented as evidence of a vendor API capability.

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

Proposed deliverables: shared HTTP boundary, separate Vision/CC clients,
capability tracking, redaction, session ownership, and one minimal mocked
end-to-end migration slice selected by readiness.

Acceptance:
- Offline tests cover TLS verification default, bounded timeouts, login failure,
  session cleanup, malformed responses, and secret redaction.
- Product/version capability mismatch blocks operations explicitly.
- Mocked failures cannot trigger automatic write replay; indeterminate writes
  are represented distinctly.
- Login/logout behavior is based on approved evidence; unknown paths stay blocked.
- Mock testing is recorded separately from vendor documentation and live testing.
- The minimal workflow completes export through verification and a structured
  result journal using synthetic inputs and mocked service responses only.
- Demonstrate create-missing, skip-identical, report-differences, and
  block-ambiguous defaults; no delete/overwrite occurs without separate approval.
- Demonstrate artifact/plan integrity binding and one partial-import case:
  reconcile an uncertain mocked write before retry, avoiding duplicate creation.
- Assert no real network access during the mocked workflow. This evidence proves
  local workflow behavior only, not product/version compatibility.

Risks: product/version differences, expired sessions, and unknown logout/async
semantics. No generic compatibility fallback or invented endpoint.

## CCV-004 - Controller objects and credentials

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

Review amendments are documented, not approved for implementation. Obtain owner
approval of the amended roadmap/architecture, readiness gates, and open policies.
Then explicitly authorize a bounded CCV-002 foundation task and, if desired, a
separately scoped CCV-009 discovery task. Neither begins during this amendment.

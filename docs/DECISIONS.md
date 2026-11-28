# Architecture Decision Register

## LF-005 - thin confirmed master CLI, 2026-11-27

Status: owner-authorized Phase 1D after passing/committed 1C closure
(`b7ba305279c39d030cd2f3f77a137dd0795e9942`). Closure passed complete review;
owner authorized local checkpoint/tag. Offline only; no push or live permission.

Add only ccv.py and its tests. Reuse prompt_config and export/import functions.
Runtime inputs, hidden passwords, verified TLS, fresh session exceptions,
existing-file replacement confirmation and two-stage import consent are UI
concerns; API/traversal/JSON/business logic stays in the existing modules.

A concrete requirement needs inspect_import's validated metadata-only preview
and optional confirm_destination hook after root discovery/before writes.
Existing programmatic imports omitting the hook remain unchanged. The hook uses
the actual consumed input and destination metadata; no stale root assumptions.
Login Ctrl+C cleanup was reproduced as zero close calls before context entry;
extend the existing ClientError cleanup path to Ctrl+C/EOF only. No shared
experimental/backend/TLS change. Refuse getpass's echo fallback rather than
silently exposing a password in noninteractive environments.

Expose the foundation's live-dispatch switch as --allow-live, default disabled,
requiring separate target approval; the flag is not permission. Three readbacks,
no automatic retry/rollback, no persistent state or payload logging remain.
Options 3-7 are unimplemented and perform no operations. No new dependencies,
launchers/deployment changes or additional production modules.
Phase 1E is a separate proposed lab qualification gate, not automatic next work.

## LF-004 - simple independent import, 2026-11-27

Status: owner-authorized Phase 1C implemented after closure passed and checkpoint
`0ee1b142fbcf07fc593f249b02f8713c50f5db2c`. Offline validation only.

Extend objects.py; no extra production module. Reuse recursive hierarchy
projection without Device access reads on the destination, preserving export
defaults. Validate strict portable input before login; source root must be
present or explicitly supplied for older files. Root-relative Site paths only
disambiguate placement; they are not representation/qualification contracts.
Source/destination IDs are separate; destination native IDs come from selected
hierarchy responses, following the original uploader's preferred identity.

Existing correct objects skip without updates or access-value comparison.
Minimal legacy POSTs preserve supported opaque access fields except top-level
ormID. At most three immediate hierarchy readbacks confirm creation, with no
invented async endpoint or automatic POST replay. Failed parents block only
dependents; uncertain completion is FAILED and requires operator review.
Small result records/counts suffice. No recovery, journals, registries,
dependencies, source connection, menu or live qualification.

The only shared export-helper change preserves sanitized cleanup notes when
read failures are wrapped; no experimental/shared foundation module changes.
Phase 1C is not committed. Phase 1D menu requires separate approval.

## LF-003 - Phase 1B closure and conditional import authorization, 2026-11-27

The owner conditionally approved 1B and required atomic JSON saving, exact
portable importer contract, a complete final regression run with skipped reasons,
full diff review and a local checkpoint excluding the historical tracker edit.
Atomic same-directory temporary-file replacement replaces truncating saves;
this is not backup rotation, a journal or recovery mechanism.

Only after closure passes may Phase 1C extend objects.py with independent import
and a dedicated mocked test module. Portable JSON is the input; no source
connection or previous execution artifact. Validate before object writes,
explicitly map roots, resolve destination identities/parents dynamically,
create parent Sites before Devices with exact minimal legacy payloads, and
verify creation by bounded source-observed GET reads. No POST retries, updates,
recovery, new production modules, master menu, live calls or Phase 1C commit.

## LF-002 - accepted foundation and export-only Phase 1B, 2026-11-27

Status: **owner accepted Phase 1A and authorized export-only Phase 1B**.
Accepted foundation limitations remain unchanged; it is not being redesigned.
Phase 1A was committed locally as
`c0d6b98854cc9ede3a398a476005ce2a494c6e3a`, excluding the pre-existing tracker
blank line from staging while preserving it in the working tree. No push.

The owner clarified that export, import and menu are independent phases.
Phase 1B implements only objects.py export and its tests/docs. The original
downloader remains the primary behavioral reference. No object writes,
destination connection, Device update, credential transformation, LDAP,
Scheduler, master CLI/menu, deployment or recovery feature is added.

Operational values come from runtime inputs/API responses. Source containment
determines parent IDs and names; missing Site/root names may use the original
Site-by-ID lookup. Unknown or duplicate identities fail, not root-fallback.
Both tree files keep legacy fields and add source_root metadata only. Access
values are copied without mutation or redaction; only deviceAccess.ormID is
removed, with an explicit sensitive-file warning.

A necessary small foundation extension exposes existing finite GET authorization
through ApiClient.authorize_gets, since IDs/IPs are discovered after tree reads.
It does not authorize writes or change origins. No shared backend or
experimental module changes in this phase.

Independent SUCCESS/FAILED results require complete reads, save and cleanup;
cleanup failure preserves primary errors, not false success. No automatic retry,
re-login, hidden Device omission, journal or envelope. Phase 1B is not committed
or live-verified. Phase 1C import and future menu need separate owner approval.

## LF-001 - approved independent legacy-first design, 2026-11-27

Status: **owner-approved design; Phase 1A implementation/offline tests authorized**.
This current decision supersedes the historical experimental design as the
direction for new application work, without modifying or removing that engine.

- Build a basic, generic export/import application from the original working
  legacy behavior. Do not repair prior qualification runs or consume their
  artifacts as dependencies.
- Use client/config/files and independent domain modules behind a simple menu.
  Only the three foundation modules are authorized in Phase 1A.
- Reuse compatible authentication, transport, HTTPS, TLS and JSON functions.
  Do not carry forward migration states, journals, guards, recovery, registries,
  comparison gates, databases or deployment changes.
- All operational values originate at runtime, in exports or API responses.
  Source and destination IDs remain independent; portable deviceAccess is
  preserved. Optional credential changes are not required for normal export.
- A shared HTTPS backend adjustment is necessary solely for generic,
  session-authorized TLS exceptions. Its optional policy argument defaults to
  absent; old callers and their workflow-specific restrictions are unchanged.
- Login requires HTTP 200 and JSON status success, fixing unsafe HTTP-only
  acceptance without inventing version-specific authentication. Cyber Controller
  retains legacy Basic-plus-JSON, with explicit encoding errors. Cookie ownership
  and optional documented session-ID handling are reused.
- Remote logout is deferred because present legacy files do not establish a
  concrete configured binding. Local cleanup must not be called remote logout.
- Mocked tests are evidence of implementation behavior only. No live calls,
  deployment, commit or automatic Phase 1B implementation is authorized.

Implementation decisions and actual verification are tracked under
[CCV-LF-1A](PROGRESS.md#ccv-lf-1a---legacy-first-foundation). Later-phase scope and
live compatibility require separate review/authorization.

**The following decision records describe historical experimental work.**

Date: 2026-11-22

Current Windows containment contract refinement:
[E-054](PROGRESS.md#e-054---ccv-010-c-targeted-contract-and-policy-resolution-2026-11-22),
**DOCUMENTATION ONLY; NOT IMPLEMENTED; INDEPENDENT REVIEW/OWNER DECISIONS PENDING**.
Independent E-052 verdict: **REVISE DESIGN BEFORE IMPLEMENTATION**.
This is not a new owner acceptance or implementation/execution authorization.
See the [targeted resolution](#design-resolution---ccv-010-c-e-054-contract-and-policy-dispositions-2026-11-22).
Independent E-053 review supports a separately authorized nonexecuting proposal,
not implementation/qualification. Historical E-043-E-053 evidence and decision
sections remain unchanged.

Current prototype decision: **CCV-010-C OFFLINE SUPERVISED-OPERATION PROTOTYPE -
ACCEPT WITH EXPLICIT LIMITATIONS**, owner accepted **2026-11-21**.
Scope: offline supervised-operation control model only, based on independent
E-050 verification; no remaining confirmed defects within the reviewed scope.
See the [dated acceptance](#owner-prototype-acceptance---ccv-010-c-offline-supervised-operation-prototype-2026-11-21)
and [E-051](PROGRESS.md#e-051---ccv-010-c-owner-acceptance-of-offline-supervised-operation-prototype-2026-11-21).
**Full CCV-010-C milestone acceptance: WITHHELD. CCV-010-B laboratory Gates A-D:
NOT PASSED. Laboratory readiness: NOT READY. Laboratory execution: NOT AUTHORIZED.**
Production capabilities remain default-deny; concrete product dispatch remains
disabled. No import, update, delete or configuration migration is authorized.

Current CCV-010-C policy decision: **REVISED DEADLINE-CONTAINMENT POLICY APPROVED**,
2026-11-20. See the [dated decision](#owner-policy-decision---ccv-010-c-deadline-containment-2026-11-20)
and [E-047](PROGRESS.md#e-047---ccv-010-c-revised-deadline-containment-policy-2026-11-20).
This approves acceptance-policy direction only, not implementation, runtime
compatibility, laboratory execution or full milestone acceptance.

Current planning decision: **CCV-010-B PLANNING: OWNER ACCEPTED — 2026-11-19**;
**ACCEPT WITH NON-BLOCKING OBSERVATIONS**, completed offline planning and
documentation only. See the [dated B acceptance](#owner-planning-acceptance---ccv-010-b-2026-11-19)
and [E-042](PROGRESS.md#e-042---ccv-010-b-owner-planning-acceptance-2026-11-19).
Gates A-D remain **NOT PASSED**.
**NOT READY — EXECUTION NOT AUTHORIZED**.
Historical present-tense milestone passages below are preserved, not edited;
this dated decision supersedes their B pending labels only for planning scope.

## Design resolution - CCV-010-C E-054 contract and policy dispositions, 2026-11-22

**Proposed engineering dispositions only; no owner decision recorded.**
[E-054](PROGRESS.md#e-054---ccv-010-c-targeted-contract-and-policy-resolution-2026-11-22)
records four-file documentation refinement of the independent E-053 findings.
The [resolution contracts](WINDOWS_WORKER_CONTAINMENT_DESIGN.md#p-e-054-targeted-contract-and-policy-resolution)
and [readiness matrix](WINDOWS_WORKER_CONTAINMENT_DESIGN.md#p7-implementation-readiness-matrix-and-stage-gates)
control current proposals; dated E-052/E-053 sections below remain historical.

Publication ambiguity is **RESOLVED AT DOCUMENTATION LEVEL** conservatively:
internal/historical completion timestamps are not new publication authority.
Successful commitment/reporting retains E-047 current owner, authorization,
generation, release and deadline guards. Expired uncommitted or late candidates
cannot succeed; uncertain publication cannot reconstruct success; delayed
diagnostics cannot silently publish new successful state. No weakening of the
accepted policy or post-D success behavior is approved.

Required owner decisions remain proposed, not accepted:

| Topic | Required decision / evidence boundary |
| --- | --- |
| U-01 | Accept authoritative creator-failure criterion or separately approve policy narrowing; review witness versus external owner authority/failure model. Quarantine does not prove orphan prevention |
| U-04 | Appoint provisioning/trust authority; approve authenticated store/epoch/history, independent rollback checkpoint/update protocol, storage assumptions, limits and exceptional quarantine disposition |
| U-05 | Approve boot/QPC/native conversion, immutable bootstrap and explicit versioned runtime projection; no v1 relabeling or deadline renewal |
| U-06 | Approve synchronization/observation and each procedure's dispatch/in-flight criterion and residual race; no waiver after observed revocation/expiry |
| U-07 | Accept producer authentication, evidence schema/bounds/retention and independent semantic/disposition authorities; no worker self-certification |
| Publication | Retain conservative P.1 rule; any new post-deadline success publication or restart-success reconstruction needs separate policy approval |

U-01/U-04/U-05/U-06/U-07 remain **UNRESOLVED — IMPLEMENTATION BLOCKED**.
U-02/U-03/U-08 remain **CONTRACT SPECIFIED — RUNTIME QUALIFICATION PENDING**,
preserving ABI, ownership/nesting and strict bounded secured IPC. U-09 never
promises hard-real-time physical cleanup; U-10 grants no authentication, remote
revocation, live networking, product changes or capability activation.

Next recommendation: separately authorize Stage 0 independent E-054/source
review and nonexecuting Stage 1 ABI/API planning. Stages 2-5 and their dependent
runtime paths remain blocked; classification is not execution authorization.
E-047 and E-051 decisions are unchanged. Historical 491-test evidence not rerun.
No source/tests/configuration/PDF edits, Git, native processes/endpoints/stores,
network/product/laboratory activity, commit, merge or owner acceptance.
**Full CCV-010-C acceptance WITHHELD; Gates A-D NOT PASSED; default-deny.**

## Design refinement - CCV-010-C Windows containment contracts, 2026-11-22

**Status:** documentation-only proposed contracts; not implemented or owner
accepted. [E-053](PROGRESS.md#e-053---ccv-010-c-windows-containment-contract-refinement-2026-11-22)
records authorized changes to the [containment design](WINDOWS_WORKER_CONTAINMENT_DESIGN.md),
architecture, this register and progress only. E-052's independent verdict
**REVISE DESIGN BEFORE IMPLEMENTATION** is review input, not acceptance.
The E-052 section below remains a historical proposal-time record.

Selected proposed contracts:

- Conditional creation-time JOB_LIST with suspended creation; no atomic rollback,
  universal creator-crash orphan guarantee or post-create-assignment fallback.
- Explicit acquisition ownership/rights/lifetimes, including attribute values
  through list destruction, duplicates and pending I/O. Exit/accounting/closure/
  disposition are separate; nested-host incompatibility fails closed.
- Bounded append-only local NTFS journal, retained no-sharing owner guard and
  independent rollback checkpoint, with write/flush/checkpoint permission barriers.
  Unknown/torn/lost state cannot permit replacement/replay. Restart is failure-only;
  commit eligibility is not proof of final timely commitment or publication.
- Immutable identity/deadline/bootstrap capability, proposed runtime QPC authority
  without reinterpreting accepted v1's synthetic tag. One D, no deadline renewal.
- Revocation closes future permission/commit authority; proposed worker observation
  and predispatch checks retain an explicit check-to-use/in-flight residual.
  Actual external dispatch remains blocked pending separate model acceptance.
- Producer/acquisition-bound candidate/release evidence; worker declarations cannot
  establish normal exit or independently verified semantic/resource disposition.
- Protected logon-SID/System, local first-instance named pipe, exact inherited
  capabilities, overlapped client/server and bounded completion-owned buffers.
  Cancellation request is not completion; accepted v1 schema/budgets stay intact.

The [requirement-to-evidence matrix](WINDOWS_WORKER_CONTAINMENT_DESIGN.md#l1-e-053-requirement-to-evidence-disposition-matrix)
labels U-01/U-04/U-05/U-06/U-07 **UNRESOLVED — IMPLEMENTATION BLOCKED**;
U-02/U-03/U-08 **CONTRACT SPECIFIED — RUNTIME QUALIFICATION PENDING**.
The three lifetime/platform/reference corrections are **RESOLVED AT DOCUMENTATION
LEVEL**, relying on prior independent review source verification, not new network
research or OS execution. No platform assumption is resolved by documenting it.

W-01-W-20 retain historical objectives and gain mandatory failure subcases,
observable/evidence/proof-limit/fail-closed criteria. U-09 overruns and U-10
secret/session/product/egress limitations remain unresolved at runtime.
Next independently reviewable activity is nonexecuting E-053 contract review.
No test run; 491 tests remain historical. No commands/Git/processes/network,
dependencies, endpoint/store creation, PDF changes or laboratory activity.
**Full CCV-010-C acceptance: WITHHELD. Gates A-D: NOT PASSED. Production
default-deny. No owner acceptance or runtime implementation authorization.**

## Design proposal - CCV-010-C Windows worker containment, 2026-11-21

**Status:** documentation-only proposal, not accepted or implemented.
The authorized [design](WINDOWS_WORKER_CONTAINMENT_DESIGN.md) refines E-046's
Windows lifecycle seam under the E-051 accepted offline coordinator, preserving
E-047 deadline policy and E-048-E-050 framing, admission and identity safeguards.
[E-052](PROGRESS.md#e-052---ccv-010-c-windows-worker-containment-design-2026-11-21)
is design evidence only; E-043-E-051 remain unchanged.

Recommend conditional creation-time job assignment with suspended creation,
explicit membership/identity verification and one resume. Do not silently
fall back to suspended-create-then-assign. Atomic rollback, orphan prevention,
kill-on-last-close ownership, host/nested-job constraints and physical disposition
must not be inferred from API success; unresolved creation guarantees block spawn.

Parent retains all coordination/commitment/recovery authority. Worker would be
one-shot, credential/session-owning, with reference-only sanitized IPC and no
reusable session export. Prefer private local overlapped named-pipe inherited
capabilities, preserving strict v1 fields/sequence/budgets. Real clock/bootstrap,
revocation and result/release provenance require separate reviewed contracts.
Durable nonsecret ownership/intents/quarantine/high-water history are proposed,
not implemented; replacement cannot clear uncertainty or replay operations.
Termination, exit, reaping and disposition evidence remain independent; no
unconditional cleanup/report by deadline is claimed.

**Next recommendation:** separately authorized nonexecuting independent architecture/
security and authoritative Windows API/source review before implementation.
W-01-W-20 are future synthetic tests, not run or authorized here.
Historical independent **491 passing tests** were not rerun.
No application/test/configuration/PDF changes, Git operations, commands,
subprocess/network/authentication activity, dependency installation or laboratory
operations occurred. No owner acceptance is recorded.
**Full C acceptance: WITHHELD. Gates A-D: NOT PASSED. Laboratory execution:
NOT AUTHORIZED. Production capabilities remain default-deny.**

## Owner prototype acceptance - CCV-010-C offline supervised-operation prototype, 2026-11-21

**Owner decision:** **CCV-010-C OFFLINE SUPERVISED-OPERATION PROTOTYPE -
ACCEPT WITH EXPLICIT LIMITATIONS**.
**Acceptance date:** 2026-11-21. **Owner:** project owner, by explicit approval
in the project conversation. **Scope:** offline supervised-operation control
model only.

**Technical basis:** independent E-050 correction verification recommended
**ACCEPT OFFLINE PROTOTYPE WITH EXPLICIT LIMITATIONS** and found no remaining
confirmed defects within the reviewed scope. The owner accepts the
network-incapable prototype with the limitations below. This is not acceptance
of full CCV-010-C, production integration, actual Windows workers, network
connectivity or laboratory testing.

**Evidence:** [E-051 acceptance record](PROGRESS.md#e-051---ccv-010-c-owner-acceptance-of-offline-supervised-operation-prototype-2026-11-21),
the independent E-050 verification report in the project conversation, and the
preserved [E-047 policy](PROGRESS.md#e-047---ccv-010-c-revised-deadline-containment-policy-2026-11-20),
[E-048 prototype](PROGRESS.md#e-048---ccv-010-c-network-incapable-supervised-operation-prototype-2026-11-20),
[E-049 corrections](PROGRESS.md#e-049---ccv-010-c-reentrant-admission-and-supervisor-fencing-corrections-2026-11-20)
and [E-050 correction](PROGRESS.md#e-050---ccv-010-c-callback-retargeting-correction-2026-11-20).
Those historical records are preserved; this dated acceptance supersedes pending
owner acceptance only for the prototype.

### Accepted offline functionality

These are simulated/offline guarantees only:

- Strict versioned JSON IPC framing with four-byte big-endian message lengths
  and finite IPC size and structural budgets.
- Explicit coordinator state transitions, immutable operation deadlines and
  authorization-generation fencing.
- Supervisor and operation identity binding, reentrant-admission reservation
  and callback-retargeting protection.
- Candidate validation and immutable successful commitment.
- Simulated worker lifecycle, with separate termination, exit, reaping and
  resource-disposition evidence.
- In-memory quarantine/recovery and fail-closed rejection of stale or late results.
- Sanitized errors/reporting and no automatic authentication or
  configuration-write replay.

### Independently executed verification

The independent E-050 review reran **491 tests** (486 retained and five new
E-050 regression methods covering 21 scenarios), with **zero failures, errors
or skips**, in 99.018 seconds. It executed **21 direct in-memory diagnostic
scenarios** and **four additional E-049 confirmation probes**. Runtime:
**CPython 3.13.14; Windows 11 AMD64, Windows-11-10.0.26300-SP0**.

Supervised test guards observed **zero prohibited attempts across 1,650
observations**; aggregate network guards observed **zero attempts across 7,380
observations**; concrete HTTP dispatch guards observed **zero attempts across
134 observations**. Syntax parsing passed and scoped Pylance diagnostics were
empty. These are scoped Python-level observations, not OS-level isolation.
**Application tests were not rerun during this documentation-only update.**

### Corrected security findings

Independent verification passed all three corrections:

1. Reentrant admission bypass.
2. Superseded-supervisor admission.
3. Callback operation-retargeting during dispatch and commitment.

No remaining confirmed defects were identified within the reviewed scope.
Historical defects are corrected, not unresolved; E-048, E-049 and E-050 remain
unchanged evidence.

### Explicit acceptance limitations

- No actual OS worker execution, Windows Job Object containment, real process
  termination/reaping qualification or physical resource-release guarantees.
- No durable quarantine across application restarts or demonstrated multithreaded
  synchronization safety. Injected clocks and recovery evidence remain trusted.
  The prototype is not a process sandbox.
- No actual nonblocking TCP/TLS integration, DNS or whole-operation runtime
  deadline qualification. No hard-real-time guarantee is accepted.
- No live authentication or JSESSIONID qualification, Vision or Cyber Controller
  runtime compatibility, or migration execution approval.

### Mandatory restrictions and future work

- **Full CCV-010-C milestone acceptance: WITHHELD.**
- **CCV-010-B laboratory Gates A-D: NOT PASSED.**
- **Laboratory readiness: NOT READY.**
- **Laboratory execution: NOT AUTHORIZED.**
- Production capabilities remain default-deny; concrete product dispatch remains
  disabled. No import, update, delete or configuration migration operation is
  authorized.

The following require separate authorization and are not begun:

1. Actual Windows process-supervisor implementation.
2. Bounded IPC integration.
3. Windows worker creation and termination qualification.
4. Durable quarantine/recovery.
5. Approved static-address nonblocking TLS transport.
6. Independent runtime and security verification.
7. Exact lab/build/operation authorization.

This decision authorizes only acceptance documentation in
[PROGRESS.md](PROGRESS.md) and this register. No application/test changes, test
execution, Git operations, dependency installation, network/product/laboratory
operations or subsequent milestone work occurred. Stop after recording this
prototype-only acceptance.

## Owner policy decision - CCV-010-C deadline containment, 2026-11-20

**CCV-010-C — REVISED DEADLINE-CONTAINMENT POLICY APPROVED**

**Decision date:** 2026-11-20. **Owner:** project owner, by explicit decision in
the project conversation. Replace CCV-010-C's unconditional whole-operation
hard-interruption acceptance requirement with a **qualified, deadline-accounted,
fail-closed containment requirement**. This dated decision controls current
C deadline acceptance; earlier evidence and dated requirements remain historical,
not rewritten or retroactively satisfied.

The approved policy requires:

1. One immutable monotonic operation deadline, covering initial authorization,
   worker creation, authentication, transport, response/contract/cookie validation,
   commitment, cleanup and final reporting; no renewed deadline at stage boundaries.
2. Authorization, dispatch, validation and commitment checks against that deadline
   and the current authorization/operation/session generation.
3. Expired or stale operations cannot become successful.
4. No new operation dispatch after observed expiry or authorization revocation;
   serialize permission decisions with observed revocation and recheck at dispatch.
5. Late worker results cannot commit authentication, cookies, configuration or
   successful results. Failure-only recovery evidence cannot revive a retired
   generation or alter a replacement session.
6. Termination escalation when a worker exceeds its deadline.
7. Explicit worker-exit, reaping and resource-disposition evidence; a termination
   request is not confirmed exit, and confirmed exit alone is not complete release.
8. Quarantine when worker termination or resource disposition cannot be confirmed.
9. No replacement operation while required quarantine restrictions remain unresolved,
   including across parent restart/recovery.
10. No automatic replay of authentication or configuration writes.
11. Measured startup, termination, cleanup and reporting overruns on approved
    runtime/platform builds, with exact build and observation scope recorded.
12. Explicit documentation of remaining timing, scheduling and resource-lifecycle
    uncertainty, including supervisor stalls, revocation races and remote sessions.

These are required acceptance properties, not newly implemented guarantees.
The policy does **not** claim unconditional hard-real-time termination, successful
report delivery or complete resource release by deadline. Expiration detection,
failure reporting, termination request, confirmed worker exit and confirmed
resource disposition must be reported separately. A timely clock check is not
proof that a descheduled parent delivered a result before expiry; delayed reporting
cannot turn an expired operation into valid success.

**Remaining prerequisites:** exact IPC wire-contract specification; worker/session
ownership; Windows process creation and job containment; parent-crash and quarantine
recovery; authorization revocation races; termination and reaping verification;
runtime-specific deadline qualification; TLS and product compatibility qualification;
independent implementation/security review. Numeric laboratory settings remain
unapproved. No prototype or supervised-containment implementation is authorized.

**Evidence:** [E-043 safeguards](PROGRESS.md#e-043---ccv-010-c-offline-http-safety-hardening-2026-11-19),
[E-044 corrections and historical 425-test verification](PROGRESS.md#e-044---ccv-010-c-review-and-authorized-corrections-2026-11-19),
[E-045 initial design](PROGRESS.md#e-045---ccv-010-c-architecture-a-offline-design-2026-11-19),
[E-046 revised design](PROGRESS.md#e-046---ccv-010-c-design-revision-and-supervised-containment-2026-11-20),
the independent E-046 technical/security review in the project conversation
(ACCEPT REVISED DESIGN WITH EXPLICIT LIMITATIONS), and this separate owner policy
decision. [E-047](PROGRESS.md#e-047---ccv-010-c-revised-deadline-containment-policy-2026-11-20)
records the update; no application tests were rerun.

**Mandatory boundaries:** production capabilities remain default-deny; concrete
laboratory dispatch remains disabled. No product authentication, laboratory
connections, configuration import/update/deletion or runtime compatibility is
authorized or established. **CCV-010-B Gates A-D remain NOT PASSED. Full CCV-010-C
milestone acceptance remains withheld.** Approval of this policy direction passes
no readiness gate and authorizes no subsequent milestone.

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

The owner separately accepted **CCV-004-C3's completed offline-only scope on
2026-11-18**, using E-030 as the latest correction evidence: 321 passing tests,
zero guarded network attempts, and no remaining confirmed acceptance blockers.
This does not establish live compatibility, authorize import execution or a
next milestone, encrypt retained records, transfer file-permission responsibility
from the operator, or guarantee cleanup when permissions prevent deletion.

The owner separately accepted **CCV-009-A's completed static discovery scope on
2026-11-18: ACCEPT WITH NON-BLOCKING OBSERVATIONS**. E-032 and the completed
independent technical acceptance review support this decision; E-033 in
[PROGRESS.md](PROGRESS.md) records it. No real-version compatibility or production
readiness is established. B's later, separately authorized offline scope and
owner acceptance are recorded below; A's historical next-milestone boundary
remains preserved in its dated decision.

The project owner separately accepted **CCV-009-B — ACCEPT WITH NON-BLOCKING
OBSERVATIONS** on **2026-11-18**, exclusively for version-pinned offline API
evidence and bounded schema qualification. **CCV-009-B: OWNER ACCEPTED —
2026-11-18**. E-035, E-036 and the independent technical acceptance review are the
accepted evidence; [E-037](PROGRESS.md#e-037---ccv-009-b-owner-acceptance-with-non-blocking-observations-2026-11-18)
records the owner decision. This grants no runtime compatibility, live
integration, migration execution or subsequent milestone authorization.

The project owner explicitly accepted **CCV-010-A — ACCEPT OFFLINE SCOPE**
on **2026-11-19**, exclusively for the concrete HTTPS backend's offline
implementation and verification. **CCV-010-A: OWNER ACCEPTED — 2026-11-19**.
E-038 implementation, E-039 corrections and independent verification of all
four corrected findings support the decision;
[E-040](PROGRESS.md#e-040---ccv-010-a-owner-offline-acceptance-2026-11-19)
records it. No live connectivity, production activation or migration execution
is authorized. **CCV-010-B: PROPOSED — NOT AUTHORIZED**; not started.

| ID | Proposed decision | Approval status | Related milestone |
| --- | --- | --- | --- |
| ADR-001 | Modular Python master CLI with explicit module registry | Architectural direction approved by owner, 2026-11-17 | CCV-002, CCV-007 |
| ADR-002 | Product-specific clients over shared transport and explicit sessions | Direction approved; implemented CCV-003 mock-only scope accepted, 2026-11-17 | CCV-003 |
| ADR-003 | Versioned artifacts, destination mappings, and plan integrity | Direction approved; A offline scope accepted, 2026-11-17; B/C1 integration and C2 reconciliation/provenance/planning integrity accepted offline-only, 2026-11-18 | CCV-002, CCV-004 |
| ADR-004 | Separate offline planning, online preflight, approval, apply, and verification | Direction approved, 2026-11-17; B and C2 offline planning/safety gates accepted, 2026-11-18; live/apply stages not authorized | CCV-002, CCV-007 |
| ADR-005 | Preserve semantics; block ambiguous or unsafe transformations | Direction approved; A preservation/Option 1 accepted, 2026-11-17; B/C1 fidelity controls and C2 qualified associations/acknowledgements/validated exclusions accepted offline-only, 2026-11-18 | CCV-004 through CCV-006 |
| ADR-006 | Capability/evidence gating by product and version | Direction approved; synthetic isolation accepted, 2026-11-17; B version-pinned offline evidence/subsets accepted with non-blocking observations, 2026-11-18; runtime qualification pending/default-deny | CCV-003, CCV-008, CCV-009-B |
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
At that acceptance checkpoint C3 remained **unauthorized and not started**.
Its subsequent separate authorization and acceptance below supersede that
historical boundary only for C3's completed offline scope. No application code
or tests are changed by either documentation-only acceptance record.

## Owner implementation acceptance - CCV-004-C3, 2026-11-18

**Owner:** project owner, by explicit decision in the project conversation.
**Decision:** accept **CCV-004-C3 for its completed offline-only scope** under the
existing architecture decisions. This is implementation acceptance, not live
product qualification, import approval, or authorization to begin another milestone.

Accepted scope includes the controller-specific master offline workflow,
versioned local declarations, existing normalization/reconciliation/acknowledgement
integration, comparison and candidate-plan integrity verification, minimal planning
CLI, redacted reports, credential-safe record retention, distinct failure statuses,
and sanitized output-cleanup reporting with safe original-operation context.

Accepted evidence:

- **321 tests passed**.
- **Zero guarded network attempts**.
- **No remaining confirmed acceptance blockers**.
- [E-030](PROGRESS.md#e-030---ccv-004-c3-final-cleanup-failure-context-2026-11-18)
  is the latest correction evidence: full suite passed in 46.619 seconds, exit 0;
  focused workflow suite passed 30 tests in 6.934 seconds.
- [E-031](PROGRESS.md#e-031---ccv-004-c3-owner-acceptance-2026-11-18)
  records this owner decision. These are existing results, not tests rerun for
  this documentation update; guards are not OS-level network isolation.

Mandatory limitations remain:

- No live product compatibility or official schema qualification is established.
- Access completeness and credential portability remain unverified; local
  evidence is a trusted offline assertion, not authenticated production approval.
- No import execution, production configuration changes, live API requests,
  or real HTTP backend is authorized.
- Retained records are plaintext, not encrypted. Operators control filesystem
  permissions and protected storage; no guaranteed access protection is claimed.
- Cleanup cannot guarantee deletion when permissions or OS/audit policy prevent
  it. A partial file may remain and requires operator inspection after the
  explicit cleanup-failure report.
- No Git operations, application changes, or next-milestone work are authorized.

This acceptance supersedes earlier C3 acceptance-pending labels only for the
completed offline scope. Only this register and the progress tracker are updated.

## Owner discovery acceptance - CCV-009-A, 2026-11-18

**Owner:** project owner, by explicit decision in the project conversation.
**Milestone:** CCV-009-A - Product Compatibility and API Discovery.
**Decision:** **ACCEPT WITH NON-BLOCKING OBSERVATIONS**.
**Date:** **2026-11-18**.
**Status:** **CCV-009-A: OWNER ACCEPTED - 2026-11-18.**
**Scope accepted:** static legacy API discovery, compatibility evidence
classification and automation-gap analysis only.

Accepted evidence:
[E-032](PROGRESS.md#e-032---ccv-009-a-static-product-compatibility-and-api-discovery-2026-11-18)
and the completed independent technical acceptance review. The formal owner
decision and review results are recorded in
[E-033](PROGRESS.md#e-033---ccv-009-a-owner-acceptance-with-non-blocking-observations-2026-11-18).
This is static discovery acceptance under the existing evidence gates, not a
production-compatibility decision or authorization to begin another milestone.

Independently verified and accepted findings:

- **22 legacy files**, **13 byte-distinct implementations**, **nine duplicate
  copies**.
- **12 concrete HTTP method/path combinations**, **10 concrete path templates**,
  **four unresolved scheduler references**, **16 logical operation records**.
- **17 product-specific API matrix rows**, **all 18 required fields present**,
  **eight of eight documented source fingerprints matched**.
- **Ten automation-gap candidates** and **ten prioritized discovery items**.
- **Zero confirmed acceptance-blocking defects**, **one LOW non-blocking
  documentation observation**, and **no confirmed discovery-related security
  vulnerabilities**. Production capability restrictions remained intact.

The independent review inspected the three discovery deliverables, cross-checked
canonical legacy implementations, verified operation traceability and
documentation consistency, and verified production capabilities remain
default-deny. Read-only static checks completed successfully, reported zero
guarded network attempts and made no project changes.

The **321 passing application tests are historical CCV-004-C3 evidence**
(E-030/E-031), not a fresh CCV-009-A run. They were not rerun during A, its
independent review or this documentation-only acceptance update.

### Accepted non-blocking observation

- **Severity:** LOW.
- **File / location:** [ARCHITECTURE.md](ARCHITECTURE.md), approximately
  **1905-1907**.
- **Issue:** an older C1/C2 acceptance checkpoint is not clearly identified as
  historical.
- **Impact:** potential reader confusion about previously completed approval
  gates; no unsafe execution is enabled.
- **Decision:** accepted as non-blocking.
- **Follow-up:** correct during a separately authorized documentation-maintenance
  task. That file is not modified under this authorization.

### Mandatory limitations and next milestone

- APSolute Vision **5.4.x** and Cyber Controller **10.10.x** remain unverified
  target version families. Neither **Vision-to-CC** nor **CC-to-CC** compatibility
  is established. Exact patch releases and independent source/destination builds
  require qualification; no blanket family compatibility is certified.
- Vendor API documentation and complete request/response schemas remain
  outstanding. Scheduler API paths remain unresolved.
- Credential portability remains unverified. Authentication, RBAC, inventory
  completeness and asynchronous completion require qualification.
- Full backup/recovery functionality is not established. Partial JSON exports
  are not qualified full product backups.
- No production migration execution is authorized. Static discovery acceptance
  is not production readiness, live compatibility, capability activation or
  approval for a real backend, API request, authentication or configuration write.
- Existing C3 limitations remain: plaintext retained records, operator-controlled
  permissions/protected storage and no guaranteed cleanup deletion when
  permissions prevent it.

**CCV-009-B: PROPOSED - NOT AUTHORIZED; not started.**
Proposed scope only:

- Version-pinned vendor documentation acquisition.
- Offline API request/response schema qualification.
- Exact product build evidence.
- Operation-level compatibility assessment.
- Outstanding scheduler and migration capability investigation.

None of these activities is started or authorized by this decision. Only
[PROGRESS.md](PROGRESS.md) and this register are updated. No application/test/API
definition changes, other documentation changes, dependencies, legacy execution,
Git operations or product operations are performed.

This acceptance supersedes earlier A acceptance-pending labels only for the
completed static scope. Preserve E-032, historical C3 evidence and all limitations;
separate authorization is required for every follow-up.

The B-not-authorized paragraph above is the historical A-decision checkpoint.
Later B authorization, implementation and the separate owner decision below
supersede it only for B's explicitly accepted bounded offline scope.

## Owner offline qualification acceptance - CCV-009-B, 2026-11-18

**Owner:** project owner, by explicit decision in the project conversation.
**Milestone:** CCV-009-B.
**Decision:** **ACCEPT WITH NON-BLOCKING OBSERVATIONS**.
**Acceptance date:** **2026-11-18**.
**CCV-009-B: OWNER ACCEPTED — 2026-11-18**.

This accepts version-pinned **offline API evidence and schema qualification
only**, under the existing evidence, artifact and planning boundaries. It is not
a new ADR, verified runtime compatibility, production readiness or migration
execution authorization.

### Accepted scope and evidence

- Vendor documentation evidence analysis.
- Exact version-specific evidence bindings.
- Bounded offline schema qualification.
- Evidence-artifact preservation.
- Evidence-only planning restrictions.
- Synthetic asynchronous-operation interpretation.
- Permanent offline regressions.

Accepted references:
[E-035](PROGRESS.md#e-035---ccv-009-b-approved-vendor-pdf-analysis-2026-11-18),
[E-036](PROGRESS.md#e-036---ccv-009-b-offline-subset-qualification-2026-11-18),
and the completed independent technical acceptance review in the project
conversation on 2026-11-18, which recommended **ACCEPT WITH NON-BLOCKING
OBSERVATIONS**. The formal owner-acceptance evidence record is
[E-037](PROGRESS.md#e-037---ccv-009-b-owner-acceptance-with-non-blocking-observations-2026-11-18).

Accepted verification:

- **350 application tests passed**, comprising **321 existing regressions**
  and **29 new permanent tests**.
- **Eight additional guarded acceptance probes passed**.
- **Six delegated security-subset tests passed**; these repeat selected
  permanent tests rather than add six unique application tests.
- **No confirmed acceptance-blocking defects**.
- **No confirmed exploitable vulnerabilities within the reviewed scope**.
- **Clean Pylance diagnostics** across the four reviewed Python files.

| Network-guard scope | Attempts | Observations |
| --- | --- | --- |
| New permanent tests | **0** | **435** |
| Additional acceptance probes | **0** | **120** |
| Delegated security subset | **0** | **90** |

These are **scoped Python-level measurements, not OS-level isolation** or an
aggregate count for all tests, subprocesses or uninstrumented calls.
These are previously completed implementation/review results, **not new tests
or probes executed for this documentation-only owner-acceptance update**.

### Accepted non-blocking observations

The recommendation to add permanent regressions is accepted for:

1. Evidence-artifact serialization and verification boundaries.
2. Forged planning records with recomputed identities/hashes.
3. Controller-specific evidence-artifact rejection.
4. Standard artifact contract reparsing.

These are **follow-up improvements, not blockers**. Acceptance does not
authorize their implementation now or start another milestone.

### Mandatory limitations and vendor reference handling

- Vision **5.4.9 runtime compatibility remains unverified**.
- Cyber Controller **10.10.7 runtime compatibility remains unverified**.
- The CC **10.10.6 PDF metadata discrepancy remains unresolved**, despite the
  10.10.7 cover/overview. No adjacent patch or whole version family is qualified.
- Complete **DevicePojo creation schemas remain unqualified**.
- **DeviceAccess nullability remains unverified**.
- **Credential portability remains unverified**.
- **Real asynchronous completion behavior remains unverified**; synthetic
  interpretation cannot establish configuration success.
- **Exact independent deployment builds require confirmation**.
- **Live destination preflight remains unimplemented**; supplied offline
  inventory assertions do not establish it.
- **Complete source inventory/export remains unverified**.
- **Vision-to-CC and CC-to-CC migration compatibility remain unqualified**.
- **No migration execution is authorized**. Production capabilities remain
  **default-deny**. No live backend, API request, product authentication,
  configuration execution or production capability activation follows from
  this decision. Existing credential, acknowledgement, identity/integrity,
  retained-record and cleanup protections/limitations remain unchanged.

The vendor PDFs are **local reference materials**:

| Document identity | Local filename | SHA-256 |
| --- | --- | --- |
| APSolute Vision 5.4.9 REST API | `APSolute-Vision-5.4.9-REST-API.pdf` | `827d4954cf5390f3a242e8bbb0af4dc7dd9ce68f5c17eba19449cf45a8d9d5c4` |
| Cyber Controller 10.10.7 REST API; unresolved 10.10.6 metadata | `Cyber-Controller-10-10-7-Rest-API.pdf` | `f6c7e474cb2df25d5d1b7b52da94f13f9b5013649419fc4276f49bd153e2d587` |

E-035/E-036 document identities, hashes and page provenance are preserved.
No PDF is staged, moved, deleted, modified or committed by this task.
**Repository storage disposition remains subject to organizational approval**;
approval for local reference use is not approval for repository storage.
No Git state is inspected or changed.

Only [PROGRESS.md](PROGRESS.md) and this register are modified for acceptance.
No application code, tests, other documentation, PDFs, dependencies or legacy
files are modified; no API/product authentication requests, configuration
execution, Git operations or production capability activation are performed.
Any future live integration or migration execution requires **separate milestone
scoping and authorization**. Follow-up implementation likewise requires separate
authorization. **No subsequent milestone is started.**

## Owner offline backend acceptance - CCV-010-A, 2026-11-19

**Owner:** project owner, explicitly approved in the project conversation.
**Milestone:** CCV-010-A.
**Decision:** **ACCEPT OFFLINE SCOPE**.
**Acceptance date:** **2026-11-19**.
**CCV-010-A: OWNER ACCEPTED — 2026-11-19**.

This accepts only the concrete HTTP backend's offline implementation and
verification under the existing transport/session and capability boundaries.
It is not a new ADR, product-compatibility certification, production activation
or migration-execution authorization.

### Accepted functionality

- Concrete standard-library HTTPS backend.
- Mandatory TLS certificate and hostname verification.
- Separate connection and read timeouts.
- No backend retries or automatic redirects.
- Independent source/destination cookie handling.
- Structured and sanitized errors.
- Safe response and connection cleanup.
- Preserved HTTP 401 expiration behavior.
- Cleanup-failure retry suppression.
- Atomic cookie updates.
- Fail-closed malformed-header handling.
- Existing production capability restrictions.

### Evidence and independent verification

Implementation evidence: **E-038**. Correction evidence: **E-039**.
Formal owner-acceptance record:
[E-040](PROGRESS.md#e-040---ccv-010-a-owner-offline-acceptance-2026-11-19).
The completed independent technical verification recommended
**ACCEPT CCV-010-A OFFLINE SCOPE** and confirmed all four original findings
corrected:

1. HTTP 401 obscured by later failures.
2. Implicit cleanup failures permitting inappropriate retries.
3. Cookie-parser diagnostics and silent state loss.
4. Malformed headers concealing subsequent fields.

**No confirmed acceptance-blocking defects remain within the reviewed offline
scope.** Accepted verification:

- **394 application tests passed**: **380 retained tests** and **14 new
  correction regressions**; **zero failures, errors or skips**.
- **Python 3.13.14 on Windows AMD64**.
- **41 additional guarded scenarios passed**.
- Backend network guards: **0 attempts across 660 observations**, scoped to
  **44 backend test methods**.
- Concrete dispatch spies: **0 calls across 88 observations**, in that same
  backend-test scope.
- Syntax and Pylance diagnostics: **no scoped errors or warnings**.

These are **previously completed implementation/review measurements**, not
tests, probes or diagnostics rerun for this documentation-only acceptance
update. They are **scoped Python-level evidence, not OS-level isolation or
suite-wide aggregate measurements**.

### Non-blocking improvement

Make the additional cookie-conversion failure-after-deletion probe a permanent
regression. This is **not an acceptance blocker** and does not authorize its
implementation during this acceptance update.

### Mandatory limitations and next-milestone boundary

- Actual TLS handshakes remain unverified.
- DNS resolution is not bounded by the configured socket timeouts.
- Total HTTP transfer duration is not bounded.
- Response-body size is not capped.
- Real-product cookie behavior remains unverified.
- Other Python interpreter versions remain unqualified.
- Header validation depends on parser-exposed defects.
- Private cookie helpers require interpreter-version regression qualification.
- Vision and Cyber Controller runtime compatibility remains unverified.
- Production capabilities remain **default-deny**.
- No live product client, live product connectivity, production activation,
  migration executor or migration execution is authorized.
- Prior API/schema/identity/credential/migration and vendor-PDF provenance
  limitations remain unchanged.

This supersedes historical A acceptance-pending/withheld labels only for the
accepted offline scope. E-038/E-039 and earlier acceptance records remain
preserved. Only this register and [PROGRESS.md](PROGRESS.md) are modified.
No application code, tests, other documentation or vendor PDFs are modified;
no Git operations, dependency installations, live API requests, product
authentication, configuration changes or production activation are performed.

**CCV-010-B: PROPOSED — NOT AUTHORIZED**. It has not been started. All further
implementation or live work requires separate scope and explicit authorization.
Stop after recording acceptance.

## Owner planning acceptance - CCV-010-B, 2026-11-19

**Owner:** project owner, explicitly approved in the project conversation.
**Milestone:** CCV-010-B laboratory qualification planning.
**Decision:** **ACCEPT WITH NON-BLOCKING OBSERVATIONS**.
**Acceptance date:** **2026-11-19**.
**CCV-010-B PLANNING: OWNER ACCEPTED — 2026-11-19**.

### Accepted deliverable and evidence

The owner accepts the completed offline planning/documentation deliverable,
including [LAB_QUALIFICATION_PLAN.md](LAB_QUALIFICATION_PLAN.md), not backend
implementation readiness, live product compatibility or execution of the
proposed procedure. This is not a new ADR or authorization to begin another
milestone.

The unchanged [E-041 planning record](PROGRESS.md#e-041---ccv-010-b-laboratory-readiness-planning-2026-11-19)
and the completed independent technical acceptance review in the project
conversation are the evidence.
[E-042](PROGRESS.md#e-042---ccv-010-b-owner-planning-acceptance-2026-11-19)
records this owner decision. The independent review recommended
**ACCEPT WITH NON-BLOCKING OBSERVATIONS — planning scope only**, found
**no acceptance-blocking planning defects**, and identified **no confirmed
vulnerabilities within the reviewed planning deliverables**. These bounded
findings do not certify application security or live readiness.

The review was static and read-only, with no file modifications, application
tests, Git operations, network requests or product/laboratory operations.
No application tests were rerun for the review or acceptance documentation.
Historical CCV-010-A evidence remains **394 passing tests** under E-040;
Python-level guard evidence is not OS-level network isolation. No new runtime
verification or real product compatibility is established.

### Gates and laboratory readiness

All four authorization gates remain **NOT PASSED**:

| Gate | Outstanding authorization/evidence boundary | Status |
| --- | --- | --- |
| A | Version, build and operation evidence | NOT PASSED |
| B | Backend safeguards and offline qualification | NOT PASSED |
| C | Laboratory targets, accounts, permissions and evidence handling | NOT PASSED |
| D | Separate execution authorization | NOT PASSED |

**Laboratory readiness: NOT READY — EXECUTION NOT AUTHORIZED**.
Planning acceptance does not approve any gate, target, account or operation.

### Future execution blockers

1. Enforced DNS-resolution deadlines.
2. Absolute HTTP operation deadlines.
3. Streaming HTTP response-size limits.
4. Explicit destination and operation allowlisting.
5. Qualified authentication and JSESSIONID handling.
6. Approved session disposition and cleanup, distinguishing local release
   from remote revocation or verified bounded expiry.
7. Independent product/build verification.
8. Approved laboratory targets, accounts, data retention and exact procedure.

None is implemented, waived or approved by this acceptance. The reference
scope remains Vision 5.4.9 and Cyber Controller 10.10.7-labelled documentation,
with the unresolved Cyber Controller **10.10.6/10.10.7 PDF metadata discrepancy**
preserved. No adjacent-version compatibility or compatibility based on
historical documentation is inferred.

### Non-blocking observation

Historical architecture/decision passages contain outdated present-tense
milestone statements. Those passages remain unchanged during this acceptance
task. A separate documentation cleanup may be performed only under future
authorization. This dated decision updates completed B planning acceptance
without rewriting historical evidence or broadening its scope.

### Mandatory boundaries and stop

- Production capabilities remain **default-deny**.
- No live API backend has been activated.
- No laboratory connection has been authorized.
- No connectivity, authentication, API requests, configuration changes,
  production activation or execution of the proposed procedure is authorized.
- No imports, writes, deletes or migration execution are authorized.
- Existing authentication and controller-planning safety restrictions remain
  unchanged.
- Acceptance establishes no runtime compatibility for either Vision-to-CC
  or CC-to-CC migration.
- Further implementation requires separate scope authorization.

Only this register and [PROGRESS.md](PROGRESS.md) are modified for acceptance.
Static verification covers decision/date/scope consistency, unchanged E-041
and historical evidence, retained links, Markdown formatting and file hashes.
No application code, tests, other documentation, legacy scripts, vendor PDFs
or configuration files are modified. No application tests, Git operations,
network requests, dependency installation, backend-safeguard implementation,
laboratory execution or subsequent milestone is performed. Stop after this
acceptance documentation.

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

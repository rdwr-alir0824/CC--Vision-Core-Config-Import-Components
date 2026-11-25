# Future dependency-aware import coordinator

Status: **design only; configuration imports remain disabled**. This document
does not qualify endpoints, mappings, release compatibility or production timings.
No state model, sleeps, polling, environment settings or write dispatch were
implemented in this launcher milestone. Existing offline planning remains
non-executable; the menu exposes only implemented read-only/offline operations.

## Eligibility before execution

Require independently verified destination release/schema/read/write contracts,
approved source/destination root and Site mappings, unambiguous destination
identities, dependency references, needed private credentials and explicit
operation approval. Successful backups and tree snapshots are not eligibility.
Do not reuse source IDs, names, addresses or equal identifiers as proof of
destination identity. Scheduler and LDAP destination contracts remain unqualified.

## Intended presentation sequence, with actual dependency edges

| Stage | Required qualification and completion evidence |
| --- | --- |
| 1. Sites/root hierarchy | Approved root mapping; eligible Sites parent-before-child; confirm the required destination parent identity before creating a child |
| 2. Devices | Qualified Alteon/DefensePro field/form-factor/credential transforms; existing prerequisite Sites; record verified destination identities, never source aliases |
| 3. Device stabilization | Qualified destination reads, resolved references, bounded polling/timeout and optional minimum settling delay; elapsed time is not success |
| 4. Scheduler | Qualified contracts and Device/other references; enable only tasks whose actual prerequisites are verified |
| 5. LDAP permissions | Qualified authorization scopes, credentials, identities and actual dependencies; do not invent a dependency on Scheduler for every LDAP object |
| 6. Final verification | Qualified read-back of eligible creates/updates; report success, failed, skipped, blocked and indeterminate operations and unresolved references |

The stage list is an intended operator presentation order, not proof of a total
dependency chain. Represent concrete edges per object, including within a stage.
Reject dependency cycles and unresolved prerequisites. A timeout/failure blocks
dependent nodes/stages; independent eligibility must remain distinguishable.
No hierarchy/root fallback, authorization broadening or automatic rollback.

## Proposed timing configuration (not active or production-validated)

| Future advanced setting | Proposed initial value | Proposed implementation bounds |
| --- | --- | --- |
| `CCV_IMPORT_OBJECT_DELAY_SECONDS` | 2 | 0-3600 seconds |
| `CCV_IMPORT_STAGE_DELAY_SECONDS` | 10 | 0-3600 seconds |
| `CCV_IMPORT_DEPENDENCY_TIMEOUT_SECONDS` | 120 | 1-3600 seconds |
| `CCV_IMPORT_POLL_INTERVAL_SECONDS` | 5 | 0.1-60 seconds; no greater than dependency timeout |

Future configuration must parse finite numeric seconds, reject blank/negative/
NaN/infinity/out-of-bound values and invalid cross-field combinations, and
report configuration errors rather than substitute defaults for invalid input.
Omitted values alone may use qualified defaults. Advanced operator-approved
settings must be configurable without source edits and need no normal menu
prompts. Bounds/defaults require laboratory review before implementation.

Object/stage delays are pacing/minimum settling controls only. Read verification
is always required. Use monotonic bounded dependency deadlines; pacing, polling
and server `Retry-After` waits must respect the remaining budget. If a required
server wait cannot fit, block/time out rather than poll early. Qualified
idempotent reads may honor bounded rate-limit retries. Never automatically retry
a non-idempotent create after transport uncertainty: mark **indeterminate**,
retain evidence and reconcile through qualified reads before deciding whether
anything may be submitted again.

## Future state and interruption contract

Proposed states: pending, ready, executing, verifying, verified, failed, skipped,
blocked and indeterminate. Verified means authoritative completion/read-back,
not merely HTTP acceptance. Persist approved input/context identity, actual
dependency edges, per-operation outcomes, established destination IDs and safe
verification/checkpoint evidence, never passwords/cookies. Partial failures
must remain visible in the final report.

On interruption, stop new writes, retain verified IDs and distinguish unknown
completion from failure. Future resumability must reconcile checkpointed
destination state first; never assume already-created objects can be recreated.
No automatic rollback claim without a separately tested recovery mechanism.

## Smallest subsequent implementation

After endpoint/schema/mapping qualification, implement a small offline-only
dependency-state model with tests for parent ordering, explicit LDAP edges,
timeouts, failed prerequisites, indeterminate creates, interruption and resumed
state reconciliation. Do not enable any write stage merely by adding timing
configuration or this model. Live execution needs separate authorization.

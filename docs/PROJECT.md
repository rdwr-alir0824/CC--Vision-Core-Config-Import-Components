# Project Foundation

## CCV Core product and deployment direction - 2026-11-28

The owner approved CCV Core as a portable engineering product
for independent deployments by different engineers across
different customer environments.

Product requirements:

- Generic Vision and Cyber Controller configuration workflows.
- No customer-specific source code or operational values.
- Independent appliance-local container execution.
- No external production utility server.
- Native Docker as the primary deployment method.
- Docker Compose retained as an optional deployment method.
- Centrally built, versioned and qualified release images.
- Offline-capable installation and operation.
- Runtime controller settings, credentials and protected file paths.
- Consistent security controls across deployment methods.
- Documented compatibility, installation, upgrades and rollback.

Engineers consuming a qualified release should not require
Git, Python, VS Code, Copilot or the development repository.

The initial release candidate is ccv-core:0.1.0.
Version 1.0.0 remains a future qualified distribution milestone.

This deployment authorization supersedes earlier phase-specific
exclusions of deployment preparation only. Existing application
scope, security requirements and separate live approval gates
remain unchanged.

No experimental migration framework, recovery engine, database
or customer-specific implementation is introduced.

## Current objective and authorization - legacy-first redesign, 2026-11-27

The owner approved a simple, generic Vision-to-Cyber Controller export/import
application, based primarily on the original [legacy scripts](../legacy/).
The redesign is independent of the experimental migration implementation and
historical qualification runs. Older foundation statements below are retained
as dated history, not current implementation instructions.

Task **CCV-LF-1A** implemented the now owner-approved foundation: new
[client](../src/cc_vision_import/client.py),
[configuration](../src/cc_vision_import/config.py) and
[JSON helpers](../src/cc_vision_import/files.py), offline/mocked tests and
existing-document updates. These are implemented; verification evidence is in
[PROGRESS.md](PROGRESS.md#ccv-lf-1a---legacy-first-foundation).
Its local checkpoint is `c0d6b98854cc9ede3a398a476005ce2a494c6e3a`;
only approved Phase 1A changes were staged. The pre-existing tracker edit was
left unstaged and preserved; no push occurred.

**CCV-LF-1B** authorizes generic Site/Device export only:
[objects.py](../src/cc_vision_import/objects.py) and a dedicated offline/mocked
test module. Source Physical/Organization roots, recursive Sites/Devices,
source parent relationships and copied deviceAccess are exported independently.
The exact JSON is `source_root`, `sites`, `devices`; there is no backup envelope,
destination metadata or migration-state dependency. The only foundation change
exposes existing finite, same-origin GET authorization for dynamically discovered
source IDs/IPs. No experimental implementation or launcher is changed.

Operational controller addresses, credentials, hierarchy names, Device types,
management addresses and IDs must come from runtime inputs, exported JSON or
API responses. Source IDs never become destination IDs by assumption. Export
and import remain independent, and supported deviceAccess values must remain
portable. Synthetic tests use independent source/destination identities.

Excluded: changes to experimental workflows, historical artifacts as inputs,
journals, recovery/resume/rollback engines, capability registries, databases,
deployment changes, customer-specific behavior and unapproved features.
Legacy sources remain read-only. Phase 1A staging/local commit was explicitly
authorized; Phase 1B staging/local commit is authorized after passing closure.
Pushes and live requests are not authorized.
Import and destination object writes remain out of Phase 1B scope; Phase 1C
was separately authorized only after passing/committed Phase 1B closure.

The owner conditionally approved Phase 1B and authorized closure: atomic
single-file JSON saves, explicit portable importer contract, final complete
regressions including skipped reasons, complete diff review and local checkpoint
excluding the historical tracker edit. Phase 1C import-only implementation is
authorized only after that closure passes; no master menu or live calls.
Closure passed (848 tests: 846 passed/two environment-dependent skips), with
local checkpoint `0ee1b142fbcf07fc593f249b02f8713c50f5db2c`.

**CCV-LF-1C** now implements independent import in the existing objects module:
portable-file validation before login, one destination session, explicit tree/
root mapping, parent-first Sites then Devices, destination-scoped identity
matching, exact minimal legacy POSTs and bounded hierarchy readback. No source
communication, automatic retries, advanced contract gates or new dependencies.
Dedicated synthetic tests cover successful/skipped/failed objects and safe
errors/cleanup. Final offline acceptance: 97 focused tests passed; 888 complete
regressions, 886 passed/two environment-dependent skips. Phase 1C remains
not live-qualified. Its closure checkpoint is
`b7ba305279c39d030cd2f3f77a137dd0795e9942`; only approved code/tests/docs staged,
preserving the historical tracker edit. No push.

**CCV-LF-1D** adds the authorized thin master CLI and dedicated offline tests.
It reuses runtime configuration and independent export/import; safe validated
previews and an optional post-discovery confirmation hook are the only import
interface changes. Login interruption cleanup addresses a demonstrated Ctrl+C
gap without modifying the experimental engine. TLS remains verified by default,
passwords hidden, writes/replacements explicitly confirmed, live dispatch opt-in
and separately authorized. No new dependencies, deployment or launcher changes.
Phase 1D passed offline acceptance: 134 focused tests; 925 full tests,
923 passed/two environment-dependent skips. Closure passed complete review with
unchanged production/tests; the owner authorized a local checkpoint and annotated
checkpoint/legacy-first-offline-qualified tag. Linux/live verification remains
unperformed; only subsequent deployment/qualification instructions are authorized.
Device updates, transformations, LDAP/Scheduler,
deployment and Phase 1E live qualification remain excluded.

Source-observed API intent, mocked validation and exact live-verified behavior
remain separate evidence levels. These phases establish no live product/version
compatibility or credential-portability certification.

Date: 2026-11-17  
Milestone: CCV-001 - Project Foundation  
Status: Documentation implemented; architecture review pending.

## Mission and objectives

CC -Vision Core Config Import Components is a proposed modular Python
application for exporting, importing, migrating, comparing, and validating
configuration between Radware APSolute Vision and Radware Cyber Controller
environments.

Objectives:

- Preserve useful legacy behavior while consolidating duplicate code.
- Centralize connections, authentication, session cleanup, and error handling.
- Separate migration domains behind a master controller.
- Separate export, offline transformation, planning, import, and verification.
- Validate dependencies and destination mappings before changing configuration.
- Produce redacted, structured outcomes instead of relying on console success.
- Track compatibility by product and version; investigate APIs only with approval.

This is a target, not a claim that cross-product migration currently works.
The [architecture](ARCHITECTURE.md) and [decisions](DECISIONS.md) await approval.

## Evidence and boundaries

The project instructions in
[copilot-instructions.md](../.github/copilot-instructions.md) and all byte-distinct
legacy sources were inspected statically. SHA-256 comparison identified
byte-identical copies. No legacy module was imported or executed.

Source code establishes attempted behavior, not vendor support or successful
execution. No official API references, supported-version list, test fixtures,
dependency manifest, application modules, or runtime test results were found in
the inspected project inventory. No live requests were made.

See the [API matrix](API_MATRIX.md) for per-operation evidence.

## Script inventory

There are **22 script files, 13 byte-distinct implementations, and nine duplicate
copies**. Paths in the copy column identify byte-identical copies as inspected,
not independent capabilities or a recommendation to delete them.

| Reference implementation | Identical copy | Source-observed purpose |
| --- | --- | --- |
| [Object downloader](../legacy/app/download_cybercontroller_objects.py) | [Copy](../legacy/cc-objects/app/download_cybercontroller_objects.py) | Export Physical and Organization sites/devices and retrieve device-access settings. |
| [Object uploader](../legacy/app/upload_cybercontroller_objects.py) | [Copy](../legacy/cc-objects/app/upload_cybercontroller_objects.py) | Create sites, then devices, for both trees. |
| [Object updater](../legacy/app/update_cybercontroller_objects.py) | [Copy](../legacy/cc-objects/app/update_cybercontroller_objects.py) | PUT device configuration; does not update sites. |
| [Credential transformer](../legacy/app/update_json_credentials.py) | [Copy](../legacy/cc-objects/app/update_json_credentials.py) | Offline CLI, HTTP, HTTPS, and SNMPv3 credential transformation in Organization export JSON. |
| [Application shell helper](../legacy/app/run.sh) | [Copy](../legacy/cc-objects/app/run.sh) | Sleep to keep a container available; not a migration orchestrator. |
| [LDAP downloader](../legacy/download_ldap_permissions%20%281%29.py) | [Copy](../legacy/ldap_permissions/download_ldap_permissions%20%281%29.py) | Export LDAP permission entries. |
| [LDAP uploader](../legacy/upload_ldap_permissions%20%281%29.py) | [Copy](../legacy/ldap_permissions/upload_ldap_permissions%20%281%29.py) | Create LDAP permission entries with optional duplicate skipping and scope fallback. |
| [Scheduler downloader](../legacy/download_scheduler.py) | [Copy](../legacy/schedulertask/download_scheduler.py) | Authenticate, export scheduled tasks, and attempt logout. |
| [Scheduler uploader](../legacy/upload_scheduler.py) | [Copy](../legacy/schedulertask/upload_scheduler.py) | List existing tasks, strip selected server fields, create tasks, and attempt logout. |
| [Document restore utility](../legacy/AMS-alerts/restore_cfg.py) | None | Restore search-hit documents by index and document ID to a local document service. |
| [Installation helper](../legacy/2install.sh) | None | Load/create Docker container; optionally write a monthly cron entry. |
| [Uninstallation helper](../legacy/2uninstall.sh) | None | Stop/remove container, remove image, and remove cron entry. |
| [Container launcher](../legacy/run-cc-objects.sh) | None | Start container, open interactive shell, then stop container. |

## Existing source-observed workflows

### Controller objects and device access

- Downloader traverses both trees into `sites` and `devices` collections.
- Site records retain source IDs, parent IDs, and parent names; device records
  retain source IDs, management address fields, type, and parent IDs.
- Device-access extraction removes its nested `ormID` before export.
- Uploader resolves parent sites by name and creates sites before devices.
- Updater submits exported device IDs as `ormID`; destination remapping is absent.
- Object scripts read separate download/upload/update INI profiles or prompt.

### Credential transformation

- Uses separate CLI and SNMP mapping INI inputs to transform Organization JSON.
- Writes a separate updated Organization artifact only when changes are detected.
- CLI, HTTP, and HTTPS mappings use old usernames; SNMPv3 uses authentication
  and privacy secrets.
- No HTTP API is called by this transformation utility.

### LDAP permissions

- Uses source/target fields and TLS configuration from a Vision INI profile.
- Existing-entry detection compares `attributeValue`, not full permission content.
- Imports selected attributes, policy references, and role/group pairs.
- Forces device locking and can retry a rejected mapping with all-scope groups.
  These behaviors are observations, not approved requirements.

### Scheduled tasks

- Endpoint paths, host/port, TLS choice, backup location, and import behavior are
  configuration-driven.
- Duplicate detection compares task names.
- Import removes `ormID`, `taskStatus`, `jobstatus`, and `previousFeedMd5`.
- Configuration is absent, so actual endpoint paths and task types remain unknown.

## Migration domains and scope

| Domain | Proposed scope | Boundary requiring review |
| --- | --- | --- |
| Physical/Organization trees | Export, normalized hierarchy, explicit parent mappings | Tree-specific identity and duplicate-name handling. |
| Sites and devices | Create and explicitly planned updates | Destination ID resolution; behavior of the same device in both trees. |
| Device access | Preserve supported settings and apply explicit mappings | Secret portability, encryption/masking, unsupported fields. |
| Credential transformation | Offline, validated, explicit replacements | Approved secret provider and export handling policy. |
| LDAP permission mappings | Preserve authorization semantics | Destination roles/groups/policies must resolve; never broaden scope silently. |
| Scheduled tasks | Export and approved task-type import | Paths, schema, dependencies, activation, timezone, and supported types. |
| Document restoration | Inventory only; excluded from initial master application | Separate approval and service/ownership clarification required. |
| Docker/cron helpers | Inventory only; excluded from initial migration modules | Packaging and scheduling are separate future decisions. |

## Limitations and migration risks

- Object scripts disable TLS verification and warnings; other API scripts take a
  configurable TLS flag. No bounded request timeouts are specified.
- Session lifecycle is inconsistent. Object login helpers leave the context
  manager before using/returning the session. Scheduler logout failures are
  swallowed. LDAP scripts have no explicit logout.
- Credential transformation prints secrets; scheduler login prints a session
  identifier. Raw API responses and exports may contain sensitive data.
- Missing parent lookup can fall back to the root, changing hierarchy silently.
  Names alone are insufficient to resolve repeated site names safely.
- Device update reuses source IDs; this is unsafe for a different destination.
- LDAP import can broaden scopes and forces `requireDeviceLock=True`.
- HTTP 200/201 checks do not prove completed configuration. Object writes advertise
  asynchronous support without completion polling.
- No general preflight, schema/version validation, reconciliation, rollback,
  configuration comparison, or consistent failure exit contract is implemented.
- Duplicate skipping does not establish equivalence; unexpected scheduler list
  shapes can be treated as an empty destination.
- Missing configuration and representative sanitized data prevent compatibility
  conclusions. Product/version support and cross-product field mappings are unknown.

## Current authorization and non-goals

CCV-001 authorizes only the six documentation files linked below. Legacy sources
remain read-only. No application modules, dependency installation, Git operations,
external configuration changes, live API calls, or script execution are authorized.

Not included: full product backup/restore, arbitrary undocumented APIs, automatic
rollback, unattended production writes, GUI development, or integration of the
document-store and deployment utilities without a separate scope decision.

## Documentation and next gate

- [Architecture](ARCHITECTURE.md): proposed component and safety boundaries.
- [API matrix](API_MATRIX.md): source evidence and verification status.
- [Roadmap](ROADMAP.md): proposed CCV-001 through CCV-008 milestones.
- [Progress](PROGRESS.md): authoritative implementation/verification checkpoint.
- [Decisions](DECISIONS.md): rationale, approval status, and consequences.

Next gate: architecture and scope review. CCV-002 must not start without explicit
authorization after that review.

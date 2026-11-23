# CC-Vision Config Import: simplified MVP

This iteration consolidates the existing code behind [master.py](master.py).
It is **offline only**: no controller authentication, API requests, imports,
updates, credential resolution, or automatic migration. No legacy script is
imported or executed. CCV-010-C and the existing package CLI are unchanged.

## Usage

Use Python 3.12 or newer (the existing contracts use Python 3.12 type aliases).
The master application's offline path uses the standard library; no installation
or third-party packages are required.

Run from this repository in PowerShell:

```powershell
python master.py --help
python master.py --operation operations
python master.py --operation profiles --source-profile examples\offline-controller\source-profile.json --destination-profile examples\offline-controller\destination-profile.json
python master.py --operation export --request examples\offline-controller\request.json --output source-export.json
python master.py --operation compare --request examples\offline-controller\request.json
python master.py --operation plan --request examples\offline-controller\request.json
python master.py --operation import-preview --request examples\offline-controller\request.json
```

`export` adapts a **supplied local source inventory** into an artifact. It does
not download controller data. Output must be a new file; existing files are never
overwritten. Artifacts contain configuration and must be stored appropriately.
Inline credentials are rejected; use existing `secret_ref` contracts or null
credential values. Incomplete or invalid source inventories fail explicitly
without producing an export. The underlying export adapters remain unchanged
and still support retaining incomplete artifacts through their existing API.

`compare`, `plan`, and `import-preview` all reuse the same existing offline
comparison/planning pipeline. They report CREATE, SKIP, CONFLICT, BLOCKED, issue
codes, and prerequisites without printing configuration or credentials.
`import-preview` is **not** a dry-run implementation of the legacy upload scripts:
it does not simulate their HTTP requests, fallback behavior, or write results.

The supplied synthetic example intentionally exits **1**:
CREATE=3, SKIP=3, CONFLICT=1, BLOCKED=1 (eight objects evaluated).
Exit 0 means the offline operation succeeded, never permission to execute.
Other exits retain the existing conventions: 2 usage error, 3 file/JSON I/O
error, 4 invalid/unsupported contract, 5 plan integrity error, 6 internal planner
error. Results are JSON on stdout; argument errors use stderr.

### Profiles and input selection

Source products: `--source-product vision` or `cyber-controller` (default).
Destination: `--destination-product cyber-controller` only.
For Vision profile inspection, select `--source-product vision` and supply a
Vision source profile. Product selectors must agree with profiles.

Profiles use the existing JSON contract:

```json
{
  "role": "source",
  "name": "source-controller",
  "product": "vision",
  "version": "5.4.9",
  "base_url": "https://source.example.invalid",
  "secret_ref": "controller-source"
}
```

Destination profiles use `role: destination` and `product: cyber-controller`.
Do not put usernames, passwords, cookies, or tokens in profiles. Profile
inspection validates syntax only; it never resolves secrets or tests connectivity.
TLS certificate verification remains mandatory for any separately authorized
future connection; this CLI has no TLS-disable option.

For export and planning, reuse [request.json](examples/offline-controller/request.json).
It binds source/destination profiles and inventories, controller IDs, explicit
mappings, device detail/access associations, policy, completeness declarations,
and acknowledgements. Manifest paths are relative to its directory; explicit
CLI profile paths are relative to the working directory. Optional
`--source-profile` / `--destination-profile` arguments must equal the corresponding
manifest profiles: they cannot silently redirect the workflow.

Accepted supplied inventory formats are recursive `tree`, context-qualified
legacy `flat` (with an explicit source root), and normalized `artifact`.
Export reads the source side, including declared reconciliation, but requires
the existing manifest and both profiles. It does not evaluate the destination
inventory or planning declarations. The current controller adapters/planner
accept only synthetic Cyber Controller version `0.0-test`; never relabel a real
controller or real export as this test version.

### Unavailable operations

```powershell
python master.py --operation authenticate
python master.py --operation import
python master.py --operation plan --module ldap-permissions --request examples\offline-controller\request.json
python master.py --operation plan --module scheduler --request examples\offline-controller\request.json
```

All return explicit unavailable results. There is no `--execute`, approval flag,
or route from preview to a configuration write. Explicit per-action approval and
separate, narrowly scoped controller-execution authorization are still required
before future changes; no approval/execution system was added in this iteration.

| Workflow | Current support |
|---|---|
| CC-to-CC controller objects | Synthetic local export, comparison and planning; live reads/writes unavailable |
| Vision-to-CC controller objects | Product/profile selection; migration unavailable because source export schemas and mappings are unestablished |
| LDAP, either direction to CC | Same operation selector; unavailable because CC endpoints/contracts and reference mappings are unresolved |
| Scheduler, either direction to CC | Same operation selector; unavailable because configured legacy paths and CC task contracts are unresolved |

The existing [API matrix](docs/API_MATRIX.md) remains the evidence source.
No endpoints, product equivalence, or compatibility claims were invented.

## Simple architecture and reuse inventory

```text
master.py -> src/cc_vision_import/master_cli.py
               profiles + strict local JSON input
               supplied export adapters + device reconciliation
               controller comparison + existing offline planning reports
```

The new CLI composes existing functions rather than introducing another
authentication, transport, object model, or planner.

| Existing reference | Reusable functionality / current shared component |
|---|---|
| [CC download](legacy/app/download_cybercontroller_objects.py) | `load_config`, `login_cyber_controller`, `extract_sites_and_devices`, `extract_device_access_data`, parent lookups, `write_json_to_file`. Authentication intent and Physical/Organization tree/detail reads are preserved in the existing [authentication](src/cc_vision_import/authentication.py), [sessions](src/cc_vision_import/sessions.py), [product clients](src/cc_vision_import/product_clients.py), [export adapters](src/cc_vision_import/controller_exports.py), and [reconciliation](src/cc_vision_import/controller_reconciliation.py). |
| [CC upload](legacy/app/upload_cybercontroller_objects.py) | Duplicate config/login/JSON/parent lookup functions; `upload_configuration` supplies observed site/device POST intent. Not invoked: root fallback and name-only parent lookup cannot safely implement approved imports. |
| [CC update](legacy/app/update_cybercontroller_objects.py) | Duplicate login/config/lookup functions and device PUT intent. Not invoked: source IDs cannot be reused as destination identities. Existing [mapping](src/cc_vision_import/controller_mapping.py) and [comparison](src/cc_vision_import/controller_comparison.py) handle explicit offline identity planning. |
| [Credential JSON updater](legacy/app/update_json_credentials.py) | `load_json_config`, `load_credentials`, `update_cli_credentials`, `update_snmp_credentials`. Transform intent identified, but not wired: legacy output exposes secrets and mutates nested access data. Existing artifact secret-reference validation is reused instead. |
| [LDAP download](legacy/download_ldap_permissions%20(1).py) / [upload](legacy/upload_ldap_permissions%20(1).py) | Top-level Vision login, GET/export, and POST/import loops. Shared Vision authentication already exists. Do not reuse forced locking, all-scope fallback, or automatic write retry; CC permission contracts are absent. |
| [Scheduler download](legacy/download_scheduler.py) / [upload](legacy/upload_scheduler.py) | Duplicate `vision_login`, `vision_logout`; export loop, `get_existing_tasks`, `sanitize_task`, import counters. Paths come from missing INI bindings; removing fields and name-only skipping are not portable task contracts. Unavailable. |
| [Document restore](legacy/AMS-alerts/restore_cfg.py) and shell helpers | Local document-store restoration, Docker/container deployment, cron setup. Not controller migration; excluded. |

Read-only SHA-256 comparison confirmed **nine duplicate file pairs**:
the four Python object scripts plus `run.sh` under
[legacy/app](legacy/app) and [legacy/cc-objects/app](legacy/cc-objects/app);
the LDAP download/upload pair duplicated under [ldap_permissions](legacy/ldap_permissions);
and the Scheduler download/upload pair duplicated under [schedulertask](legacy/schedulertask).
No copies were changed, deleted, or executed.

Legacy Python dependencies are `requests` and `urllib3`, plus standard-library
JSON/configparser/getpass/logging utilities. Shell helpers depend on Docker and
Linux utilities/cron, not on the master offline application. No dependency
manifest existed at inspection; none was added and no packages were installed.

Additional shared reuse:
[transport](src/cc_vision_import/transport.py) provides the existing HTTP request
interface; [artifacts](src/cc_vision_import/artifacts.py) preserves exported JSON
and validates credential handling; [workflow](src/cc_vision_import/controller_workflow.py)
provides comparison, planning and redacted result/error reports. The master never
constructs sessions, a backend, or production clients. It adds only local
new-file export output and CLI dispatch; no credential or write retries.

## Implementation report

Implemented: root entry point, unified offline selectors, shared profile
validation, source artifact export, comparison/planning/import preview, redacted
results, explicit unavailable states, and this inventory/usage guide.

Verification: 35 existing-runner guarded offline workflow tests passed, including
five focused master CLI regressions; zero guarded network attempts. Syntax checks
passed for the entry point, CLI and affected tests. No legacy execution, live
tests, Git operations, new testing framework, or additional milestones.

Remaining: real-controller reads/authentication, approved import execution,
Vision controller adapters/mappings, CC LDAP and Scheduler contracts, and
real-version qualification. All remain unavailable; resolving or enabling them
requires a separate decision, not automatic continuation of this MVP.

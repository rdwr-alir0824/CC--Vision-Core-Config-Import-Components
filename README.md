# CC-Vision Master

## Current direction: approved legacy-first redesign (2026-11-27)

The active objective is a simple, generic Vision-to-Cyber Controller application
based primarily on the original working [legacy scripts](legacy/). This is an
independent functional redesign, not continuation or repair of the experimental
migration engine described in the historical usage below.

**Phase 1A foundation is owner-approved and offline/mocked tested.** It adds:

- [client.py](src/cc_vision_import/client.py): session ownership, login,
  GET/POST/PUT, strict JSON responses, bounded timeouts and sanitized errors.
- [config.py](src/cc_vision_import/config.py): runtime controller/product,
  username/hidden password input, TLS selection and timeout settings.
- [files.py](src/cc_vision_import/files.py): JSON load/save without envelopes,
  journals or databases; portable access values are preserved, not redacted.

**Phase 1B implements generic Site/Device export only** in
[objects.py](src/cc_vision_import/objects.py), using the original
[object downloader](legacy/app/download_cybercontroller_objects.py) as the primary
reference. There is no import, new master entry point, credential editor, LDAP
or Scheduler implementation in Phase 1B. **Phase 1C adds independent Site/Device
import** in the same module; no master entry point, editor, LDAP or Scheduler.
**Phase 1D adds a thin master menu** in [ccv.py](src/cc_vision_import/ccv.py).
Existing experimental commands,
deployment files and historical qualification data remain unchanged; they are
not dependencies of the redesign. See the current sections of
[architecture](docs/ARCHITECTURE.md), [roadmap](docs/ROADMAP.md) and
[progress](docs/PROGRESS.md) for the next approval gate.

The client defaults to verified HTTPS and disabled live dispatch. Every new
unverified client requires explicit `tls_exception_authorized=True`, warns that
controller identity is unverified, and binds consent to that client's origin
and lifetime. No saved authorization file is required by the new foundation.
The caller supplies finite runtime method/path-segment tuples as `operations`;
only login is automatically included. The export module adds discovered GET
targets through `authorize_gets`, which cannot authorize POST/PUT or another
origin. This is not a capability registry. `allow_live=True` is an explicit
dispatch switch, not permission to contact a controller: no live access is
authorized for Phase 1A, Phase 1B, Phase 1C or Phase 1D.

Remote logout is not implemented: legacy Scheduler logout is configurable and
its concrete binding is unavailable in the present reference files. Local
`close()` always discards client authentication and backend cookies. Controller
login requires HTTP 200 and JSON `status: ok`, rather than trusting HTTP 200 alone.
An optional returned `jsessionid` is validated and used without printing it.

JSON exports may contain device secrets. Atomic saves create a private temporary
file beside the destination, close it after writing, and replace the destination
only on success. Failed writes/replacements preserve previous output and remove
the temporary file; cleanup errors are explicit. New/replaced POSIX files use
mode 0600. Windows directory ACLs remain the operator's responsibility.
Controller credentials are not automatically written to JSON.
Timeouts/deadlines are bounded, but hard DNS cancellation is not guaranteed.

Offline validation (set `PYTHONPATH` to `src` and `tests`):

```text
python -S -B -m unittest test_legacy_cli test_legacy_object_imports test_legacy_object_exports test_legacy_foundation
python -S -B -m unittest discover -s tests
```

Actual Phase 1B results: final focused run **53 passed** (28 export + 25 foundation).
Full regression run **842 tests, 840 passed / 2 skipped**; it started before the
final two cleanup-reporting tests, which passed in the final focused run.
Final closure validation, including atomic saves: **57 focused tests passed;
848 complete regression tests, 846 passed / two skipped**. Skips require
unavailable Docker/Compose and POSIX TTY/readline respectively.
All validation was offline/mocked. See [test evidence](docs/PROGRESS.md#ccv-lf-1b---generic-sitedevice-export-only).

### Phase 1B export interface and portable JSON

`export_objects(config, outputs, ...)` accepts a `ControllerConfig` and an output
mapping: `{"Physical": path}`, `{"Organization": path}`, or both with distinct
paths. Filenames are runtime inputs; no output folder is created automatically.
One client/session authenticates once, traverses each selected source hierarchy,
resolves parent names locally or by Site ID, then retrieves Device access by IP.
Only login POST and source GETs occur; there are no destination calls or writes.

Each file has exactly these top-level keys. All values below are synthetic;
actual names, IDs, model types, addresses and credential values come from input
or API responses. Extra supported deviceAccess members are preserved.

**This is the portable input contract consumed by the independent importer.**
The root has nonempty string id/name. Both arrays are required. Each Site has
nonempty string name/id/parent_site_name/parentOrmID; each Device has nonempty
string name/type/managementIp/id/parentOrmID plus a deviceAccess object.
Parent IDs refer to source_root.id or another Site.id; parent_site_name must
agree with that source relationship. IDs are unique across root/Sites/Devices.
Site names can repeat under different parents, but not ambiguously under the
same parent. Device names must be unambiguous within their source parent, and
management IPs must be unique within the file (the source lookup is by IP).
No protocol-specific credential keys are mandatory: supported
deviceAccess fields are opaque JSON and retained. The top-level access ormID
is excluded from destination payloads. No schema, journal or migration envelope.
Supported older files without source_root require an explicit runtime source
root `{id, name}`; it is never inferred from an unresolved reference.

```json
{
  "source_root": {"id": "source-root-a7", "name": "Example Source Root"},
  "sites": [
    {
      "name": "Example Branch",
      "id": "source-site-b8",
      "parent_site_name": "Example Source Root",
      "parentOrmID": "source-root-a7"
    }
  ],
  "devices": [
    {
      "name": "Example Root Device",
      "type": "example-model-from-api",
      "managementIp": "192.0.2.10",
      "id": "source-device-r0",
      "parentOrmID": "source-root-a7",
      "deviceAccess": {
        "cliUsername": "synthetic-cli",
        "cliPassword": "synthetic-cli-secret",
        "supportedOpaqueSetting": {"values": [false, null, "synthetic-value"]}
      }
    },
    {
      "name": "Example Device",
      "type": "example-model-from-api",
      "managementIp": "192.0.2.11",
      "id": "source-device-c9",
      "parentOrmID": "source-site-b8",
      "deviceAccess": {
        "cliUsername": "synthetic-cli",
        "cliPassword": "synthetic-cli-secret",
        "httpUsername": "synthetic-http",
        "httpPassword": "synthetic-http-secret",
        "httpsUsername": "synthetic-https",
        "httpsPassword": "synthetic-https-secret",
        "snmpV3Username": "synthetic-snmp",
        "snmpV3AuthenticationPassword": "synthetic-auth-secret",
        "snmpV3PrivacyPassword": "synthetic-privacy-secret"
      }
    }
  ]
}
```

Root-attached Devices use the source root's ID as `parentOrmID`. Site traversal
is parent-first and depth-first, preserving the legacy fields. Missing names
can use the source-observed Site-by-ID lookup; missing IDs or duplicate hierarchy
identities fail explicitly. The server-owned deviceAccess `ormID` alone is
removed from a deep copy; original responses and other access values are retained.
Exports warn that credentials may be present. This preservation does not certify
that encrypted or masked values are reusable on a different controller.

The returned mapping contains a separate `ExportResult` per selected tree:
`status`, `path`, `site_count`, `device_count`, `error_code`, `failed_step` and
`cleanup_failed`. SUCCESS requires complete collection, file writing and local
session cleanup. A failed collection writes no new file; an older file at that
path remains untouched. Atomic file-write failures preserve the previous output
and are always FAILED. A cleanup failure retains the primary tree error or marks a
written export FAILED with its known counts/path. Successful independent trees
are retained when another tree fails; authentication/session loss is not retried.
No combined success is inferred from one successful tree.

### Phase 1C independent import

`import_objects(destination_config, input_path, tree, ...)` imports one portable
file into the explicitly selected Physical or Organization destination tree.
It does not call export or connect to a source. Optional `source_root={id, name}`
identifies a supported older file's source root; conflicting metadata fails.
TLS consent/injected offline connections use the unchanged foundation interface.
Live dispatch remains disabled by default and is not authorized.

Strict JSON loading and complete structural validation occur **before login**:
required fields, unique IDs, unambiguous identities, source parents/name
agreement, access objects and acyclic Site dependencies. Invalid input raises a
sanitized `ImportError` without any POST, including login. Access objects are
opaque JSON; no mandatory protocol credentials or nested IP fields are invented.

One destination session reads the selected hierarchy and explicitly maps the
source root ID to its API-returned native root ID. Parent-first Sites use an
in-memory source-to-destination ID map; Devices follow. Existing Sites match by
name within the mapped parent, never by a global name lookup. Same-name Sites
at other intended root-relative source paths are independent; an unmatched
same-name Site outside those paths is a wrong-placement conflict. Devices match
by IP or name within their parent and skip only when name/type/IP/placement agree.
Ambiguity/conflicts fail; nothing is moved, renamed, updated or deleted.

Only the legacy minimal payloads are sent (all example values synthetic):

```json
{"name": "Example Branch", "parentOrmID": "destination-root-z3"}
```

```json
{
  "name": "Example Device",
  "parentOrmID": "destination-site-y4",
  "type": "example-model-from-api",
  "deviceSetup": {
    "deviceAccess": {"cliUsername": "synthetic-cli", "cliPassword": "synthetic-cli-secret"}
  }
}
```

Source object IDs and the top-level server-owned deviceAccess.ormID are never
included as destination identifiers. Other supported access fields are copied
unchanged. Accepted POST bodies/async acknowledgements are not proof: at most
**three immediate hierarchy GET readbacks per creation** establish identity and
placement before a child can use its new parent. GET failures stop that
confirmation; requests are not retried. Unconfirmed outcomes and POST failures
are FAILED with `destination_outcome_uncertain` reasons and never resubmitted.
A failed parent prevents dependent writes; unrelated branches continue.
A changed destination root stops remaining writes.

`ImportResult.objects` holds object_type, source_id, SUCCESS/SKIPPED/FAILED and a
concise static reason. `counts` aggregates each status separately for Site and
Device. Overall status is FAILED on any object/global failure. Local cleanup
failure makes the overall operation FAILED while retaining confirmed per-object
results/counts; cleanup notes are preserved. Results omit Device access, raw
responses and controller/session credentials.

Final focused validation: **97 passed** (40 import, 28 export, 29 foundation).
Complete final regressions: **888 tests in 848.882s; 886 passed/two skipped**.
Docker/Compose configuration skipped because Docker/Compose is unavailable;
POSIX TTY/readline editing skipped because it requires Linux/macOS. Evidence is in
[PROGRESS](docs/PROGRESS.md#ccv-lf-1c---independent-sitedevice-import).
All tests are offline/mocked, including actual-client memory connections.
Live API/version compatibility and cross-controller secret portability remain
unverified. Three immediate readbacks may not cover slow asynchronous operations;
FAILED/uncertain requires operator review, not automatic rerunning. There is no
rollback or reconciliation of uncertain writes, nor a concurrency guarantee
against other controller writers. The Phase 1D master menu below is implemented;
live qualification requires separate Phase 1E approval.

### Phase 1D master CLI

From the repository root in the VS Code PowerShell terminal:

```powershell
Set-Location 'C:\DATA\Scripts\CC -Vision Core Config Import Components'
$env:PYTHONPATH = "$PWD\src"
python -m cc_vision_import.ccv
```

This exact src-layout invocation and `python -m cc_vision_import.ccv --help`
were executed successfully with safe menu exit. No package installation,
launcher or deployment change is required. Normal operation needs an interactive
terminal for hidden password input; the CLI refuses getpass's echoing fallback.

The menu displays:

```text
CC-Vision Core Config Import Components

1. Export Sites and Devices
2. Import Sites and Devices
3. Modify exported credentials (Not implemented)
4. Export LDAP configuration (Not implemented)
5. Import LDAP configuration (Not implemented)
6. Export Scheduler configuration (Not implemented)
7. Import Scheduler configuration (Not implemented)
8. Exit
```

Option 8 exits the menu with status 0 without starting an operation. It was
explicitly included as "8. Exit" in the Phase 1D authorization; it is not an
additional migration capability.

Equivalent Linux invocation from an operator-selected checkout directory:

```bash
cd -- "$APP_DIR"
export PYTHONPATH="$PWD/src"
python3 -m cc_vision_import.ccv
python3 -m cc_vision_import.ccv --help
```

Linux instructions are untested, not Linux qualification evidence. The existing
Windows runtime is CPython 3.13.14; imports/menu/help were reconfirmed with
`python -S -B`, without site-packages. The new application requires no third-party
Python packages. Workspace requests/urllib3 imports belong to legacy references,
not this runtime. Use an existing CPython 3.13 runtime for initial lab preparation;
other versions are not newly certified by this closure.

**Live API dispatch is disabled by default.** The menu can be launched safely;
an operation without live dispatch authorization fails explicitly, not with
fake success. Only after separate owner approval for the actual systems:
`python -m cc_vision_import.ccv --allow-live`. This switch enables the existing
backend dispatch mechanism; it does not grant permission to contact a controller.
No live API calls were made during Phase 1D.

Export collects source product (Vision/Cyber Controller), controller address,
username, hidden password, TLS selection, tree(s), and separate output filenames.
Defaults are physical.json/organization.json in the current directory; parent
directories must already exist. Files may contain sensitive Device credentials.
Protect Windows directory ACLs and keep exports out of Git. Each existing output
requires explicit replacement confirmation; blank/invalid/no cancels before
dispatch. Both trees share the original single export session.

Import collects the input filename, destination Cyber Controller settings/TLS
and one explicitly selected destination tree. It delegates strict validation to
objects.py before login; older files missing source_root request its explicit
ID/name. The first summary shows destination, tree, filename, source root and
counts, warns that objects are created, conflicts are not moved/updated/deleted,
and automatic rollback is unavailable. Explicit confirmation allows login/
discovery only. A second summary from the actual consumed input and discovered
destination root requires another explicit confirmation **before object writes**.
Blank, invalid or declined replies cancel. No Device access values are displayed.

TLS verification defaults to enabled. Selecting unverified TLS requires a
second explicit, origin/session-scoped authorization and warns that controller
identity is NOT VERIFIED. Consent is never reused for the next operation.
Ctrl+C/EOF exits gracefully; sessions close on cancellation/failure, including
login interruption. Interrupted writes may have an uncertain destination
outcome and require manual review before any repeat attempt.

Export reports independent tree status, paths and available exported counts.
Import reports SUCCESS/SKIPPED/FAILED counts and concise per-object failures,
including uncertain creation. Options 3-7 return to the menu without network
requests or file modifications. No retries, rollback, persistent state or
sensitive-payload logging is added.

Condensed synthetic examples of the tested interaction (passwords hidden):

```text
Export: option 1 -> Vision -> source.example.invalid -> synthetic-operator
        -> [hidden password] -> verified TLS -> Both
        -> physical.json and organization.json -> confirm replacement if present
Physical: SUCCESS; output=...; Sites=1, Devices=1
Organization: SUCCESS; output=...; Sites=1, Devices=1

Import: option 2 -> portable-menu.json -> destination.example.invalid
        -> synthetic-operator -> [hidden password] -> verified TLS -> Physical
Source root: 'Mist Canopy'; ID='portable-root-81'; Sites=1, Devices=1
Proceed to destination login/discovery? [y/N]: yes
Destination root: 'Discovered Canopy'; ID='discovered-root-901'
Create objects under this destination root? [y/N]: yes
Sites: SUCCESS=0, SKIPPED=1, FAILED=0
Devices: SUCCESS=1, SKIPPED=0, FAILED=0
```

These examples are offline/mocked evidence, not live compatibility claims.
Final focused evidence: **134 tests passed** (37 CLI + 97 existing legacy-first).
Final complete regressions: **925 tests in 716.288s; 923 passed/two skipped**.
Skips: Docker/Compose unavailable; POSIX TTY/readline requires Linux/macOS.
Actual commands and zero-network guard evidence are recorded in
[PROGRESS](docs/PROGRESS.md#ccv-lf-1d---thin-master-cli).
Readback remains three immediate attempts; no automatic rollback/concurrent-
writer guarantee, live compatibility or credential-portability certification.
The proposed, separately approved [Phase 1E procedure](docs/ROADMAP.md#proposed-phase-1e---bounded-live-qualification)
starts with authorized lab targets and protected exports, verifies roots and
basic identities manually, and stops on uncertain outcomes. No deployment,
credential transformation, Device update, LDAP or Scheduler implementation.

**The remaining sections document the existing experimental application, not
the approved legacy-first design or new functionality.**

One on-demand application for supported, read-only APSolute Vision configuration
collection, offline export/comparison/planning, separately selected experimental
Site migration, and read-only Organization Device migration qualification.
It reuses shared authentication, sessions, HTTP transport and JSON validation.
Original legacy scripts are references only: none are imported or executed.
The detailed capability/legacy mapping is maintained in the
[internal API matrix](docs/API_MATRIX.md).

## Operator Quick Start

### Backup-driven migration

Use the existing image, launcher and incoming/reports mounts. The selected
native Vision backup is inspected by schema rather than customer filenames or
fixed inventory counts. No new image service or dependency is required.

```sh
./ccv.sh --migration-dry-run
./ccv.sh --migration-execute --backup /incoming/CUSTOMER-BACKUP
./ccv.sh --migration-resume --backup /incoming/CUSTOMER-BACKUP
./ccv.sh --migration-reconcile --backup /incoming/CUSTOMER-BACKUP
./ccv.sh --migration-status --backup /incoming/CUSTOMER-BACKUP
```

Choose menu **2**. Without `--backup`, choose an incoming folder once. Enter the
authorized destination and credentials. Different source/destination root names
require interactive review; no unresolved object is silently assigned to Default.
Execution/resume separately requires fresh preflight and batch authorization.
Captured TLS discovery remains read-only; root review and batch input run with
Docker stdin/TTY in the foreground.

Only experimental Organization Site creation is currently write-capable.
Devices receive inventory/association and qualified-existing-object read checks;
Device creation, controller attributes, access/credential restoration, Physical
hierarchy, LDAP and Scheduler writes remain **BLOCKED** by unqualified contracts.
Populated unsupported modules, unknown schemas and unprojected settings remain
explicitly outstanding. `COMPLETED` means every **selected-backup in-scope**
record is verified (or the validated scope is genuinely empty), not that source
enumeration or full controller/version compatibility has been certified.
`PARTIAL` and `BLOCKED` must not be presented as full migration success.

Native root identity, original snapshot/comparison and the entire backup's
content binding are retained in protected migration state. Existing Site
journals/one-POST guards remain authoritative. Resume never clears an uncertain
attempt; reconcile verifies remote state without creating anything. Status does
not change journals. Historical path-based single/batch Site commands remain
available: use their **original** source/comparison/snapshot to reconcile the two
historical lab attempts, not newly generated evidence or manually edited JSON.

Read-only historical recovery assessment (choose menu **2**):

```sh
./ccv.sh --migration-recovery-assess --backup /incoming/CUSTOMER-BACKUP
# For a historical Site plan predating the backup-driven state:
./ccv.sh --migration-recovery-assess --backup /incoming/CUSTOMER-BACKUP \
  --input /incoming/CUSTOMER-BACKUP/ORIGINAL-ORGANIZATION.json \
  --comparison /reports/ORIGINAL-COMPARISON.json \
  --destination-snapshot /reports/ORIGINAL-SNAPSHOT.json
```

Assessment validates the original protected evidence, reads attempted Sites
and saves a sanitized report without changing journals/guards. Legacy Site
journals bind Organization source/comparison/snapshot, not the entire backup;
assessment explicitly reports that limitation. Missing original inputs are not
replaced with a new plan. Empty enumeration, GUI deletion and HTTP lookup misses
do **not** prove absence. Complete Organization enumeration, definitive by-ID
absence and settlement of historical POST operations remain unqualified.
`--migration-lab-reset` therefore stays **BLOCKED**: no reset, guard clearing,
POST retry or controller deletion. Assessment exits nonzero while reset is blocked.

Inspection limits are configurable with `--backup-max-files`,
`--backup-max-objects`, `--backup-max-depth`, `--backup-max-file-bytes` and
`--backup-max-total-bytes`. Defaults: 4,096 files, 10,000 domain records,
48 hierarchy levels, 16 MiB/file and 128 MiB total. Existing execution ceilings
remain 10,000 tree nodes/64 levels; Device detail readers retain 4 MiB/file and
64 MiB aggregate. Limits fail explicitly, never truncate.

Exact current lab read-only validation:

```sh
cd /opt/radware/storage/scripts/CC--Vision-Core-Config-Import-Components
./ccv.sh --migration-dry-run \
  --backup /incoming/vision-backup-20261125T122823Z-3ad1c37f503d \
  --target-version 10.15.0-2
```

Choose **2**, then the authorized lab destination `155.1.1.7`. This command was
**not live-tested or deployed** during development. CC 10.10.x remains the
primary, unverified target; CC 10.15.0-2 observations are not universal contracts.
For an entirely offline inventory using the same application:

```sh
python master.py --operation backup-inventory \
  --backup /path/to/customer-backup --output /path/to/inventory-report.json
```

The older menu **3** full-six-module offline assessment retains its original
format checks; use the backup-driven commands for partial/targeted backups or
noncanonical filenames.

On an **authorized appliance Docker host or approved adjacent Docker host**:

```sh
cd /opt/radware/storage/scripts/CC--Vision-Core-Config-Import-Components
./ccv.sh
```

Choose **1** for the six-module Source Vision backup, **2** for read-only
destination Site discovery, **3** for transferred-backup validation, or **4** to
exit. Live operations request the controller IP/hostname, username and hidden
password. Offline validation lists transferred folders and requests no controller
credentials. No manual credential JSON, environment setup or Compose service
names are needed. Review the concise result and complete backup/report path.

HTTPS certificate verification is always attempted first. Trusted certificates
need no extra prompt. If verification fails before authentication, the launcher
asks once:

> Untrusted/self-signed certificate. Continue without certificate verification for this session only? [y/N]

Blank input or NO cancels safely. YES permits one same-origin retry for this
execution only; controller identity is not authenticated and credentials could
be intercepted. Every new execution starts verified again. No `.env` setting,
manual JSON policy or administrator TLS provisioning is needed for this choice.
An optional administrator production lock can prohibit it.

**Source Backup -> Transfer Complete Folder -> Destination Validation ->
Destination Discovery -> Separately Authorized Site Migration.** Device writes
remain blocked pending API qualification. A blocked assessment never authorizes
writes; single-Site and Site batch execution require separate explicit operations.
Successful collection is not a complete/restorable configuration backup.

The launcher uses **Bash + Docker only**, including offline helpers from the
same image; no host Python dependency. Application/helper containers remain
UID/GID 10001. For live operations, approved sudo may request the engineer's
host password **before** controller credentials, solely to provision temporary
file ownership. Passwordless sudo is not assumed. Credential files are mode
0600/UID:GID 10001:10001; only their uniquely created directory is used.
Normal exit, Ctrl-C and TERM remove temporary files and this run's labeled
containers, without deleting administrator-managed secrets or reports.
SIGKILL, host failure or an unavailable Docker daemon can prevent complete
cleanup; ask the administrator to inspect any reported leftover run.

## Supported functionality and requirements

| Backup component | Current support |
| --- | --- |
| Controller Objects | Vision 5.4.9 managed-device inventory and supported device details |
| Device Access | Documented nested device-access data, with credentials redacted |
| LDAP Permissions | Legacy-observed read-only list export; validated/redacted record subset, completeness unverified |
| Physical Tree | Native tree JSON; schema and enumeration completeness unverified |
| Organization Tree | Native tree JSON; source Site readiness available, destination mappings unqualified |
| Scheduler | Read-only task-list subset; credentials redacted, completeness unverified |

Full Supported Backup selects all six modules. It does not mean every possible
configuration item or a restorable credential backup. Imports, updates and
deletes remain unavailable; the only configuration-write exception is the explicit
experimental single-Site operation below. Other Vision versions and Cyber Controller live
backup are not qualified. Existing offline commands remain available.

- **Deployment hosts:** approved Linux/Bash 4+ environment, Git, Docker and a
  current Docker Compose v2 plugin. No host Python replacement is required.
- **Container engine:** official Python **3.13-slim**, `/app`,
  `PYTHONPATH=/app/src`, UID/GID **10001:10001**.

Docker access is privileged; use the host's approved access policy.
Do not start collection until the owner authorizes the controller and account.

## Standard Deployment — Source and Destination

Use this **same deployment procedure on both hosts**. Only execution selects a
role. Deployment inside a Vision or Cyber Controller appliance requires explicit
authorization; an adjacent approved Docker host uses the same procedure.
Use an approved account with application-directory write access and Docker access.
Run subsequent commands from the standard application directory; set the
transfer variables again when switching hosts or opening a new shell.

| Shared item | Standard |
| --- | --- |
| Repository | https://github.com/rdwr-alir0824/CC--Vision-Core-Config-Import-Components |
| Application directory | `/opt/radware/storage/scripts/CC--Vision-Core-Config-Import-Components` |
| Build/runtime | Same reviewed Git revision, [Dockerfile](Dockerfile) and [compose.yaml](compose.yaml) on both hosts |
| Shared image | `cc-vision-master:0.3` (same `CC_VISION_IMAGE` override on both hosts if approved) |

### 1. Install (identical on both hosts)

**First installation only.** If the application directory already exists, use
Update below; do not clone it again. Have the administrator provision its parent
directory for the approved deployment account.

```sh
APP=/opt/radware/storage/scripts/CC--Vision-Core-Config-Import-Components
test ! -e "$APP" && git clone \
  https://github.com/rdwr-alir0824/CC--Vision-Core-Config-Import-Components.git "$APP"
```

After installation, or after the Update step, run this shared deployment block:

```sh
cd /opt/radware/storage/scripts/CC--Vision-Core-Config-Import-Components
sudo install -d -m 0700 -o 10001 -g 10001 \
  ../ccv-runtime/source-backups ../ccv-runtime/source-secrets \
  ../ccv-runtime/source-config ../ccv-runtime/destination-incoming \
  ../ccv-runtime/destination-reports ../ccv-runtime/destination-secrets
chmod u+x ccv.sh
docker compose --profile source --profile destination config --quiet
docker compose --profile source --profile destination build
```

Stop on any error. Builds need the base image locally or approved registry access,
not controller access. Rebuilding is required even when retaining the same tag.
No operation is started by deployment.

The default mounts match the standard proposal; **no configuration correction is
needed**. Relative host paths resolve beside the Compose file:

| Host path below `/opt/radware/storage/scripts/` | Container path | Access |
| --- | --- | --- |
| `ccv-runtime/source-backups/` | `/backups` | Source writes |
| `ccv-runtime/source-secrets/` | `/run/secrets` | Source read-only |
| `ccv-runtime/source-config/` | `/run/config` | Source read-only |
| `ccv-runtime/destination-incoming/` | `/incoming` | Destination read-only |
| `ccv-runtime/destination-reports/` | `/reports` | Destination writes |

Review any private `.env` or shell `CCV_*_DIR` overrides: the standard procedure
assumes these default paths. Keep secrets out of `.env`, Git and the image.
Containers run as `10001:10001`, with a read-only root and no privileged mode,
Docker socket or published ports. Source uses bridge networking; destination has
networking disabled. Missing bind directories fail rather than being auto-created.

### 2. Source backup (source host only)

```sh
./ccv.sh
```

Select **1** and enter the approved controller IP/hostname and credentials.
The launcher executes the existing six read-only modules and exits. It displays
the complete generated folder and module counts/redactions/limitations;
full engine JSON and `summary.json` remain unchanged. Transfer that whole folder
using Step 3; never transfer temporary or administrator credential files.

### 3. Transfer the complete backup folder (mandatory)

**Copying a backup is not importing configuration.** Transfer never triggers a
CC restore, API write or automatic extraction. Hosts need no direct connectivity:
use SFTP, SCP, WinSCP through approved staging, or approved offline media.

1. Find the source run folder from the backup output or:

   ```sh
   sudo find ../ccv-runtime/source-backups -mindepth 1 -maxdepth 1 \
     -type d -name 'vision-backup-*' -printf '%f\n'
   ```

2. Set `BACKUP_FOLDER` to that exact single directory basename, then package the
   **whole folder**, not selected files. Use private staging outside the clone:

   ```sh
   BACKUP_FOLDER=vision-backup-REPLACE-WITH-ACTUAL-RUN
   TRANSFER="$HOME/ccv-transfer"
   umask 077
   mkdir -p "$TRANSFER"
   sudo tar -C ../ccv-runtime/source-backups -czf - -- "$BACKUP_FOLDER" \
     > "$TRANSFER/$BACKUP_FOLDER.tar.gz" &&
   (cd "$TRANSFER" && sha256sum "$BACKUP_FOLDER.tar.gz" \
     > "$BACKUP_FOLDER.tar.gz.sha256")
   ```

3. Transfer the archive and trusted checksum to private staging on the
   destination. Approved secure full-directory transfer is also acceptable;
   verify its source/destination file checksums. Never transfer source credentials.
4. On the destination, set `BACKUP_FOLDER` to the same basename and
   `TRANSFER="$HOME/ccv-transfer"`. Verify before extracting:

   ```sh
   (cd "$TRANSFER" && sha256sum -c "$BACKUP_FOLDER.tar.gz.sha256") &&
   tar -tvzf "$TRANSFER/$BACKUP_FOLDER.tar.gz"
   ```

   Stop on checksum failure. A checksum detects corruption, not authenticity:
   use a trusted source/transfer channel. Extract only trusted archives containing
   that single backup folder; reject absolute paths, `..`, links or unexpected
   entries. Do not overwrite an existing incoming folder.

   ```sh
   INCOMING="../ccv-runtime/destination-incoming/$BACKUP_FOLDER"
   sudo test ! -e "$INCOMING" &&
   sudo tar --no-same-owner --no-same-permissions \
     -xzf "$TRANSFER/$BACKUP_FOLDER.tar.gz" -C ../ccv-runtime/destination-incoming &&
   sudo chown -R 10001:10001 "$INCOMING" &&
   sudo chmod -R u=rwX,go= "$INCOMING" &&
   sudo ls -ld "$INCOMING"/{controller-objects,device-access,ldap-permissions,physical-tree,organization-tree,scheduler,summary.json}
   ```

5. Before preflight, verify all **six module directories and `summary.json`**
   exist, match the source transfer, and are readable by UID 10001. Check source
   summary module statuses/counts/failures; directory presence alone is not
   successful collection or schema completeness. The ownership changes above
   apply only to the newly transferred, reviewed folder, not existing backups.

Standard placement is:
`../ccv-runtime/source-backups/<backup-folder>/` on source and
`../ccv-runtime/destination-incoming/<backup-folder>/` on destination.
Inside the destination container, it is `/incoming/<backup-folder>/`, read-only.

### 4. Destination preflight (destination host only)

```sh
./ccv.sh
```

Select **3**, then a displayed incoming folder number. No controller credentials
or version declaration is requested. The launcher checks six nonempty module
directories, both trees and the successful source collection summary, rejecting
links, unsafe folders and incomplete collection. These are **presence/safety
checks, not a full package/schema or checksum validator**. Transfer-integrity
verification in Step 3 remains mandatory.

The existing offline Organization **Site-readiness** assessment runs with
networking disabled and `/incoming` read-only. It saves a new report under
destination-reports and displays its path/counts. Exit **1** plus “Assessment
completed; migration BLOCKED” is the expected non-executable readiness outcome,
not application failure. Input/runtime errors are reported separately. This
does not validate all six schemas, authenticate to CC or qualify import mappings.

#### Optional: read-only destination Site discovery

Run `./ccv.sh`, select **2**, and enter the approved CC IP/hostname and credentials.
It uses the existing explicitly selected discovery role, never enabling networking
in the offline destination. The summary displays counts/redactions and the
private snapshot path under destination-reports. Snapshot native Site names/IDs
must not be copied into shared logs. Parent semantics and enumeration remain
unqualified; product version stays **unknown/unverified**, including the unresolved
10.10.7/10.10.6 documentation conflict. No imports, writes or speculative version
requests occur. Exit 0 means collected-unqualified, not migration-ready.

#### Optional: read-only Default root ID qualification

After separately authorizing the controller/account and existing restricted
HTTPS egress, rebuild the same shared image from the reviewed checkout:

```sh
cd /opt/radware/storage/scripts/CC--Vision-Core-Config-Import-Components
docker compose --profile destination-discovery config --quiet
docker compose --profile destination-discovery build ccv-destination-discovery
./ccv.sh --qualify-default-root
```

Select **2** in the unchanged menu. Enter only controller, username and hidden
password. This explicit mode replaces the Organization read with exactly GET
`/mgmt/system/config/tree/site/byname/Default`, after existing validated login.
It allows neither other lookups nor configuration writes. Existing session-only
TLS consent and production lock apply unchanged; no automatic downgrade.

Output includes only presence/Python/JSON types, usability and identity-match
results. It never prints or saves native identifier values or response bodies.
The sanitized `root-qualification.json` is written in a new `cc-destination-*`
directory under destination-reports. Exit **0** means exact Default name and a
usable candidate ormID were observed, **not** verified root identity, valid
create parentOrmID or migration readiness. Missing/mismatched name or missing/
unusable ormID yields partial evidence and exit **1**; malformed/ambiguous
response or authentication/transport failure is an explicit error.
Root type/parent semantics, correspondence to earlier snapshots and Site-create
acceptance remain unqualified even if response identity fields compare equal.

Normal `./ccv.sh` still performs the original read-only/offline workflows.
Site creation requires the separate explicit mode below.
Check [API_MATRIX.md](docs/API_MATRIX.md) for field/schema risks.
Offline developer verification (no controller access), from a checkout with
Python and tests, is:

```sh
PYTHONPATH=src:tests python -S -B -m unittest \
  test_destination_discovery test_compose_deployment
```

This developer command does not add a host Python requirement to deployment.
Do not rerun a live lookup if adequate protected evidence already exists.

#### CCV-012: full hierarchical Site migration

The existing choice **2** now supports `--sites-dry-run`, `--sites-execute` and
`--sites-resume`. Single-Site flags and choices 1-4 remain unchanged. This is
Site-only orchestration, not Device, Scheduler, LDAP or Physical-tree migration.
Primary target remains **CC 10.10.x**; the current lab is **CC 10.15.0-2**.
Neither release family has verified create/completion compatibility here.

On the existing authorized Linux destination host, after transferring the
reviewed updated application, rebuild the **same image/service**:

```sh
cd /opt/radware/storage/scripts/CC--Vision-Core-Config-Import-Components
docker compose --profile destination-discovery config --quiet
docker compose --profile destination-discovery build ccv-destination-discovery
```

Keep the original protected backup, snapshot and complete confirmed comparison
unchanged. From that directory, in Bash:

```bash
migration_inputs=(
  --input /incoming/vision-backup-20261125T122823Z-3ad1c37f503d/organization-tree/tree.json
  --comparison /reports/source-destination-site-comparison.json
  --destination-snapshot /reports/cc-destination-20261126T001502Z-c71a84af2691/organization-sites.json
  --target-version 10.15.0-2
)
site_inputs=(
  "${migration_inputs[@]}"
  --operation-delay 1
  --readback-interval 1
  --readback-attempts 3
)
./ccv.sh --sites-dry-run "${site_inputs[@]}"
```

Use the actual original comparison basename if different. Select **2**, enter
the approved lab destination (currently `155.1.1.7`) and session credentials.
This operation authenticates and performs fresh **read-only** Site/tree checks
for the entire hash-bound list. It does not create Sites. Future child-parent
IDs are planned dependencies, never substituted with the root or source IDs.
Existing Sites require exact identity/parent/by-ID/tree agreement. An absence
candidate, including the exact observed 10.15.0-2 M_00734 response, still requires
a fresh collision-free Organization tree. Unknown evidence blocks the batch.

**Only after separate owner authorization for controller writes**, review the
full dry-run, freeze competing writers and use:

```bash
./ccv.sh --sites-execute "${site_inputs[@]}"
```

The launcher first repeats the read-only batch preflight, then starts one fresh
interactive session. After fresh read-only preflight, the engine displays the
destination, Site count and experimental risks, then asks
`Proceed with creating <count> Sites? [Y/n] (default Yes):`.
Y/Yes or Enter approves; N/No cancels. Invalid answers re-prompt with terminal
line editing; noninteractive input, EOF or interruption never approves.
The reviewed list/destination remain bound internally without typing a hash.
Compact progress/counts replace console JSON; complete reports and protected
journals remain in their existing locations. Each create has fresh parent
and collision checks, a durable reservation, one POST maximum and bounded
returned-ID/hierarchy readback before dependent children can run. Unknown
results stop immediately; no POST retries, rollback, root rename or fallback.
Delays are 0-60 seconds; readback rounds 1-10, using existing bounded HTTP timeouts.

Sanitized `ccv-sites-report-<random>.json` files in destination-reports contain
ordered artifact references, dependencies, preview placeholders and cumulative
created/verified/already-existing/blocked/failed/pending counts. On resume,
`verified_this_run` separately identifies fresh reconciliation, not cached
journal evidence. Names, native IDs, credentials and response bodies are absent.
The deterministic `ccv-sites-<list-hash>-<origin-hash>.journal.json` is **protected,
not shareable**: it retains destination-native mappings and incomplete-attempt
evidence. POSIX files are 0600; preserve the private runtime directory and owner.
The per-origin kernel lock prevents overlapping batches and releases on process
exit; per-Site guards are shared with the single-Site engine.

For an interrupted batch, retain the **same inputs, origin and reports directory**:

```bash
./ccv.sh --sites-resume "${site_inputs[@]}"
```

Resume is explicit and requires batch authorization again. Fresh identity,
parent and hierarchy evidence must reconcile previous work before continuation.
A possibly successful POST that still appears absent, or whose identity/parent
is ambiguous, is **not retried**; manual reconciliation is required. Never delete
or edit journals/guards to force continuation. Development tests used a synthetic
30-Site/22-dependency graph with network access denied; Docker builds and the
owner's real protected snapshots/live batch remain unverified in this environment.

##### Read-only reconciliation of an indeterminate Site

Retain the original protected journal, guards, inputs and destination. Do not edit,
delete or regenerate them. Before separately authorized continuation:

```bash
./ccv.sh --sites-reconcile "${migration_inputs[@]}"
```

Select **2** and the same destination. This authenticates and rechecks only the
attempted/verified prefix; it never creates pending Sites or asks for write
approval. A candidate must have exact name/type/unique destination identity,
by-ID agreement and fresh hierarchy membership. A direct root child may have
an explicit null parent only when the hierarchy independently proves placement
under the qualified Default root. Missing parent fields, non-root null parents,
identity changes, duplicates and wrong placement still block.

The original one-POST count and incomplete-operation evidence are retained in a
protected reconciliation history. After a successful report, a **separately
authorized** `./ccv.sh --sites-resume "${site_inputs[@]}"` can continue pending
Sites; it never repeats the reconciled POST. A successful HTTP 200/201 JSON
acknowledgement need not contain the full Site identity: bounded fresh name
lookup (when needed), exact type/name/native-ID checks, by-ID and independent
hierarchy/parent verification can establish completion automatically. Resolved
IDs must not occur in the pre-create identity baseline. Error/contradictory
responses, timeout or exhausted verification still stop the batch without
repeating the POST.

The original `site_identity_missing_or_ambiguous` code comes from parsing an
expected name/nonempty ormID, not from parent validation. A POST response without
identity reproduces it. The original POST body/journal are unavailable locally,
so its exact failing response cannot be asserted. New fixed stages distinguish
create-response parsing from later readback without saving response bodies.

#### CCV-013: Organization Device qualification and combined preview

Reuse `migration_inputs` above; no additional paths, configuration files,
credentials prompts within a run, images or services. The same transferred
backup's sibling `controller-objects/device-by-ip-*.json` and
`device-access/device-by-ip-*.json` records are found and hash-bound automatically.

```bash
./ccv.sh --devices-dry-run "${migration_inputs[@]}"
./ccv.sh --migration-dry-run "${migration_inputs[@]}"
./ccv.sh --migration-status "${migration_inputs[@]}"
```

Choose **2**, destination and session credentials once per invocation. Combined
preview includes full read-only Site preflight. Status freshly checks the Site
journal prefix and Device inventory; it does not change either journal.

Every Organization Device retains its source reference and parent dependency.
Controller-object/access inventories remain separate, with unmatched records,
duplicate addresses/identities and uncertain associations reported. Source
name/type/queried-IP corroboration is an association candidate, **not proof that
source ormID and tree managedElementID namespaces are equivalent**. No access
values or credentials are copied to reports. Unsupported/unprojected fields
are counted, not applied.

Only fresh-verified mappings from the original Site journal can resolve Device
parents; pending parents block without Default fallback. Read-only existing
Device qualification requires matching name/type/IP/native identity, unique
fresh tree membership and the expected verified destination Site. Matching IP
alone is insufficient. HTTP 400 is not Device absence; unknown responses stop
further Device lookups. No Device updates, reparenting, access writes or retries.
Existing inventory objects are never reported as fully configured/connectable.

**Device execution remains deliberately BLOCKED for all target versions.**
The only source-observed Device POST embeds `deviceSetup.deviceAccess`; an
inventory-only payload and create/completion contract have not been qualified.
No Device POST implementation or speculative credential defaults are enabled.
The explicit guarded entry points:

```bash
./ccv.sh --devices-execute "${migration_inputs[@]}"
./ccv.sh --devices-resume "${migration_inputs[@]}"
```

perform read-only qualification and maintain a protected zero-attempt per-Device
journal, but never ask for approval or write controller configuration while the
contract is blocked. Resume freshly checks identities/parents; attempted or
uncertain future journal states require manual reconciliation, never retry.
They share the Site engine's per-origin lock, private atomic storage and original
input/origin binding. A failed authentication does not create a Device journal.

Sanitized `ccv-devices-report-<random>.json` and protected
`ccv-devices-<plan-hash>-<origin-hash>.journal.json` use the existing reports
directory. Only the protected journal contains destination-native mappings.
All Device modes currently return exit **1** (blocked, not migration success),
even when read-only inventory checks finish. CC 10.10.x remains the primary
target; neither it nor the 10.15.x lab has qualified Device-create compatibility.
Docker build and real snapshots remain unverified locally.

#### CCV-011: experimental controlled single-Site migration

Primary target: **CC 10.10.x**; additional lab target: **CC 10.15.x**.
One shared implementation, **not certified write compatibility for either**.
The successful Default GET on 10.15.0-2 does not qualify POST, omitted source
fields, absence semantics or readback. The operator must explicitly accept these
risks before a separately authorized one-Site lab test.

On the authorized Linux destination host, from the reviewed updated checkout,
rebuild the **same shared image**; no new service, container type or settings:

```sh
cd /opt/radware/storage/scripts/CC--Vision-Core-Config-Import-Components
docker compose --profile destination-discovery config --quiet
docker compose --profile destination-discovery build ccv-destination-discovery
```

Keep the real protected backup, original destination snapshot and confirmed,
hash-bound comparison unchanged in their existing directories. The discovery
service now also mounts existing `/incoming` **read-only**. The comparison must
be the original complete report, not a manually reconstructed summary. With
standard mounts and the known lab artifact paths:

```sh
./ccv.sh --single-site-dry-run \
  --input /incoming/vision-backup-20261125T122823Z-3ad1c37f503d/organization-tree/tree.json \
  --comparison /reports/source-destination-site-comparison.json \
  --destination-snapshot /reports/cc-destination-20261126T001502Z-c71a84af2691/organization-sites.json \
  --site-reference source:node-2 \
  --target-version 10.15.0-2
```

Use the actual existing comparison basename if different. Select **2**; enter the
approved lab controller and credentials. This is a **live read-only preflight**,
not an offline command: fresh login, exact parent/candidate by-name lookups and
Organization tree. Source/snapshot hashes, selected comparison record, confirmed
root mapping, resolved destination-parent dependency, fresh parent identity and
collision checks must all pass. HTTP 404 or the exact legacy absence signature
is accepted only together with a fresh, structurally valid collision-free tree;
neither proves complete destination enumeration. Unrecognized evidence blocks.
No Device lookup, configuration write, root rename or source-ID reuse occurs.

The sanitized `ccv-single-site-<random>.json` is saved in destination-reports
(0600); no Site names, native IDs, credentials or response bodies are included.
Exit 0 / `dry-run-ready` means this bounded preflight passed, not compatibility
certification or write approval. The non-executable preview contains only:

```json
{
  "method": "POST",
  "path": "/mgmt/system/config/tree/site",
  "body_generated": false,
  "fields": {
    "name": "unchanged-protected-source-name",
    "parentOrmID": "fresh-protected-destination-ormID"
  }
}
```

**Only after separate owner authorization for the one-Site lab test**, invoke:

```sh
./ccv.sh --single-site-create \
  --input /incoming/vision-backup-20261125T122823Z-3ad1c37f503d/organization-tree/tree.json \
  --comparison /reports/source-destination-site-comparison.json \
  --destination-snapshot /reports/cc-destination-20261126T001502Z-c71a84af2691/organization-sites.json \
  --site-reference source:node-2 \
  --target-version 10.15.0-2
```

Select **2**. The launcher first performs the read-only stage. Only if it passes
does the same existing service run interactively for controlled execution.
Within that new authenticated session, fresh preflight displays the target origin,
artifact reference and experimental risks. Approval requires a real terminal and
the exact phrase `CREATE source:node-2`; blank/EOF/non-terminal cancels.
There is no `--yes`. A final same-session preflight rechecks after approval.
TLS starts verified; the existing default-NO, origin-bound session-only lab
exception remains separate from write authorization. Create-stage failures are
never automatically restarted, including TLS/authentication failures.

At most **one POST** sends only the protected source name and freshly resolved
destination ormID as parentOrmID. HTTP 200/201 alone is insufficient: the response
must identify the expected Site with a usable new ormID; at most three by-ID/tree
readback rounds must confirm the same identity, name and destination parent.
There is no inferred async/job API. Missing identity, 202, malformed output,
timeout, conflicting/duplicate identity or incomplete/wrong-parent readback stops
as **indeterminate**, exit nonzero, requiring manual reconciliation.
Read timeouts/deadlines are inherited (connect 10s/read 30s/request 60s, zero
transport retries); the existing DNS limitation means no hard overall wall-clock
containment claim.

A durable, private `.ccv-site-attempt-<hash>.json` reservation in the same reports
directory is written **before POST** and retained after success or uncertainty.
It blocks another attempt for that canonical origin/name across invocations.
Do not delete/reset it, change reports directories or switch controller aliases
to bypass it. Reconcile through an independently authorized administrator workflow;
there is no automatic retry, second create, rollback or deletion.
Child dependencies unresolved in the comparison remain blocked; no bulk,
Device, Scheduler or LDAP migration is enabled.

Offline developer verification (all controller connections mocked):

```sh
PYTHONPATH=src:tests python -S -B -m unittest \
  test_single_site test_http_backend test_destination_discovery \
  test_site_comparison test_compose_deployment test_unified_launcher
```

No live test or deployment is implied by these instructions. Before live use:
authorize the exact host/account/egress and one candidate, inspect a successful
dry-run, prevent concurrent GUI/API changes, accept the recorded unverified
contracts, and arrange manual reconciliation if completion cannot be proved.

### Administrator TLS/CA and egress provisioning

Before permitting live operations, authorize the controller/account and restrict
discovery's Docker egress to the approved CC address on TCP **443**, with approved
DNS only if required. The dedicated bridge is **not an egress firewall**; the
launcher never changes host rules or grants broader networking. Application
discovery permits only POST login and GET Organization tree at the chosen origin,
or POST login and the exact Default GET in explicitly selected root-only mode.
Explicit single-Site mode adds only the selected parent/candidate GETs and
Organization GET; separate runtime authorization arms one exact Site POST and
only the returned identity's by-ID GET. Other paths, methods, queries and origins
remain blocked.
Host validation checks syntax only; it does not resolve DNS or prove controller
identity. Actual TLS verification occurs in the existing selected operation.

TLS certificate-chain and hostname verification starts **TRUE** for every source
backup and destination discovery execution. There is no automatic downgrade.
System CA trust from the application image is used unless an
administrator PEM bundle is present. Provision an approved private CA before
execution (omit the unneeded product's command):

```sh
sudo install -m 0600 -o 10001 -g 10001 /absolute/private/vision-ca.pem \
  ../ccv-runtime/source-config/vision-ca.pem
sudo install -m 0600 -o 10001 -g 10001 /absolute/private/cc-ca.pem \
  ../ccv-runtime/destination-secrets/cc-ca.pem
```

Use regular, readable CA bundles, not symlinks or private keys. Invalid bundles
or explicitly configured missing bundles fail before credential collection.
A missing private CA cannot be identified from hostname syntax alone: if only
system trust is available, the actual operation must fail closed for an untrusted
controller certificate. Production certificates need an appropriate SAN matching
the entered hostname/IP; trusting a self-signed certificate does not fix a missing
SAN. Existing administrator
`CCV_*_DIR` and PEM-basename trust overrides are resolved through Compose;
normal engineers do not configure them. Rebuild after updating image system trust.

#### Optional administrator production restriction

The interactive default permits the **choice**, not an automatic downgrade or
unverified authentication. Engineers do not need to configure anything. To
prohibit TLS exceptions in production, an administrator sets the existing
non-secret control in the ignored Compose `.env`:

```dotenv
CCV_ALLOW_INSECURE_TLS_EXCEPTION=false
```

Omitting this control allows the default-NO interactive choice. An existing
explicit `false` remains a production lock; it is never silently removed.
Administrators can use `sudoedit .env`
when approved privileges are needed; never assume passwordless sudo. Keep the
configuration administrator-controlled, readable but not writable by engineers,
and do not put credentials in it. Docker access/configuration also requires
administrator control; this application is not a boundary against a Docker
administrator overriding the deployment.

There are no per-controller policy files to provision. Old `tls-policy.json`
files are no longer read. Remove obsolete persistent `CCV_TLS_VERIFY=false` /
`CCV_DESTINATION_TLS_VERIFY=false` overrides; these runtime flags alone cannot
authorize an exception.

#### Normal operator workflow

Run `./ccv.sh`, select **1** or **2**, and enter controller, username and hidden
password as before. A trusted certificate needs **no additional prompt**.
The TLS handshake verifies identity before any HTTP credentials are transmitted.

If certificate verification fails **before authentication**:

- With the optional production lock, execution stops with a sanitized certificate
  warning; there is no exception prompt.
- Otherwise, the launcher offers **one** “Untrusted/self-signed certificate. Continue without certificate verification for this session only? [y/N]” choice. Enter `y`/`yes` to approve.
  Blank input, EOF or any other answer stops safely.
- The warning explains controller impersonation and credential interception.
  HTTPS encryption without identity verification does not prevent those risks.
- Approval retries the same selected operation/origin once, without repeating
  credential prompts. It never retries partial collections or post-authentication
  failures and never silently downgrades.

The exception exists only in this execution's private temporary directory, with
mode **0600**, UID/GID **10001:10001**, and follows existing success/failure/INT/TERM
cleanup. It is not saved as a preference or reused for another controller/run.
Sanitized reports/snapshots record `tls.verify=false` and
`tls.exception_scope=selected_origin_current_execution`, without raw origin values.
Network restrictions, HTTPS and read-only API scope are unchanged. Source retries
retain a separate failed first-attempt report; transfer only the successful backup
folder identified by the final summary. No host Python or new Docker image is used.

After an approved update, rebuild and run offline configuration checks, then
perform **separately authorized** runtime validation:

```sh
docker compose --profile source build ccv-source
docker compose --profile source --profile destination --profile destination-discovery config --quiet
./ccv.sh
```

Select **2** for read-only destination discovery or **1** for source backup.
Confirm trusted certificates proceed without prompting. For an untrusted lab
certificate, first decline and verify no retry, then start a new execution and
explicitly approve; inspect its saved TLS scope/status. With the control false,
verify that certificate failure stops without offering an exception. Do not share
raw backup/snapshot data. No import is enabled.

### 5. Verification and troubleshooting

From the standard application directory, these checks are offline:

```sh
./ccv.sh --help
docker compose --profile source --profile destination --profile destination-discovery config --quiet
docker compose --profile source run --rm ccv-source --help
docker compose --profile destination run --rm --entrypoint python ccv-destination --version
docker compose --profile destination run --rm ccv-destination --operation operations
```

Expect Python **3.13.x** and help/operations exit 0. Check `git rev-parse HEAD`
on both hosts against the same approved revision. Do not print credentials.

| Problem | Check / action |
| --- | --- |
| Missing configuration/image | Run from the standard directory; confirm Compose v2, config validation and completed build |
| Launcher not executable | Administrator runs `chmod u+x ccv.sh` after clone/update |
| Sudo denied | Obtain approved ownership-provisioning permission; no controller credentials are collected |
| Missing backup or wrong mount | Check the selected folder and `.env`/shell path overrides; `/incoming` is intentionally read-only |
| Permission/SELinux failure | Check `sudo ls -ld` on the selected host paths, UID 10001 ownership/private modes, and administrator-approved labels; never use privileged/world-write workarounds |
| TLS failure on source/destination | Correct CA trust/certificate SAN or use the default-NO interactive session choice on an authorized controller. An explicit production lock prohibits exceptions |
| Invalid preflight metadata | Supply HTTPS origins and actual installed CC version; this is not a network probe |
| Partial backup/checksum mismatch | Stop; review source summary or repeat the approved transfer |
| Readiness exit 1 / report exists | Readiness remains blocked; choose a new report name, never overwrite artifacts |

### 6. Cleanup / update (identical on both hosts)

`run --rm` containers are removed after execution. Cleanup leaves every bind
directory, credential, backup, incoming package and report untouched:

```sh
docker compose --profile source --profile destination --profile destination-discovery down
```

For an **existing repository**, update in place during an approved idle window:

```sh
cd /opt/radware/storage/scripts/CC--Vision-Core-Config-Import-Components
git status --short
# Stop if there are local changes; do not force-reset, re-clone or change branches.
(test -z "$(git status --porcelain)" && git pull --ff-only)
```

Stop on update errors. Use the same approved revision on both hosts, then repeat
the shared deployment block in Install and the offline Verification commands.
Do not repeat source collection or transfer automatically during an update.

### Advanced Docker commands (administrators and approved unattended workflows)

These are diagnostics/existing interfaces, **not another installation procedure**.
The interactive operator entry point is always `./ccv.sh`. Existing
`run-vision-backup.sh` is retained for legacy deployments only; it is not the
recommended interactive launcher.

```sh
docker compose --profile destination-discovery run --rm ccv-destination-discovery --help
docker compose --profile destination run --rm ccv-destination \
  --operation tree-readiness-preview --site-readiness --report-format json \
  --input "/incoming/$BACKUP_FOLDER/organization-tree/tree.json" \
  --output "/reports/REPLACE-WITH-A-NEW-REPORT-NAME.json"
```

Existing direct `backup`/`discover-sites` shortcuts still require private
administrator credential mounts and connection/CA settings. They are not
normal-operator prerequisites. Existing metadata-only `preflight` validates
profile syntax, not a backup or connectivity, and requires independently known
version metadata; never substitute an invented version.

The [future import coordinator design](docs/IMPORT_COORDINATOR.md) specifies
dependency sequencing and proposed bounded timing settings. It is documentation
only: no import coordinator, timing variables, polling or write stages are enabled.

### Existing deployments: legacy paths only

Existing host-launcher deployments may retain `/srv/cc-vision-backups` and
`/srv/cc-vision-master-config`. That unchanged launcher used `/data` inside its
container; **Compose uses `/backups`**, not `/data`. Do not rename/delete existing
backups or switch their mounts blindly. Transfer an existing complete folder
through Step 3, or document approved `CCV_*_DIR` overrides for that deployment.
The launcher remains supported for existing installations, not a second
recommended deployment procedure.

For this host launcher, HTTPS verification remains enabled by default.
Disabling it requires a default-NO, exact-origin authorization prompt on every
interactive execution, including when loading a saved `tls.verify=false` profile.
Approval creates a credential-free, mode-0600 UID/GID-10001 temporary
`tls-exception.json`, mounted read-only beside the temporary credentials at
`/run/secrets/tls-exception.json`. It is removed with the temporary runtime files
after success, failure or cancellation, and is never saved in settings or backups.
Unattended `--non-interactive` runs reject `verify=false`; reusable settings alone
are not authorization. `CCV_ALLOW_INSECURE_TLS_EXCEPTION=false` still prohibits
insecure TLS. The host launcher checks this lock before provisioning and never
overrides the container image's own deployment control.

## Additional offline reference

These are optional execution tools using the same standard Compose deployment,
not other installation procedures. Default destination preflight is Step 4 above.

### Vision tree readiness preview

From the repository, inspect either existing native `tree.json` envelope:

```sh
docker compose --profile destination run --rm ccv-destination \
  --operation tree-readiness-preview \
  --input "/incoming/$BACKUP_FOLDER/physical-tree/tree.json" \
  --report-format json --output /reports/physical-readiness-new.json
```

No controller profiles, credentials or network access are required. `--output`
writes a new structured JSON report and refuses to overwrite an existing file;
omit it for stdout only. Text is the default for this operation only; existing
operations retain JSON output. URLs and UNC inputs are rejected.

The preview validates the Vision 5.4.9 backup envelope and counts inspected
node candidates, separately from top-level JSON records. It recognizes the
legacy-observed Site/Device classes and managedElementID string identities.
A single object root is a root candidate, not a vendor-qualified root.
Actual `children` nesting is observed; interpreting it as a parent/dependency
relationship is explicitly legacy-based inference. Missing/duplicate identities,
unknown classes/fields, malformed children and conflicting/unresolved explicit
parent references are reported without configuration names, addresses, IDs,
field names or values. Array root semantics remain unverified.

Dependency order is source nesting evidence only, never destination mapping or
write order. No ID aliases, device-access enrichment, credentials, import
payloads or executable plans are created. Root/site/device destination mappings,
schema/enumeration completeness and restoration remain unresolved.

Exit status **1** means inspected but migration readiness remains blocked,
including otherwise well-shaped trees. Status **3** reports local input/output
failure; **4** reports an invalid envelope or exceeded preview limits (depth 64,
10,000 node candidates). Original backup artifacts are never modified.

### Legacy cc-objects compatibility assessment

Add `--legacy-compatibility` to the tree preview to assess the original
downloader/uploader's flat field contract without producing an import file:

```sh
docker compose --profile destination run --rm ccv-destination \
  --operation tree-readiness-preview --legacy-compatibility \
  --input "/incoming/$BACKUP_FOLDER/organization-tree/tree.json" \
  --output /reports/organization-legacy-preview-new.json
```

Use the Physical tree input separately; add `--report-format json` for JSON
stdout. Exit status 1 means assessed but blocked, not migration-ready.
The report contains only counts, opaque node references and static field/code
labels, not copied source IDs, names, addresses, secrets or flat `sites/devices`.
Original source IDs and hierarchy remain unchanged in the original backups.

The original flat format is not interchangeable with native `tree` envelopes.
Legacy site/device projection and source-parent traversal are reusable concepts;
legacy by-IP access enrichment, root fallback, global site-name lookup and
destination writes are not adopted. Inventory-to-tree ID equivalence is not a
prerequisite to assess the tree subset, but the 36/35 difference still prevents
claiming full device coverage. Device-access enrichment, credentials, destination
IDs/root mapping and exact target-version compatibility remain unqualified.

### Site migration readiness

Step 4's `--site-readiness` command assesses only the source Sites in the
transferred Vision Organization backup.

Default stdout is a safe text summary; add `--report-format json` for structured
stdout. The optional JSON report is created exclusively, never overwritten.
`--site-readiness` cannot combine with `--legacy-compatibility` and rejects
Physical tree inputs. Exit 1 means assessed but migration remains blocked;
existing local-I/O/invalid-envelope exit codes 3/4 still apply.

The report assesses name and native source ID, derives source parent ID/name
from observed nesting, and lists source-only parent-before-child ordering.
The legacy Site-create loop consumes name/parent_site_name, not the flat
id/parentOrmID reference fields. The latter are retained conceptually for
source integrity, never treated as destination identities. Parent-name projection
from nesting is not certified equivalent to the original downloader's Site
lookup. The source root is context, not a Site to create.

Sufficient source fields do not establish full schema coverage or destination
readiness. Extra fields, duplicates, unknown structure, root/parent problems and
destination identity/schema requirements remain explicit. No source values,
Device associations, credentials, flat import files or executable plans are
produced; source identities and hierarchy remain in the unchanged backup.

### Offline Source-to-Destination Site comparison

Use the existing network-disabled destination service; no credentials or launcher
changes are required. From the standard checkout, select the **exact** saved
Organization backup and destination Site snapshot:

```sh
docker compose --profile destination run --rm ccv-destination \
  --operation site-comparison \
  --input /incoming/<backup-folder>/organization-tree/tree.json \
  --destination-snapshot /reports/<discovery-folder>/organization-sites.json \
  --source-root-name "<reviewed-source-root>" \
  --destination-root-name "<reviewed-destination-root>" \
  --destination-gui-version 10.15.0-2 \
  --output /reports/source-destination-site-comparison.json
```

Root names declare a **proposal** only. After reviewing both saved root records,
add `--confirm-root-mapping` to explicitly confirm their association; this is
neither identity equivalence nor permission to rename either root or write to CC.
Omit both root-name options to report a missing mapping. The GUI version is an
optional operator declaration, **not API verification**.

Default stdout is a sanitized text summary; `--report-format json` provides the
same structured evidence as the new output file. Exit **1** means comparison
generated but migration **BLOCKED**, including with confirmed roots and potential
creations. Missing/invalid inputs fail explicitly (3/4); no alternative snapshot
is selected. Choose a new output name on each run; inputs and existing outputs
are never overwritten.

The report preserves identities through distinct `source:node-*` and
`destination:node-*` artifact-local references bound to whole-input SHA-256.
Native IDs, names and unknown configuration values remain in the unchanged
protected inputs, not stdout/shared reports. No per-device hashes are emitted.
Exact Site names identify **potential collisions**, not proven identity matches.
Source parent-before-child order is retained; children explicitly depend on
future destination identity resolution after parent creation or qualification.
No Site is relocated and no Device is compared or associated.

An empty destination snapshot can yield potential creations, **not verified
absence or complete enumeration**. Unsupported/unprojected fields, root/parent
semantics, name matching rules, destination version/schema, native identity to
create-parent-field correspondence and post-create readback remain blockers.
The custom report domain cannot be used as an import file or executable plan.
Rebuild the existing shared image using the standard update procedure before
running the new operation; no new deployment method/service/image is introduced.

### Inventory/tree reconciliation reference

The [offline reconciler](src/cc_vision_import/inventory_reconciliation.py)
remains available for separately authorized investigations, not as a deployment
or mandatory destination-preflight step. It accepts saved inventory,
Organization and Physical tree inputs and an optional new output report.

The optional output must be a new file. Safe JSON stdout/report uses opaque
record references, counts and static issue codes, never native identifiers,
names, addresses or configuration values. Original backups are unchanged.
Existing tree preview validates trees and supplies containment/dependency evidence.

Inventory `ormId` and tree `meIdentifier.managedElementID` are separate native
identity fields with no established equivalence. Equal values, names or addresses
are not used to join them. The current report therefore returns status 1
(`identity-bridge-unverified`), zero **verified** matches, unresolved record
references, and null inventory-only/tree-only sets (unknown, not empty).
Duplicates/missing identities are evaluated within each representation.
Site associations describe observed tree containment and legacy-based parent
inference, not certified semantic parentage or destination mapping.
A record-count difference alone is not evidence that a specific device is missing.

Next prerequisite: qualify the native identity crosswalk with independent
schema evidence or an explicitly reviewed offline association contract before
implementing a one-to-one matcher. No name/IP/ID alias inference is authorized.

## Discovery, artifacts and results

Vision 5.4.9 evidence supports login POST
`/mgmt/system/user/login`, inventory GET
`/mgmt/system/config/itemlist/alldevices`, and supported site/device GETs.
Normal discovery preserves the recursive thin graph and native
`ormId`/`parentOrmId`; these are not aliased to lookup `ormID`.
Unique valid management IPs receive device-detail GETs. Unknown nonsecret fields
are preserved; passwords, usernames, communities and tokens are null/redacted.
Device detail `deviceSetup.deviceAccess.managementIp` must match the queried
IP after canonical normalization. A response `ormID` cannot be reused for a
different device IP in the same run. Missing identity, mismatched IP or repeated
response IDs fail the target before either controller/access file is written.
Error codes contain no device addresses or identities. Native discovery-ID to
lookup-ID equivalence is still not assumed.

There is no established pagination/full-tree guarantee. Empty sites, all tree
placements and full configuration completeness remain unverified. Malformed
responses, missing access or failed reads produce partial/failure results.
Device-access-only selection discovers devices but saves only access artifacts
and summary counts, not an unselected raw inventory.
Advanced targeted lookup arrays remain supported by the existing profile
contract, but are not the normal workflow or complete inventory exports.

```text
../ccv-runtime/source-backups/
  vision-backup-<UTC timestamp>-<random suffix>/
    controller-objects/
      inventory.json
      device-by-ip-001.json
    device-access/
      device-by-ip-001.json
    ldap-permissions/
      permissions.json
    physical-tree/
      tree.json
    organization-tree/
      tree.json
    scheduler/
      tasks.json
    summary.json
```

Only selected module directories appear. Artifacts include source name/version,
timestamp, native identifiers where present and scoped API evidence. Access object example:
`{"ormID": "device-1", "deviceAccess": {"cliPassword": null}}`.
Redaction counts describe processing of the underlying response.

### LDAP permissions scope

LDAP uses the legacy-observed GET
`/mgmt/system/config/itemlist/ldapobjectpermission` through the existing session,
TLS and credentials. It runs after controller/device collection, without
manual object input. An LDAP failure does not discard successful device files;
modules report their own results. LDAP-only selection does not query devices.

The supported response subset is a JSON array of objects with nonempty string
`attributeValue`. Present `objectClassName`/`attributeName` must be nonempty
strings; present `roleGroupPairList` must contain objects with string
`groupName`/`roleName`. Unknown fields and network policies are preserved,
without permission/locking changes. Shared recursive credential redaction also
redacts credential-valued LDAP attributes. Invalid records fail the collection,
not silently become an empty list. A genuinely empty list produces a valid
zero-record artifact.

Select only LDAP in a non-secret profile using:

```json
"backup_mode": "selected",
"domains": ["ldap-permissions"]
```

Keep the normal source/TLS/output settings; no controller object selection is
needed. The summary adds `ldap_permissions` (status, record_count, issues and
file when collected) and `ldap_permission_records`. Export evidence explicitly
says legacy-source-observed, not officially documented/live-tested. Exact
version-wide LDAP schema, pagination/enumeration completeness, restoration and
Vision-to-CC permission mapping are not qualified; this is not a full or
restorable LDAP configuration backup.

### Physical and Organization tree scope

The owner confirmed HTTP 200 and valid tree JSON from both exact GETs on the
authorized Vision 5.4.9 lab:

- `/mgmt/system/config/tree/Physical`
- `/mgmt/system/config/tree/Organization`

Each module reuses the existing authenticated session/TLS settings and runs
after device/LDAP collection. Select components `4,5`, or use a non-secret
profile with `"backup_mode": "selected"` and
`"domains": ["physical-tree", "organization-tree"]`. Tree-only selection needs
no device inputs and performs no device discovery or LDAP query.

Each separate `tree.json` envelope stores the redacted native JSON response in
`tree`, preserving the root object/array, ordering, unknown fields, identifiers
and parent relationships exactly as received apart from sensitive-field
redaction. No flattening, ID conversion, guessed parents or schema defaults.
JSON containers are retained without requiring undocumented node field types;
invalid JSON, scalar/null roots, explicit error responses and failed reads
produce module failures, not empty success artifacts.

Summary `trees["physical-tree"]` and `trees["organization-tree"]` report their
own status, record_count, file, issue codes and qualification limits. Counts
use `record_count_basis: "top_level_json_records"`: an object root counts as
one JSON record, an array counts its elements (an empty array counts as zero).
These are **not hierarchy-node counts**. A failure in one module preserves
already saved device/LDAP files and the other tree where the session remains usable.

Exact tree schemas, tree identity binding and enumeration/pagination completeness
remain unverified. Artifact evidence distinguishes owner-confirmed endpoint
reads from the new master implementation, which is offline-tested only; neither
exact endpoint is found in the reviewed Vision PDF. This is a native response
export, not a certified complete or restorable configuration backup. Existing
16 MiB response and recursive redaction limits still apply.

### Scheduler scope

Component `6` uses GET `/mgmt/system/config/itemlist/scheduledtask`, the
`API.scheduler_endpoint` value in both owner-supplied Scheduler INIs. The original
downloader uses a session GET with no query parameters or body after the existing
Vision login; the master retains its application headers and session cookies.
The master binds this one fixed read path, not an operator-configurable API URL.
It does not load the legacy INI or copy its credentials/controller settings.

For Scheduler-only collection use `"backup_mode": "selected"` and
`"domains": ["scheduler"]` with the normal source/TLS/output settings. It performs
no device discovery, LDAP or tree reads. Full Supported collects Scheduler last,
preserving already saved outputs from the five existing modules if Scheduler fails.

The source-observed response subset is an array of task objects. Each object is
preserved in `scheduler/tasks.json` under `tasks`, apart from existing sensitive-field
redaction. No required task name/type is invented; native IDs, status fields and
unknown fields are retained. Upload-only sanitization and name-based skipping are
not used. An empty array is a valid zero-record result; malformed/wrapped/non-object
records fail, never silently become empty success.

Summary `scheduler` reports status, record_count (saved array elements), file,
redactions and issue codes. Full schema, task types, timezone/reference semantics,
enumeration/pagination completeness and the new master live behavior remain
unverified. This is a source-observed export, not a certified full/restorable backup.
Existing response/redaction bounds apply; no remote logout or task writes are added.

Legacy naming caveat: both identical downloaders read `config.ini` relative to
their working directory, not the supplied `scheduler_config.ini` by name. The
supplied INIs establish the path reference; the master needs no rename/copy step.

Example summary fields (synthetic, not live acceptance):

```json
{
  "overall_status": "supported_collection_succeeded",
  "requested_modules": ["controller-objects", "device-access"],
  "completed_modules": ["controller-objects", "device-access"],
  "failed_modules": [],
  "device_details_collected": 1,
  "device_access_objects": 1,
  "tls": {"verify": true},
  "discovery_completeness": "partial-unverified",
  "scope": {"complete_inventory": false, "complete_configuration_backup": false, "migration_input": false}
}
```

```sh
sudo find /srv/cc-vision-backups -maxdepth 3 -type f -name '*.json'
sudo python3 -m json.tool /srv/cc-vision-backups/REPLACE_WITH_RUN_DIRECTORY/summary.json
```

Inspect module results, failed targets, issue codes and limitations, not file
count alone. These artifacts are **not migration inputs or complete restorable
configurations**. Store them as sensitive configuration with approved retention.

Exit 0 means selected supported collection succeeded, not full configuration
completeness. Exit 1 means partial/failed collection; successful partial files
remain. Usage/input errors use 2/3/4. Declining Start/Exit returns 0; Ctrl-C
returns 130. Docker may return 125/126/127 for startup/execution failures.

## Existing offline workflows

Use the same destination Compose service (networking disabled). Profiles validate syntax only;
exports adapt supplied local data, not controller downloads.

```sh
docker compose --profile destination run --rm ccv-destination \
  --operation profiles \
  --source-profile /app/examples/offline-controller/source-profile.json \
  --destination-profile /app/examples/offline-controller/destination-profile.json
docker compose --profile destination run --rm ccv-destination \
  --operation compare --request /app/examples/offline-controller/request.json
docker compose --profile destination run --rm ccv-destination \
  --operation plan --request /app/examples/offline-controller/request.json
```

The synthetic compare/plan fixture intentionally exits 1 (3 CREATE, 3 SKIP,
1 CONFLICT, 1 BLOCKED). Never relabel real controllers as synthetic `0.0-test`.
`import-preview` remains offline planning, not write authorization; standalone
`authenticate`/`import` remain unavailable.
Offline export output requires a writable external mount and a new `--output`
file; never mount over `/app` or overwrite existing exports.

## HTTP compatibility and collection limitations

The backend accepts identity or ordinary single-member gzip responses. Encoded
and decoded bodies each have a strict 16 MiB limit; truncated/corrupt gzip,
trailing data, multiple gzip members and oversized output are rejected before
session cookies are committed. Only repeated Cache-Control and Vary fields are
combined. Duplicate framing, authentication, content-type/encoding and other
unqualified headers remain rejected. Login still requires HTTP 200, JSON
`status: "ok"` and a valid body `jsessionid`; no cookie-only fallback or retry.

Selected Vision backups print a failure-only JSON diagnostic to stderr, with
event `vision_http_failure`, method, safe endpoint path/template, received status,
failure stage, normalized exception/error category, safe Content-Type/Encoding
and a validation reason. Header parameters and unrecognized values are
redacted/normalized. No credentials, cookies, tokens, bodies, full headers or
raw exception messages are printed. Login JSON/session validation failures are
reported too. Successful backups produce no extra diagnostic; the existing TLS
warning for explicit false is unchanged.

Use the standard Update step before a separately authorized source run.
Diagnostics appear on stderr; retain them only in approved private logs and
share sanitized diagnostic records, never raw responses. Gzip/repeated-header support is
offline-tested compatibility work, not proof of the original live root cause
or successful lab authentication.

Unsupported: complete Physical/Organization tree enumeration, restorable
credential backup, complete LDAP/Scheduler schema and enumeration qualification, live CC backup, appliance
configuration downloads and all configuration writes. Evidence gaps remain
documented internally rather than advertised as working modules.
Authentication is cleared locally; remote logout/renewal is not implemented.
Connect/read timeouts are 10s/30s, checked per-request deadline 60s and response
budget 16 MiB each for encoded and decoded data. DNS and whole-run execution are not hard-deadline bounded.
No redirects, automatic renewal or request retries.

Offline test evidence, owner-reported lab results and exact qualification limits
are recorded in [PROGRESS.md](docs/PROGRESS.md). Runbook maintenance does not
change collectors or certify new migration capabilities.

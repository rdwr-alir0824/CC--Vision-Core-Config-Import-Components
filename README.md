# CC-Vision Master

One on-demand application for supported, read-only APSolute Vision configuration
collection and existing offline export/comparison/planning workflows.
It reuses shared authentication, sessions, HTTP transport and JSON validation.
Original legacy scripts are references only: none are imported or executed.
The detailed capability/legacy mapping is maintained in the
[internal API matrix](docs/API_MATRIX.md).

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
deletes remain unavailable. Other Vision versions and Cyber Controller live
backup are not qualified. Existing offline commands remain available.

- **Deployment hosts:** approved Linux/Bash environment, Git, Docker and a
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
  ../ccv-runtime/destination-reports
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

Provision an approved least-privilege account's owner-private JSON credential
file containing exactly `username` and `password`. Do not put secret values in
command arguments or shell history:

```sh
sudo install -m 0600 -o 10001 -g 10001 /absolute/private/vision-credentials.json \
  ../ccv-runtime/source-secrets/credentials.json
read -r -p 'Approved Vision HTTPS origin: ' CCV_VISION_URL
export CCV_VISION_URL
export CCV_TLS_VERIFY=true
docker compose --profile source run --rm ccv-source backup
```

Run only after controller/account authorization. This executes all six read-only
modules, then exits; engine JSON and `summary.json` are preserved. The HTTPS origin
must contain no credentials, path, query or fragment. Verification defaults to
system trust. For a private CA, provision `source-config/vision-ca.pem`, readable
by UID 10001, and set `CCV_TRUSTED_CA=/run/config/vision-ca.pem`. Do not silently
disable TLS verification to resolve certificate failures.

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

After the transfer/completeness checks, validate non-secret profile metadata:

```sh
read -r -p 'Source Vision HTTPS origin (metadata only): ' CCV_VISION_URL
read -r -p 'Destination CC HTTPS origin (metadata only): ' CCV_DESTINATION_URL
read -r -p 'Exact installed CC version: ' CCV_DESTINATION_VERSION
export CCV_VISION_URL CCV_DESTINATION_URL CCV_DESTINATION_VERSION
docker compose --profile destination run --rm ccv-destination preflight

REPORT_NAME="${BACKUP_FOLDER}-sites-$(date -u +%Y%m%dT%H%M%SZ).json"
docker compose --profile destination run --rm ccv-destination \
  --operation tree-readiness-preview --site-readiness \
  --input "/incoming/$BACKUP_FOLDER/organization-tree/tree.json" \
  --output "/reports/$REPORT_NAME"
```

`preflight` invokes existing **profile syntax validation only**, exits 0 for
valid profiles, and does not read the backup or contact either controller.
The second command assesses source Sites from the transferred artifact; it
exits **1** when inspected but migration-blocked. Reports must have new names.
Neither command imports/restores anything. There is no live CC connectivity,
authentication, TLS, license/capacity preflight or complete package validator.

### 5. Verification and troubleshooting

From the standard application directory, these checks are offline:

```sh
docker compose --profile source --profile destination config --quiet
docker compose --profile source run --rm ccv-source --help
docker compose --profile destination run --rm --entrypoint python ccv-destination --version
docker compose --profile destination run --rm ccv-destination --operation operations
```

Expect Python **3.13.x** and help/operations exit 0. Check `git rev-parse HEAD`
on both hosts against the same approved revision. Do not print credentials.

| Problem | Check / action |
| --- | --- |
| Missing configuration/image | Run from the standard directory; confirm Compose v2, config validation and completed build |
| Missing backup or wrong mount | Check the selected folder and `.env`/shell path overrides; `/incoming` is intentionally read-only |
| Permission/SELinux failure | Check `sudo ls -ld` on the selected host paths, UID 10001 ownership/private modes, and administrator-approved labels; never use privileged/world-write workarounds |
| TLS failure on source | Use an approved CA and matching certificate hostname; no silent downgrade |
| Invalid preflight metadata | Supply HTTPS origins and actual installed CC version; this is not a network probe |
| Partial backup/checksum mismatch | Stop; review source summary or repeat the approved transfer |
| Readiness exit 1 / report exists | Readiness remains blocked; choose a new report name, never overwrite artifacts |

### 6. Cleanup / update (identical on both hosts)

`run --rm` containers are removed after execution. Cleanup leaves every bind
directory, credential, backup, incoming package and report untouched:

```sh
docker compose --profile source --profile destination down
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

### Existing deployments: legacy paths only

Existing host-launcher deployments may retain `/srv/cc-vision-backups` and
`/srv/cc-vision-master-config`. That unchanged launcher used `/data` inside its
container; **Compose uses `/backups`**, not `/data`. Do not rename/delete existing
backups or switch their mounts blindly. Transfer an existing complete folder
through Step 3, or document approved `CCV_*_DIR` overrides for that deployment.
The launcher remains supported for existing installations, not a second
recommended deployment procedure.

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

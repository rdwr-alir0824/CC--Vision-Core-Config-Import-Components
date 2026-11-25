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

The owner reports a successful Vision 5.4.9 run: 36 devices, 36 controller-object
exports, 36 device-access exports, 73 valid module JSON files and zero failures.
That confirms the prior deployed path, not the new identity guards or LDAP
collector. These changes are offline-tested; LDAP master collection still needs
authorized live validation. Full Supported Backup selects all three modules;
it does not mean every possible controller configuration
item or a restorable credential backup. Imports, updates and deletes remain
unavailable. Other Vision versions and Cyber Controller live backup are not
qualified. Existing offline commands remain available.

- **Host launcher:** authorized Linux, Bash, Python **3.8+**, Git and Docker.
  No third-party Python packages or appliance system-Python replacement.
- **Container engine:** official Python **3.13-slim**, `/app`,
  `PYTHONPATH=/app/src`, UID/GID **10001:10001**.
- Running the master directly outside Docker requires Python **3.12+**;
  it is not the recommended path on a Python 3.8 appliance.
- The launcher imports only its setup, policy and strict JSON helpers; deferred
  annotations preserve the host import path.

Docker access is privileged; use the host's approved access policy.
Do not start collection until the owner authorizes the controller and account.

## Clone, build and check offline

Select the branch containing the reviewed changes:

```sh
git clone --branch feature/ccv-010c-http-safety --single-branch \
  https://github.com/rdwr-alir0824/CC--Vision-Core-Config-Import-Components.git cc-vision-master
cd cc-vision-master
chmod +x run-vision-backup.sh
docker build --tag cc-vision-master:0.3 .
./run-vision-backup.sh --help
docker run --rm --network none --name cc-vision-master cc-vision-master:0.3 --help
docker run --rm --network none --name cc-vision-master cc-vision-master:0.3 --operation operations
docker run --rm --network none --name cc-vision-master \
  --entrypoint python cc-vision-master:0.3 --version
```

Expected container Python: **3.13.x**. Help/operations exit 0 and do not
authenticate or collect. An older image with the same tag must still be rebuilt
to include these source changes. Build needs the base image locally or registry
access; no controller connection is required.

The [.dockerignore](.dockerignore) limits build inputs to master/source and
approved synthetic offline examples. Credentials, operational JSON, vendor
PDFs, legacy artifacts, Git metadata, caches and TAR archives stay out.
[Git exclusions](.gitignore) are separate and cannot untrack existing sensitive
files. Owner review of tracked files/history remains required before publication.

## Portable Docker Compose roles

[compose.yaml](compose.yaml) provides independent `source` and `destination`
profiles. Both use the same Dockerfile/image (`cc-vision-master:0.3`, overridable
with `CC_VISION_IMAGE`). Rebuild it after updating the application. A current
Docker Compose v2 plugin is required. The file uses JSON-compatible YAML so its
structure can also be tested with Python's standard library.

- `ccv-source backup` delegates to existing `backup-vision`, Full Supported
  Backup (all six modules), with normal discovery, authentication and TLS rules.
  Running the source service without a command displays help, not a backup.
- `ccv-destination` defaults to the existing offline operation inventory.
  Existing master arguments, including tree/Site readiness, pass through.
  Its `preflight` shortcut invokes existing `profiles` validation using
  environment-derived, temporary non-secret profiles: **syntax only**.
- **Capability gaps:** no live Cyber Controller connectivity/authentication/TLS/
  licensing/capacity preflight exists. No complete six-module backup-package
  validator exists; tree readiness validates only the selected native artifact.
  A successful profile check does not qualify destination APIs or migration.

Containers run as `10001:10001`, with a read-only root filesystem, dropped
capabilities and no-new-privileges. Temporary profiles use a small `/tmp` tmpfs.
Source uses ordinary Compose bridge networking; destination has
`network_mode: none`. There are no published ports, host networking, Docker
socket mounts, nested Docker, persistent services or automatic restarts.
The host launcher remains unchanged and is a separate alternative to Compose.

### Prepare and build

Run commands from the clone on each relevant Docker host. By default, runtime
directories are siblings of the clone, outside the build context:

```sh
# Source host only:
sudo install -d -m 0700 -o 10001 -g 10001 \
  ../ccv-runtime/source-backups ../ccv-runtime/source-secrets \
  ../ccv-runtime/source-config
# Copy an already-provisioned owner-private {"username": "...", "password": "..."}
# JSON file; do not put credentials in command arguments, .env, Git or the image.
sudo install -m 0600 -o 10001 -g 10001 /absolute/private/vision-credentials.json \
  ../ccv-runtime/source-secrets/credentials.json

# Destination host only:
sudo install -d -m 0700 -o 10001 -g 10001 \
  ../ccv-runtime/destination-incoming ../ccv-runtime/destination-reports

# Offline configuration check; it does not start containers or contact controllers:
docker compose --profile source --profile destination config --quiet
# Build the shared image on a host with the base image or registry access:
docker compose --profile source --profile destination build
```

Only the selected role's directories must exist to run that role. Missing bind
directories fail instead of being silently created as root. On SELinux-enforcing
hosts, have the host administrator provision appropriate bind-mount labels.
Do not solve permission/label errors with privileged mode or world-writable data.

These optional environment variables override the five independent host binds:
`CCV_SOURCE_BACKUPS_DIR`, `CCV_SOURCE_SECRETS_DIR`, `CCV_SOURCE_CONFIG_DIR`,
`CCV_DESTINATION_INCOMING_DIR`, `CCV_DESTINATION_REPORTS_DIR`.
Use dedicated directories (prefer absolute paths), never the same source and
destination directory. Secrets/config and incoming packages are mounted read-only;
only backups and reports are writable. Ensure transferred input trees are
readable by UID 10001 and reports are writable by that UID.

### Source: explicit authorized backup

Non-secret connection settings come from environment variables, not the image:

```sh
docker compose --profile source run --rm ccv-source --help
read -r -p 'Approved Vision HTTPS origin: ' CCV_VISION_URL
export CCV_VISION_URL
export CCV_TLS_VERIFY=true
# Run only after authorization; this command authenticates and performs reads:
docker compose --profile source run --rm ccv-source backup
```

`CCV_SOURCE_NAME` defaults to `vision-source`; use the existing lowercase
hyphenated profile-name syntax. The origin must be HTTPS without credentials,
path, query or fragment. Credentials are read exclusively from the mounted
`source-secrets/credentials.json`. Full engine JSON stdout and per-run
`summary.json` are preserved; run directories appear in `source-backups/`.

For an approved private CA, provision it in `source-config/vision-ca.pem`
(readable by UID 10001), then set
`CCV_TRUSTED_CA=/run/config/vision-ca.pem`. Verification defaults to true/system
trust. Explicit `CCV_TLS_VERIFY=false` uses the existing warning-bearing backup
exception only; it is not the recommended deployment setting.

### Transfer and destination checks

Source and destination hosts need **no direct connectivity**. Through an approved
offline transfer process, copy a complete `vision-backup-...` directory into
`destination-incoming/` on the destination host, preserving private permissions
and UID-10001 readability. Do not copy the source credential directory.
Incoming packages are not embedded in or automatically unpacked by the image.

The same built image can also be transported without a registry:

```sh
# Build host; transfer this archive and the reviewed repository separately:
docker save --output cc-vision-master-0.3.tar cc-vision-master:0.3
# Destination host:
docker load --input cc-vision-master-0.3.tar
docker compose --profile destination run --rm --entrypoint python ccv-destination --version
docker compose --profile destination run --rm ccv-destination --operation operations

# Replace RUN with the transferred directory name; report name must be new:
docker compose --profile destination run --rm ccv-destination \
  --operation tree-readiness-preview --site-readiness \
  --input /incoming/RUN/organization-tree/tree.json \
  --output /reports/site-readiness.json
```

Python should report 3.13.x. Site readiness exits **1** when inspected but still
migration-blocked; this is expected, not a successful migration qualification.
Use `--report-format json` for machine-readable stdout. Omitting
`--site-readiness` uses the existing general tree check.

For **offline profile syntax preflight**, supply actual, non-secret origins and
the exact installed CC version; nothing is resolved or contacted:

```sh
read -r -p 'Source Vision HTTPS origin (metadata only): ' CCV_VISION_URL
read -r -p 'Destination CC HTTPS origin (metadata only): ' CCV_DESTINATION_URL
read -r -p 'Exact installed CC version: ' CCV_DESTINATION_VERSION
export CCV_VISION_URL CCV_DESTINATION_URL CCV_DESTINATION_VERSION
docker compose --profile destination run --rm ccv-destination preflight
```

`CCV_DESTINATION_NAME` defaults to `cyber-controller-destination`. Valid profiles
exit 0; this is not a read-only live CC probe. Preflight JSON is stdout only;
the existing `profiles` operation does not support `--output`.
All per-role environment settings are optional during Compose configuration,
image loading and offline tree checks; connection fields are required only by
the selected backup/preflight shortcut. A private ignored `.env` may contain
non-secret settings, but never passwords/tokens.

### Cleanup and offline verification

Each `run --rm` container exits and is removed. To remove Compose resources:

```sh
docker compose --profile source --profile destination down
```

This leaves bind-mounted backups, incoming packages, credentials and reports
untouched. No application/service needs to stay running.

Focused checks: `PYTHONPATH=src:tests python -S -B -m unittest test_compose_deployment`.
Docker/Compose configuration validation and image build/runtime checks remain
**unverified locally when Docker is unavailable**; structural tests and mocked
delegation are not a successful container build or deployment.

## Interactive backup

```sh
sudo ./run-vision-backup.sh
```

```text
=================================
       CC-VISION MASTER
=================================

1. Full Supported Backup
2. Select Backup Components
3. Backup from JSON Configuration
4. Exit
```

Full Supported Backup selects every currently supported module.
Select Backup Components offers **Controller Objects**, **Device Access**,
**LDAP Permissions**, **Physical Tree**, **Organization Tree** and **Scheduler**;
enter component numbers `1` through `6` or a comma-separated selection.
Blank still selects `1,2`, preserving the previous selected-mode default.
Full Supported includes all six;
existing explicit domain lists keep their previous scope. Other selections fail clearly.
Backup from JSON loads an existing non-secret profile and uses the same engine.

Menu options 1/2 finish with a readable six-module summary: status, collected
count and its meaning, redactions, limitations, run directory and overall status.
Tree counts are top-level JSON records, not hierarchy-node totals. Controller/
access redactions describe their source detail responses; controller inventory
redactions are not included in that terminal total, and access is not an
access-only redaction count. Unreported redactions are shown as such, not zero.
No raw device data or secret-bearing fields are displayed.

The full `summary.json` artifact is unchanged. `--config`, menu option 3 and
`--non-interactive` retain the existing engine JSON output and exit status.
Invalid/missing menu-mode engine output is reported explicitly without echoing
it; a successful engine with an unavailable readable summary returns launcher
status 3 (saved artifacts may still be valid). Existing nonzero engine statuses
are preserved. See the [coverage report](docs/API_MATRIX.md#operator-backup-coverage---vision-549)
for collected subsets, restoration gaps and unverified assumptions.

Normal setup displays the supported Vision source, then asks for:

1. Vision IP/HTTPS URL (an IP is normalized to an HTTPS origin).
2. Username and hidden password.
3. `Verify HTTPS certificate? [Y/n]:`
4. Persistent external output directory.
5. Optional non-secret settings save.
6. Final read-only backup confirmation.

### Offline Vision tree readiness preview

From the repository, inspect either existing native `tree.json` envelope:

```sh
python master.py --operation tree-readiness-preview \
  --input /srv/cc-vision-backups/<run>/physical-tree/tree.json

python master.py --operation tree-readiness-preview \
  --input /srv/cc-vision-backups/<run>/organization-tree/tree.json \
  --report-format json --output /srv/cc-vision-backups/organization-readiness.json
```

On Windows, use the same arguments with local Windows paths. No Docker,
controller profiles, credentials or network access are required. `--output`
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

### Offline legacy cc-objects compatibility assessment

Add `--legacy-compatibility` to the tree preview to assess the original
downloader/uploader's flat field contract without producing an import file:

```powershell
python master.py --operation tree-readiness-preview --legacy-compatibility `
  --input "C:\CCV-Backups\organization-tree\tree.json" `
  --output "C:\CCV-Backups\organization-legacy-preview.json"
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

### Offline Site migration readiness

Assess only the source Sites in an existing Vision Organization backup:

```powershell
python master.py --operation tree-readiness-preview --site-readiness `
  --input "C:\CCV-Backups\organization-tree\tree.json" `
  --output "C:\CCV-Backups\site-readiness.json"
```

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

### Offline inventory/tree reconciliation

From the repository on Windows, use only the saved local inputs:

```powershell
$env:PYTHONPATH = "$((Get-Location).Path)\src"
python -B -m cc_vision_import.inventory_reconciliation `
  --inventory "C:\CCV-Backups\controller-objects\inventory.json" `
  --organization "C:\CCV-Backups\organization-tree\tree.json" `
  --physical "C:\CCV-Backups\physical-tree\tree.json" `
  --output "C:\CCV-Backups\reconciliation-safe.json"
```

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

No individual site/device IDs or IP lists are needed for automatic discovery.
Opening the menu, help, Exit or declining Start makes no controller requests.
Temporary credentials are created only after execution confirmation.

Use `sudo`, or UID 10001 with Docker access and pre-provisioned writable output.
The **container always runs 10001:10001**, regardless of host launcher privilege.
Existing nonempty output directories are not recursively chowned; incompatible
ownership fails instead of using root containers or world-writable permissions.

## JSON configuration

Start with [profile.json](examples/vision-backup/profile.json), copy it outside
the clone and edit the HTTPS origin for the approved controller:

```sh
sudo install -d -m 0700 -o 10001 -g 10001 /srv/cc-vision-master-config
sudo install -m 0600 -o 10001 -g 10001 examples/vision-backup/profile.json \
  /srv/cc-vision-master-config/backup.json
```

```json
{
  "source": {
    "role": "source",
    "name": "vision-source",
    "product": "vision",
    "version": "5.4.9",
    "base_url": "https://vision.example.invalid"
  },
  "tls": {"verify": true},
  "backup_mode": "full-supported",
  "controller_objects": {"discovery": true},
  "output_directory": "/srv/cc-vision-backups"
}
```

For selected components, use `"backup_mode": "selected"` and add
`"domains": ["device-access"]` or the desired supported names.
Do not supply domains alongside full-supported mode. Unknown, duplicate,
unsupported or out-of-scope components fail before controller access.

Profiles contain **no usernames, passwords, tokens or credential references**.
Relative CA/output paths resolve beside the profile. Output must be a dedicated
directory outside the clone; the launcher provisions it where permitted and
maps it to `/data` in Docker.

```sh
# Preloaded settings; prompts for credentials and confirmation.
sudo ./run-vision-backup.sh --config /srv/cc-vision-master-config/backup.json

# Unattended: no prompts; the credential file below must already exist.
sudo ./run-vision-backup.sh --config /srv/cc-vision-master-config/backup.json \
  --non-interactive --credentials-file /srv/cc-vision-master-config/credentials.json
```

## TLS certificate verification

`tls.verify` accepts only JSON Booleans; omitted tls/verify defaults to **true**.

- `true`: verify the certificate and hostname using the **container's** system
  trust store. Host-added CAs are not automatically available inside Docker.
- `false`: disable certificate and hostname verification for this selected
  Vision backup only. No extra flag or certificate confirmation is needed.
  It applies to authentication and all read requests; unrelated operations
  retain mandatory verification.

Selecting No or setting false displays once:

```text
WARNING: HTTPS certificate verification is disabled.
```

Disabling verification increases the risk of **server impersonation and
credential interception**. There is no silent downgrade after a certificate
failure. A self-signed certificate fails with true unless its CA is trusted;
the hostname or IP SAN must also match.

Optional advanced trust with true:
`"tls": {"verify": true, "trusted_ca": "/srv/cc-vision-master-config/vision-ca.pem"}`.
The launcher stages/mounts this PEM bundle automatically. A custom CA combined
with false is rejected; no CA is required during normal setup.
Execution metadata retains `"tls": {"verify": false}` when selected.

## Credentials

Interactive credentials use private temporary JSON files, made readable by
UID 10001 and mounted read-only. Temporary files are removed after success,
failure or interruption. No secrets are saved in reusable settings, Docker
images, shell arguments, environment variables or logs.

For unattended execution, create an owner-private external file without placing
secrets in shell history:

```sh
sudo python3 -c 'import getpass,json,os; username=input("Vision username: "); password=getpass.getpass("Vision password: "); fd=os.open("/srv/cc-vision-master-config/credentials.json",os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600); f=os.fdopen(fd,"w"); json.dump({"username":username,"password":password},f); f.close()'
sudo chown 10001:10001 /srv/cc-vision-master-config/credentials.json
sudo chmod 0600 /srv/cc-vision-master-config/credentials.json
```

The contract is exactly username/password strings. Use an approved least-
privilege read account. This file is plaintext protected by host permissions:
keep it out of Git, exports, ordinary backups and logs. It is not overwritten
or automatically deleted; only the launcher's temporary copy is cleaned.
Initial and opened-file permission checks reject unsafe credential files.

## Configurable Docker image

Default: **`cc-vision-master:0.3`**, matching the current release tag.
The launcher inspects and runs the same selected reference. It never falls back
to an older image. To use a different reviewed build:

```sh
docker build --tag cc-vision-master:0.4 .
sudo env CC_VISION_IMAGE=cc-vision-master:0.4 ./run-vision-backup.sh
# When already running as an authorized root/UID-10001 operator:
CC_VISION_IMAGE=cc-vision-master:0.4 ./run-vision-backup.sh --config backup.json
```

Missing/inaccessible images report the selected reference and require an
explicit build/load or override. `CC_VISION_IMAGE` contains an image reference,
never credentials. The host launcher does not use Compose; the optional roles
above are independent. Neither path adds a persistent service, cron or ports.

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
/srv/cc-vision-backups/
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

Use Docker's Python runtime and `--network none`. Profiles validate syntax only;
exports adapt supplied local data, not controller downloads.

```sh
docker run --rm --network none --name cc-vision-master cc-vision-master:0.3 \
  --operation profiles \
  --source-profile /app/examples/offline-controller/source-profile.json \
  --destination-profile /app/examples/offline-controller/destination-profile.json
docker run --rm --network none --name cc-vision-master cc-vision-master:0.3 \
  --operation compare --request /app/examples/offline-controller/request.json
docker run --rm --network none --name cc-vision-master cc-vision-master:0.3 \
  --operation plan --request /app/examples/offline-controller/request.json
```

The synthetic compare/plan fixture intentionally exits 1 (3 CREATE, 3 SKIP,
1 CONFLICT, 1 BLOCKED). Never relabel real controllers as synthetic `0.0-test`.
`import-preview` remains offline planning, not write authorization; standalone
`authenticate`/`import` remain unavailable.
Offline export output requires a writable external mount and a new `--output`
file; never mount over `/app` or overwrite existing exports.

## Update, transfer and remove containers

From a clean clone on the intended branch:

```sh
git pull --ff-only
chmod +x run-vision-backup.sh
docker build --tag cc-vision-master:0.3 .
./run-vision-backup.sh --help
docker run --rm --network none --name cc-vision-master cc-vision-master:0.3 --operation operations
```

Stop on local changes/update errors; do not force-reset. For an approved host
without build access, transfer the matching-architecture image:

```sh
docker save --output cc-vision-master-0.3.tar cc-vision-master:0.3
# After approved transfer, on the target:
docker load --input cc-vision-master-0.3.tar
```

The image TAR does not include external settings/credentials/exports. Run on
demand; `--rm` removes the container but external output persists.
If a previous container was retained, inspect and remove it only when exited:

```sh
docker inspect --format '{{.State.Status}} {{.State.ExitCode}}' cc-vision-master
docker rm cc-vision-master
```

## Troubleshooting and known limitations

| Problem | Action |
| --- | --- |
| GitHub HTTPS authentication | Use approved Git credential management/token or SSH; never embed tokens in URLs |
| Docker/image missing | Check daemon access; build/load the selected tag or set CC_VISION_IMAGE |
| Mount path/CA missing | Use existing absolute host input paths; optional relative CA paths resolve beside the profile |
| Credentials/permissions | Check approved account and owner-private JSON; never print secrets or session IDs |
| Certificate validation fails | Trust its CA/use matching hostname, optional custom CA, or consciously select false with its documented risks |
| Controller unreachable | Check authorized bridge routing/firewall/HTTPS connectivity; no automatic network probing |
| Unsupported API/version or partial collection | Inspect sanitized issue codes/module status; stop rather than guessing endpoints or completeness |
| Output permissions | Use a dedicated external directory writable by UID 10001; no recursive chown/world-write workaround |
| Container name already exists | Inspect the owner's previous container and remove it only when safely exited |
| Abnormal Docker/client termination | Temporary files are normally cleaned; forced termination/daemon failure may require operator container/file cleanup |

### Vision login HTTP compatibility and diagnostics

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

After the reviewed changes have been published, update the approved lab clone
and rebuild; these are operator commands, not automatically executed:

```sh
git pull --ff-only
docker build --tag cc-vision-master:0.3 .
./run-vision-backup.sh --help
```

For the next separately authorized read-only lab run, use the unchanged launcher
and secure credential workflow. Optional private diagnostic capture:

```sh
umask 077
install -d -m 0700 "$HOME/cc-vision-master-logs"
./run-vision-backup.sh 2>"$HOME/cc-vision-master-logs/http-failure.log"
```

The launcher forwards diagnostics without requiring a new option. Share only
the sanitized diagnostic records if it fails. Gzip/repeated-header support is
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

Offline test evidence and exact limitations are recorded in
[PROGRESS.md](docs/PROGRESS.md). Updated Linux/Docker/live behavior still requires
owner-supervised validation; previous deployed-image results do not qualify
these changes. No live controller calls, Git operations or deployment were
performed during implementation.

## Owner-reviewed publication commands

Instructions only; review branch, all staged content, sensitive tracked files
and history before committing. The following is the exact ten-file device
qualification/LDAP change list.
Wrapper, root master, Dockerfile, original legacy scripts and containment
documentation are unchanged.

```sh
git status --short
git branch --show-current
test "$(git branch --show-current)" = feature/ccv-010c-http-safety || exit 1
git ls-files -- '*.pdf' '*.PDF' '*.tar' '*.ini' '*.pem'
# Stop for approved cleanup if sensitive/vendor files are tracked.
git add -- README.md docs/API_MATRIX.md docs/PROGRESS.md \
  src/cc_vision_import/capabilities.py \
  src/cc_vision_import/product_clients.py \
  src/cc_vision_import/backup_policy.py \
  src/cc_vision_import/backup_setup.py \
  src/cc_vision_import/vision_backup.py \
  tests/test_backup_setup.py tests/test_vision_backup.py
git --no-pager diff --cached --check
git --no-pager diff --cached
git commit -m "Validate device query identity and add read-only LDAP subset backup" \
  -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
git push origin HEAD:feature/ccv-010c-http-safety
```

Do not stage runtime JSON, credentials, controller exports, vendor PDFs or image
TARs. Rebuild the reviewed image and stop before live testing until separately
authorized.

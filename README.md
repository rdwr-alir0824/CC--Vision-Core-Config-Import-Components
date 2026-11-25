# CC-Vision Config Import: simplified MVP

This application consolidates the existing code behind [master.py](master.py).
Existing commands remain **offline**. The explicitly selected `backup-vision`
operation adds automatic discovery and read-only Vision 5.4.9 collection; it is not a full
configuration backup or migration capability. Configuration imports, updates,
and deletes remain unavailable. No legacy script is imported or executed.
CCV-010-C and the existing package CLI are unchanged.

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

### Controller Objects: source-only reads

No destination profile or migration manifest is needed for the following:

```powershell
python master.py --operation lookup-site-by-name --source-profile examples\offline-controller\source-profile.json --lookup-value Existing
python master.py --operation lookup-site-by-id --source-profile examples\offline-controller\source-profile.json --lookup-value src-existing --input examples\offline-controller\site-lookup.json --exported-at 2026-11-22T00:00:00Z
python master.py --operation lookup-device-by-ip --source-profile examples\offline-controller\source-profile.json --lookup-value 192.0.2.10 --input examples\offline-controller\device-lookup.json --exported-at 2026-11-22T00:00:00Z --output device-lookup-artifact.json
python master.py --operation export --source-profile examples\offline-controller\source-profile.json --input examples\offline-controller\source-tree.json --tree Physical --controller-id synthetic-source --exported-at 2026-11-22T00:00:00Z --output tree-export.json
```

Without `--input`, lookup returns a **request preview**, not a controller result.
With `--input`, it inspects a supplied synthetic single-object response, preserving
unknown fields. Minimum local identity evidence is a nonempty string `ormID` and
`name`; this is not a complete vendor schema. Responses without this evidence
(including empty JSON, the legacy not-found string, and managed-element-ID-only
aliases) are rejected, never treated as "not found."
The query-to-response association, alias equivalence, absence semantics and
live compatibility remain unverified. Inline credentials are rejected before
an artifact is written.

Optional lookup `--output` writes an artifact with a distinct lookup domain,
**not** `controller-objects`. A site/device lookup is not a tree/configuration
export and is not a migration input. Summaries omit object contents, controller
addresses and parameter values; supplied records can be inspected in the local
artifact. Output is never overwritten.

Supported lookup path templates are source-observed:
`GET /mgmt/system/config/tree/site/byname/{name}` (API-04),
`GET /mgmt/system/config/tree/site/byid/{id}` (API-05), and
`GET /mgmt/system/config/tree/device/byip/{ip}` (API-06).
Existing URL construction validates/encodes the parameter; no request is sent.
The shared CC client methods `get_site_by_name`, `get_site_by_id` and
`get_device_by_ip` reuse the existing managed-session authentication and GET
request path, but accept **explicit mock backends and `0.0-test` only**.
The offline lookup commands do not construct or authenticate such sessions.

Standalone export defaults to `--format tree`; select `--tree Physical` or
`Organization` explicitly. Legacy flat exports use `--format flat --root
source-root.json`, where the root file is a supplied source root with empty
children. Never infer a root or parent from a name. Both formats reuse existing
adapters. Missing device access is preserved as an invalid artifact with
`status: exported-incomplete`, issue codes and exit **1**; it cannot enter
planning. Completeness remains unverified even when offline validation succeeds.
Do not combine standalone input with `--request`.

`export` adapts a **supplied local source inventory** into an artifact. It does
not download controller data. Output must be a new file; existing files are never
overwritten. Artifacts contain configuration and must be stored appropriately.
Inline credentials are rejected; use existing `secret_ref` contracts or null
credential values. Manifest-based export still rejects incomplete/invalid
inventories without producing an output. Standalone export retains safely
representable incomplete data with the explicit invalid status described above.
Malformed data, unresolved parents, and inline credentials fail without output.

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
TLS certificate verification remains mandatory for existing operations.
Only explicitly selected Vision backup has the warned lab-only exception below.

For manifest-based export and planning, reuse [request.json](examples/offline-controller/request.json).
It binds source/destination profiles and inventories, controller IDs, explicit
mappings, device detail/access associations, policy, completeness declarations,
and acknowledgements. Manifest paths are relative to its directory; explicit
CLI profile paths are relative to the working directory. Optional
`--source-profile` / `--destination-profile` arguments must equal the corresponding
manifest profiles: they cannot silently redirect the workflow.

Accepted supplied inventory formats are recursive `tree`, context-qualified
legacy `flat` (with an explicit source root), and normalized `artifact`.
Manifest-based export reads the source side, including declared reconciliation, but requires
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
before future configuration changes. The separate `backup-vision` operation
permits only its documented login, inventory GET and device/site GETs, not standalone authentication
or configuration writes.

| Workflow | Current support |
|---|---|
| CC site/device lookup | Request preview and supplied single-response inspection; mock client GET methods; no complete-export claim |
| CC source-only tree/flat export | Local adapters, explicit root/context, preservation of incomplete data with invalid status |
| CC-to-CC controller objects | Existing synthetic manifest export, comparison, planning and import preview preserved |
| Vision-to-CC controller objects | Product/profile selection; migration unavailable because source export schemas and mappings are unestablished |
| General live Controller Objects/migration clients | Unavailable; migration capabilities remain default-deny; only the separate Vision backup path below permits live reads |
| Explicit `backup-vision` | Vision 5.4.9 documented login, managed-device discovery and device details/access; advanced targeted site/device GETs retained; mock tested, not live validated |
| Controller imports/updates/deletes | Unavailable; separate execution authorization and explicit action approval still required |
| LDAP, either direction to CC | Same operation selector; unavailable because CC endpoints/contracts and reference mappings are unresolved |
| Scheduler, either direction to CC | Same operation selector; unavailable because configured legacy paths and CC task contracts are unresolved |

The existing [API matrix](docs/API_MATRIX.md) remains the evidence source.
No endpoints, product equivalence, or compatibility claims were invented.

## Read-only Vision 5.4.9 backup

**Implemented and mock tested; not live tested. Do not run against a controller
until the owner explicitly authorizes the lab target and read-only test.**

`--operation backup-vision` authenticates once, discovers the accessible managed
device list, collects selected supported components, saves external JSON, and
exits. It does not establish complete site/tree enumeration, collect appliance
configuration downloads, or enable imports. **Full Supported Backup** means all
implemented modules, not a complete controller configuration backup.

Evidence: the locally supplied *APSolute Vision 5.4.9 REST API* documents
`POST /mgmt/system/user/login` (PDF pages 156-158), managed-device list GET
`/mgmt/system/config/itemlist/alldevices` (119-120; recursive model 263), site-by-name GET (141),
site-by-ID GET (146), and device-by-IP GET (143-144). The existing Vision LDAP
and Scheduler scripts supply reusable login/session intent; the object script
supplies read intent but targets CC. The documented managed-device response
provides the initial discovery path, not proof of full Vision enumeration.
No undocumented tree, LDAP, or Scheduler paths are used.
The old mock-only clients and `VERIFIED_CAPABILITIES` catalogue remain unchanged.

### Install and launch one application

Host requirements: authorized **Linux**, Bash, Git, Python **3.8+** for the
standard-library launcher, and working Docker access. The image runs Python
**3.13**; running the master directly instead requires Python **3.12+**.
Docker access is privileged; follow the host's approved access policy.
The host launcher imports only its setup, backup-policy and strict JSON helpers;
it does not import the Python 3.13 backup engine. Keep the appliance's system
Python unchanged: no host packages or Python replacement are required.
`./run-vision-backup.sh --help` exits before Docker, credentials or controller
access; menu Exit and declining Start also perform no controller access.
The host import chain uses deferred annotations for Python 3.8 compatibility.
This fix passed Python 3.8 grammar checks and Python 3.13.14 execution tests;
Python 3.8 runtime execution was unavailable on the development workstation.

```sh
git clone --branch feature/ccv-010c-http-safety --single-branch \
  https://github.com/rdwr-alir0824/CC--Vision-Core-Config-Import-Components.git cc-vision-master
cd cc-vision-master
chmod +x run-vision-backup.sh
docker build --tag cc-vision-master:0.2 .
docker run --rm --network none --name cc-vision-master cc-vision-master:0.2 --help
docker run --rm --network none --name cc-vision-master cc-vision-master:0.2 --operation operations
sudo ./run-vision-backup.sh
```

These are **operator instructions, not evidence of deployment or authorization
to connect**. Do not select Start until the owner authorizes the lab target.
Use a branch containing these changes; an older deployed `0.2` image must be
rebuilt even when reusing the tag.

The menu provides:

1. **Full Supported Backup**: controller-objects and device-access.
2. **Select Backup Components**: choose supported component numbers, separated
   by commas; unavailable modules and their reasons are displayed.
3. **Backup from JSON Configuration**: load non-secret settings, then prompt
   for credentials and confirmation.
4. **Exit**: no controller access.

Only APSolute Vision **5.4.9** is currently selectable. Interactive setup asks
for source, controller HTTPS address, username, hidden password,
`Verify HTTPS certificate? [Y/n]`, output directory, optional non-secret settings
save, and final confirmation. No manual CA or site/device list is required.
The launcher handles Docker mounts, private temporary files and output
provisioning; Docker always runs UID/GID **10001:10001**, never root. Run the
launcher as host root through `sudo`, or as UID 10001 with Docker access and
pre-provisioned output. Existing nonempty directories are not recursively
chowned; incompatible ownership fails explicitly.

### Supported modules and automatic discovery

| Module | Discovery / collection | Limits |
| --- | --- | --- |
| controller-objects | Documented `alldevices` GET; preserve recursive thin site/device graph, then GET each unique valid `managementIp` through device-by-IP | Native `ormId`/`parentOrmId` remain distinct from lookup `ormID`; empty sites and all Physical/Organization placements are not proven complete |
| device-access | Same discovery and device-detail GETs, extract `deviceSetup.deviceAccess` by native device `ormID` | Missing access marks this module incomplete; passwords, usernames, communities and tokens are redacted, not restorable credential backups |

The returned graph and unknown nonsecret fields are preserved; repeated device
IPs do not cause duplicate detail GETs. The supplied documentation establishes
no pagination parameters or full-inventory guarantee. No pagination paths,
extra requests or hierarchy placement are invented. Unsupported envelopes,
malformed addresses and failed detail requests produce explicit failures.
Empty valid discovery arrays are supported empty collections, not full backups.
Selecting device-access alone still discovers devices but does not save the
controller-objects module or raw inventory graph; discovery counts remain in
the summary.

Unavailable selections are rejected before live access:
`physical-tree`, `organization-tree`, `credential-configuration`,
`ldap-permissions`, `scheduler`; reasons are in the legacy matrix below.
Cyber Controller live backup, other Vision versions and all migration/import
capabilities remain unavailable.

**AMS-alerts is explicitly excluded, not a backlog module.** This includes
`AMS-alerts`, `AMS_alerts`, `AMS Alerts`, `AMSAlert`, `AMSAlerts` and equivalent
normalized naming variants. The menu never offers it; JSON selection rejects
it. The existing document-restoration script is not imported or executed.

### External profile and selection

Start with [profile.json](examples/vision-backup/profile.json). It contains:

- `source`: role/name, product `vision`, exact version `5.4.9`, HTTPS origin.
- `tls.verify`: boolean, default `true`, using system trust. Optional advanced
  `tls.trusted_ca` is a local PEM bundle path; omit it for normal setup.
- `backup_mode`: `full-supported`, or `selected` with a nonempty `domains`
  array of supported module names. Do not combine full-supported with domains.
- `controller_objects`: `{"discovery": true}` by default. Advanced explicit
  arrays `site_names`, `site_ids`, `device_ips` remain supported instead of
  discovery; do not combine them with discovery.
- `output_directory`: dedicated external host directory, outside the Git
  clone. Relative paths resolve beside the JSON file. The launcher creates it
  when permitted and translates it to `/data` inside Docker.

Example unattended/interactive configuration without secrets:

```json
{
  "source": {
    "role": "source",
    "name": "lab-vision",
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

For selected modules replace `backup_mode` with `"selected"` and add, for
example, `"domains": ["device-access"]`. Unknown, duplicated, unsupported or
excluded modules fail rather than silently narrowing the request.

```sh
# Preloaded settings; prompts for username/hidden password and confirmation.
sudo ./run-vision-backup.sh --config /srv/cc-vision-master-config/backup.json

# Unattended explicit selection; never prompts or stores secrets in backup.json.
sudo ./run-vision-backup.sh --config /srv/cc-vision-master-config/backup.json \
  --non-interactive --credentials-file /srv/cc-vision-master-config/credentials.json
```

### Simple TLS configuration

`"tls": {"verify": true}` (or omitted tls/verify) verifies certificate and
hostname against system trust. A self-signed certificate fails unless its CA
is trusted; use the certificate's matching hostname/IP SAN. System trust here
means the **container's** trust store, not automatically the host's added CAs. Optional advanced
`"trusted_ca": "/srv/cc-vision-master-config/vision-ca.pem"` selects a custom
trusted PEM bundle; the launcher mounts it automatically.

`"tls": {"verify": false}` is permitted **only** with explicitly selected
`--lab-only`, including interactive mode. There is no silent fallback on a
certificate error, and the insecure setting cannot affect other operations.
The warning appears before login and applies consistently to login and GETs:

> WARNING: LAB-ONLY HTTPS certificate verification is disabled. Server
> impersonation and credential interception are possible.

```sh
# Only after lab authorization; JSON must explicitly set tls.verify=false.
sudo ./run-vision-backup.sh --config /srv/cc-vision-master-config/backup.json \
  --non-interactive --credentials-file /srv/cc-vision-master-config/credentials.json \
  --lab-only
# Interactive lab mode: explicitly select it before answering No.
sudo ./run-vision-backup.sh --lab-only
```

Do not combine `verify=false` with custom CA trust; do not use this exception
for production. Interactive mode without `--lab-only` rejects a No answer.

Replace synthetic device addresses with approved **managed-device IPs**.
Those are not the source Vision management address. For advanced targeted
mode, use the approved Vision
address in `source.base_url`. If using an IP, its certificate must have a matching
IP SAN; otherwise use the certified hostname or the explicit lab-only exception.
Site IDs must be native source `ormID` values; do not invent or reuse destination
IDs. `Default` is a documented root-name example, not guaranteed on every system.
Relative CA/output paths are relative to the profile file.
At most 100 unique explicit operation/target pairs are accepted; automatic
discovery is bounded by the existing response size budget, not this manual cap.

The example profile is available in the Git clone but intentionally excluded
from the image; the live run uses an external profile. Do not add passwords,
usernames, tokens, or `secret_ref` to it. This workflow accepts credentials only
through temporary credential files. Interactive passwords are never saved
to the reusable profile. Unattended mode requires the separate credentials file.

### Secure credential provisioning

Interactive mode needs no pre-created credential file: the launcher writes
owner-private runtime credential/settings files outside Git, mounts them
read-only, and removes them on completion, failure or cancellation. Secret
values are not passed in shell arguments or environment variables.

For unattended mode, prepare a private external configuration directory and
copy the example (edit the controller URL outside the Git clone):

```sh
sudo install -d -m 0750 -o 10001 -g 10001 /srv/cc-vision-master-config
sudo install -m 0640 -o 10001 -g 10001 examples/vision-backup/profile.json /srv/cc-vision-master-config/backup.json
```

Create credentials interactively using host Python 3; neither secret appears in
shell history, command arguments, environment variables, or the profile:

```sh
sudo python3 -c 'import getpass,json,os; username=input("Vision username: "); password=getpass.getpass("Vision password: "); fd=os.open("/srv/cc-vision-master-config/credentials.json",os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600); f=os.fdopen(fd,"w"); json.dump({"username":username,"password":password},f); f.close()'
sudo chown 10001:10001 /srv/cc-vision-master-config/credentials.json
sudo chmod 0600 /srv/cc-vision-master-config/credentials.json
```

The file is plaintext secret storage protected by host permissions: keep it out
of Git, images, output directories, ordinary backups, and logs. Use an approved
least-privilege read account. Existing credential files are not overwritten.
For rotation, replace the specific file using your approved secret-handling
procedure. The reusable input credential file is **not automatically deleted**;
only the launcher's temporary copy is removed. On POSIX, the application rejects group/world-readable credential
files. On Windows, filesystem ACLs must be secured by the operator.
Do not supply credentials as CLI values or Docker environment variables.

### Advanced direct Docker command (only after lab authorization)

Rebuild the updated application image first. The existing Dockerfile already
copies the new source; no dependency installation or service is needed.

```sh
docker build --tag cc-vision-master:0.2 .

docker run --rm --network bridge --name cc-vision-master \
  --user 10001:10001 \
  --mount type=bind,source=/srv/cc-vision-master-config/backup.json,target=/run/config/profile.json,readonly \
  --mount type=bind,source=/srv/cc-vision-master-config/credentials.json,target=/run/secrets/vision-credentials.json,readonly \
  --mount type=bind,source=/srv/cc-vision-master-data,target=/data \
  cc-vision-master:0.2 --operation backup-vision \
  --backup-profile /run/config/profile.json \
  --credentials-file /run/secrets/vision-credentials.json
echo "Exit code: $?"
```

Unlike offline smoke tests, this explicit operation needs network connectivity
from the Docker bridge to the approved Vision HTTPS origin. No host networking,
published ports, proxy, cron, persistent process, or configuration-write operation
is needed. For **direct Docker only**, edit the external profile output directory
to `/data` and pre-create `/srv/cc-vision-master-data` writable by UID 10001
(directory provisioning example below). UID/GID `10001:10001` must read both
input mounts and write the output. For optional custom CA, also mount its file
read-only at the profile's `trusted_ca` path. Prefer the launcher, which
translates these paths and provisions permissions automatically.

### Results and output

Each run creates a new private `vision-backup-<UTC timestamp>-<random suffix>`
directory organized as follows. No existing output is overwritten:

```text
vision-backup-<UTC timestamp>-<random suffix>/
  summary.json
  controller-objects/
    inventory.json
    device-by-ip-001.json
  device-access/
    device-by-ip-001.json
```

`inventory.json` preserves the returned recursive thin graph and has domain
`vision-managed-device-inventory`; `device-access` files have domain
`vision-device-access`, with objects shaped as
`{"ormID": "device-1", "deviceAccess": {"cliPassword": null}}`.
Only selected module directories are created. Advanced site lookup files go
under controller-objects. Example **synthetic advanced lookup** file:

```json
{
  "schema_version": 1,
  "domain": "vision-controller-object-lookup",
  "source": {"product": "vision", "version": "5.4.9", "name": "lab-vision"},
  "collected_at": "2026-11-24T12:00:00+00:00",
  "scope": {
    "requested_targets_only": true,
    "complete_inventory": false,
    "complete_configuration_backup": false,
    "migration_input": false
  },
  "request": {
    "method": "GET",
    "path_template": "/mgmt/system/config/tree/site/byname/{name}",
    "target": "Default"
  },
  "evidence": {
    "document": "DOC-V549",
    "pdf_pages": [141],
    "live_compatibility_verified": false
  },
  "objects": [{"ormID": "site-1", "name": "Default", "type": "Site"}],
  "redacted_fields": 0,
  "issue_codes": []
}
```

Unknown response fields are preserved; recognized credential/token/community
fields are explicitly replaced with `null` and counted as redactions.
Redaction counts describe the underlying response processing, including for
device-access files extracted from a larger device response.
The documented model subset is checked without inventing full wire-schema
semantics. Device responses must supply nonempty `ormID`/`name` as local identity
evidence; device query-to-response binding remains explicitly unverified.
These files are **not migration inputs** or restorable complete configurations.
Store them as sensitive configuration, even after credential redaction.

Stdout and `summary.json` report requested/completed/failed modules,
discovered objects, device detail/access counts, per-target filenames,
unsupported/excluded modules, and stable failure codes.
They omit controller addresses, target values, object contents, credentials,
tokens, and raw server error messages. `execution_authorized: false` means
configuration execution/import remains unauthorized; `live_read_selected: true`
identifies the explicitly selected read workflow.

Example selected summary fields (synthetic, not a live acceptance result):

```json
{
  "overall_status": "supported_collection_succeeded",
  "requested_modules": ["controller-objects", "device-access"],
  "completed_modules": ["controller-objects", "device-access"],
  "failed_modules": [],
  "collected_objects": 2,
  "device_details_collected": 1,
  "device_access_objects": 1,
  "discovery_completeness": "partial-unverified",
  "scope": {"complete_inventory": false, "complete_configuration_backup": false, "migration_input": false}
}
```

Exit **0** means all selected supported reads were collected, not a complete
backup. Exit **1** means collection/login/cleanup or a selected module failed;
successful partial files are retained and explicitly incomplete.
Existing usage/input/contract exits remain **2/3/4**. Invalid profile, CA, or
output directory fails before controller access. Credential resolution fails
before login dispatch. No successful output is fabricated for a failed read.
Launcher cancellation returns 0 before Start, or 130 for Ctrl-C; launcher
setup errors return 2 and file/input/Docker-launch errors return 3. Docker
itself may return 125/126/127 for startup/execution failures.

Inspect the dedicated output after execution:

```sh
sudo find /srv/cc-vision-backups -maxdepth 3 -type f -name '*.json'
sudo python3 -m json.tool /srv/cc-vision-backups/REPLACE_WITH_RUN_DIRECTORY/summary.json
```

Inspect failure codes, module results and limitations, not just file count.
`partial_collection`/`failed_collection` are failures, never complete backups.
Treat artifacts as sensitive configuration and use approved retention/access.

### Bounds, verification, and remaining capabilities

Only documented login POST, the discovery GET and exact selected/discovered GET targets are authorized.
No automatic login renewal, redirects, GET retries, or configuration-write retry
is performed. Authentication cookies are held in memory and cleared locally.
Remote logout is not implemented; the server session may remain until expiry.
Fixed limits: connect timeout 10s, read timeout 30s, checked per-request deadline
60s, response body 16 MiB. The owner's explicit live-transport opt-in accepts that
synchronous DNS and whole-run execution are **not hard-deadline bounded**.
No containment guarantee is claimed; default backend construction remains blocked.

Offline verification uses existing unittest network guards and mocked HTTP/Docker
responses: documented cookie handling, discovery/target parsing, redaction,
partial module reporting, TLS propagation/default-deny, module/AMS rejection,
menu cancellation and private runtime credential cleanup. Actual results are
recorded in [PROGRESS.md](docs/PROGRESS.md). Windows cannot exercise real Linux
ownership/mount behavior. Docker build and live compatibility remain unverified.

Still unavailable: proven complete site/device discovery, full configuration
backup, LDAP/Scheduler collection, managed-appliance configuration downloads,
credential backup/portability, Vision-to-CC migration, CC live backup, all
configuration writes/imports/deletes, and live compatibility qualification.
No live controller access, deployment, Git operations, or new-image Docker build
was performed. The previously operator-tested container does not validate this
updated live-read implementation.

### Troubleshooting

| Problem | Action |
| --- | --- |
| GitHub HTTPS authentication fails | Use an approved Git credential manager/token or approved SSH access; do not embed tokens in clone URLs or profiles |
| Docker/image unavailable | Confirm daemon access and rebuild `cc-vision-master:0.2` from the updated branch |
| Missing mount path | Use existing absolute host paths; the launcher stages inputs and optional CA automatically |
| Credential permissions | Use owner-private regular JSON (`chmod 600`); direct Docker input must be readable by UID 10001 |
| Invalid credentials/login schema | Check the approved least-privilege account; inspect sanitized login failure codes, never print passwords/session IDs |
| Certificate verification failure | Trust its CA/use matching certified hostname; optional trusted_ca or explicitly authorized warned lab-only exception, never silent fallback |
| Controller unreachable | Confirm authorized bridge routing/firewall/HTTPS access; no automatic network probing is provided |
| Unsupported API/version | Stop; verify installed Vision build and documented contract; do not substitute guessed paths or synthetic versions |
| Missing enumeration/partial backup | Inspect inventory status, failed targets/modules and limitations; available list is not proof of full configuration coverage |
| Output permission error | Use a dedicated external directory owned/writable by UID 10001; no recursive ownership changes or world-write workaround |
| Container name already exists | Inspect the owner's previous `cc-vision-master` container; remove it only when safely exited, using the commands below |
| Abnormal Docker/client interruption | Inspect the owner's container state; temporary host files are cleaned, but Docker-daemon failure/forced termination may require operator cleanup |

## Docker deployment

This replaces the legacy application image with the unified
[master.py](master.py), preserving offline behavior and adding only the
explicit read-only backup described above. The
[Dockerfile](Dockerfile) uses the official `python:3.13-slim` image, `/app`,
`PYTHONPATH=/app/src`, and non-root UID/GID `10001:10001`. The Python entrypoint
receives CLI arguments directly, executes one operation, and exits.
Only the standard library is required: no packages or dependency manifest are
needed. No cron, installation/startup shell scripts, service manager, background
worker, Windows containment/IPC, or new DNS-validation components are required.

The [.dockerignore](.dockerignore) allows only the Docker build files,
[master.py](master.py), Python source under [src](src), and the 15 explicitly
listed synthetic JSON examples under [offline-controller](examples/offline-controller)
into the build context. The examples retain their relative paths inside
`/app/examples/offline-controller`; no other runtime files are needed.
Git metadata, virtual environments, caches, credentials, local configuration,
exported controller JSON, vendor API PDFs, image TAR archives, tests,
documentation, and unrelated legacy artifacts are excluded.
Never embed secrets in Python source. Keep credentials and configuration outside
the image. Only explicit `backup-vision` resolves the external credentials file
and authenticates; offline commands never do.
Mount any required local JSON inputs read-only, separately from the output
directory. Do not mount over `/app`, which would hide the packaged application.

Git exclusions are separate: [.gitignore](.gitignore) excludes virtual
environments, caches, secrets, operational directories, JSON (except synthetic
examples/test fixtures), PDFs, and image archives. Never put real credentials or
controller exports into the synthetic fixture directories. Docker exclusions
do not protect Git commits, and Git exclusions do not untrack existing files.
The two local vendor PDFs were retained at the owner's request; Git tracking
and history were not inspected because Git operations were prohibited.
Before publishing, the owner must verify that PDFs, credentials, live
configuration, and image archives are not tracked or present in published
history. Ignore rules alone cannot establish that a Git clone excludes them.

### Clone and select the intended branch

On an authorized Linux lab Docker host, select the intended updated branch:

```sh
REPOSITORY_URL='https://github.com/rdwr-alir0824/CC--Vision-Core-Config-Import-Components.git'
BRANCH='feature/ccv-010c-http-safety'
git clone --branch "$BRANCH" --single-branch "$REPOSITORY_URL" cc-vision-master
cd cc-vision-master
chmod +x run-vision-backup.sh
```

Select a branch containing the packaging changes on top of master checkpoint
`056e5e0`; checking out that checkpoint alone does not include these changes.
These commands are instructions only, not evidence of a clone or deployment.

### A. Build the image

Run from the clone's repository root on Linux, or from this repository in
PowerShell with Docker configured for Linux containers:

```powershell
docker build --tag cc-vision-master:0.2 .
```

The build needs the official base image available locally or access to its
registry. No controller connection is needed. Build for the lab host's CPU
architecture; `docker save`/`docker load` do not convert architectures.

### B. Run CLI help

```powershell
docker run --rm --network none --name cc-vision-master cc-vision-master:0.2 --help
```

### C. List offline operations

```powershell
docker run --rm --network none --name cc-vision-master cc-vision-master:0.2 --operation operations
```

All offline examples in this section disable networking. No authentication,
controller reads, configuration imports/writes, or production capability
activation occurs during those smoke checks. The explicit live command above
is the sole separate read-only selection.

### D. Mount a local directory for exported JSON

```powershell
New-Item -ItemType Directory -Force -Path .\exports | Out-Null
$exportDirectory = (Resolve-Path .\exports).Path
docker run --rm --network none --name cc-vision-master --mount "type=bind,source=$exportDirectory,target=/exports" cc-vision-master:0.2 --operation operations
```

This safely demonstrates the output mount; `operations` only prints JSON to
stdout and creates no file. For a separately selected offline local-data export,
use `--output /exports/<new-file>.json` and supply the required inputs through a
separate read-only bind mount. Exports are configuration artifacts, not secrets
storage; existing output files are never overwritten.
On Linux, the output directory must be writable by UID/GID `10001:10001`
(or an explicitly selected non-root `--user UID:GID` matching its ownership).
Do not use root or world-writable permissions as a workaround. Docker Desktop
bind-mount permissions depend on host file-sharing settings.

For an authorized Linux host, create a dedicated external data directory
(only directory provisioning requires elevated permissions):

```sh
sudo install -d -m 0750 -o 10001 -g 10001 /srv/cc-vision-master-data
docker run --rm --network none --name cc-vision-master --mount "type=bind,source=/srv/cc-vision-master-data,target=/data" cc-vision-master:0.2 --operation operations
```

Use `--output /data/<new-file>.json` for a separately selected offline export.
Operator access to the directory must follow the host's approved permissions.
The default smoke operation writes nothing.

### E. Export the image to a TAR archive

```powershell
docker save --output cc-vision-master-0.2.tar cc-vision-master:0.2
```

Transfer the TAR to an authorized lab Docker host. It contains the image, not
bind-mounted inputs or exported configuration. No actual appliance deployment
is part of this task.

### F. Load the image on the lab Docker host

After placing the archive in the host's current directory:

```sh
docker load --input cc-vision-master-0.2.tar
```

### G. Run on demand

```sh
docker run --network none --name cc-vision-master cc-vision-master:0.2 --operation operations
docker inspect --format '{{.State.ExitCode}}' cc-vision-master
```

This runs in the foreground and leaves an exited container for inspection.
No restart policy, persistent service, port publishing, or host networking is
needed. Retain the existing CLI exit-code meanings described above.

### H. Remove the exited container

```sh
docker rm cc-vision-master
```

Remove it before reusing the same container name. The `--rm` examples instead
remove the container automatically after execution; bind-mounted files persist.
Removing a container does not remove the image or its TAR archive.

### Update the clone and rebuild

From the clean clone on the intended branch:

```sh
git pull --ff-only
chmod +x run-vision-backup.sh
docker build --tag cc-vision-master:0.2 .
docker run --rm --network none --name cc-vision-master cc-vision-master:0.2 --help
docker run --rm --network none --name cc-vision-master cc-vision-master:0.2 --operation operations
```

If the update fails or local changes exist, stop and resolve them explicitly;
do not force-reset the clone. Remove any previously retained exited container
as in H before reusing its name. For TAR-only targets, save and transfer the
rebuilt image, then load it again as in E/F; recreating the container uses the
updated tag. No cron, persistent service, or automatic background update is used.

### Minimal offline verification

Where Docker is available, build as in A, then run B and C. Verify the image's
Python version separately (this overrides the entrypoint only for the check):

```powershell
docker run --rm --network none --name cc-vision-master --entrypoint python cc-vision-master:0.2 --version
```

Expected: Python **3.13.x**, help exits **0**, and `operations` exits **0** with
`offline_only: true` and `execution_authorized: false`.
Historical packaging verification passed on Python **3.13.14** under `python -S -B`
(no third-party site packages). An isolated temporary runtime contained only
[master.py](master.py), all 33 Python source files, and the 15 allowlisted JSON
examples. All source imports were standard-library or internal modules, and all
example JSON parsed successfully.
Eight guarded CLI checks passed: help, operations, and profiles exited **0**;
synthetic comparison retained its intentional exit **1**; authentication and
import were explicitly refused with exit **4** and `live_execution_disabled`;
both supplied lookup fixtures exited **0** without writing artifacts.
Existing offline-test guards recorded zero attempts across all 15 guarded
socket/DNS/HTTP targets for each command. Temporary files were cleaned up.
No controller connection, authentication, import, or configuration write was
performed. No Git commands were run; tracked-file and history exclusions remain
an owner verification requirement before publishing.
Docker remains unavailable in the development environment: the updated image
build, Linux bind-mount permissions and TAR save/load are **unverified**.
Earlier operator-supplied results established Python 3.13.18, UID/GID 10001,
`/app`, help and offline operations on the earlier image; those results do not
validate the new backup implementation.

## Simple architecture and reuse inventory

```text
master.py -> src/cc_vision_import/master_cli.py
               profiles + strict local JSON input
               supplied export adapters + device reconciliation
               controller comparison + existing offline planning reports
               explicit backup-vision -> existing sessions/HTTP -> Vision GETs
run-vision-backup.sh -> backup_setup.py -> one on-demand Docker invocation
```

The new CLI composes existing functions rather than introducing another
authentication, transport, object model, or planner.

Inventory: **25 script files: 17 Python and 8 shell**. Twenty-four were reviewed
read-only for applicable functionality; the AMS restoration script is explicitly
excluded. Product versions are unspecified in the legacy scripts, so legacy
intent is not exact-version qualification. All original files remain unchanged.

| All available references (identical copies grouped) | Original function / evidence / dependencies | Unified application mapping |
|---|---|---|
| [CC download](legacy/app/download_cybercontroller_objects.py), [copy](legacy/cc-objects/app/download_cybercontroller_objects.py) | CC intent; Basic+JSON login; recursive Physical/Organization GETs, site-by-name/ID and device-by-IP GETs, nested device access extraction; missing operation INI; requests/urllib3/configparser; no pagination | Shared auth/session/read intent reused. Offline tree/flat adapters retained. Vision controller-objects/device-access use separately documented Vision GETs; CC live backup and Vision tree enumeration unavailable |
| [CC upload](legacy/app/upload_cybercontroller_objects.py), [copy](legacy/cc-objects/app/upload_cybercontroller_objects.py) | CC intent; duplicate login/INI; site/device POST writes, supporting tree/site GETs; requests/urllib3 | Upload-only, not backup. No writes reused; unsafe root fallback/name-only placement not adopted |
| [CC update](legacy/app/update_cybercontroller_objects.py), [copy](legacy/cc-objects/app/update_cybercontroller_objects.py) | CC intent; duplicate login/INI; device PUT writes, supporting GETs; requests/urllib3 | Update-only, not backup. Offline explicit mapping/comparison retained; no source IDs reused on destination |
| [Credential transformer](legacy/app/update_json_credentials.py), [copy](legacy/cc-objects/app/update_json_credentials.py) | Local JSON transformation, no authentication/API; external credential JSON; prints credentials | Not a backup/API module. Unsafe secret printing/mutation not ported; device-access backup explicitly redacts credentials |
| [LDAP download](legacy/download_ldap_permissions%20(1).py), [copy](legacy/ldap_permissions/download_ldap_permissions%20(1).py) | Vision JSON login; GET `/mgmt/system/config/itemlist/ldapobjectpermission`; missing `vision.ini`; requests/urllib3; no enumeration/pagination contract | Login/session intent reused. LDAP selection unavailable: source-observed path lacks exact Vision 5.4.9 documented response qualification; CC contract absent |
| [LDAP upload](legacy/upload_ldap_permissions%20(1).py), [copy](legacy/ldap_permissions/upload_ldap_permissions%20(1).py) | Vision login and LDAP POST; missing `vision.ini`; requests/urllib3 | Import-only, not backup. No forced locking, broadened scope fallback or write retry reused |
| [Scheduler download](legacy/download_scheduler.py), [copy](legacy/schedulertask/download_scheduler.py) | Vision JSON login/session/logout intent; configured scheduler GET, missing scheduler `config.ini` API bindings; requests/urllib3 | Shared login/session reused. Scheduler unavailable: literal configured endpoint, response/task contract and enumeration not established |
| [Scheduler upload](legacy/upload_scheduler.py), [copy](legacy/schedulertask/upload_scheduler.py) | Vision login, configured task GET/create, sanitization/name-based skip; missing API INI; requests/urllib3 | Create/import-only, not backup. Paths, sanitization and name-only skip not adopted; legacy session logging not reused |
| [Sleep wrapper](legacy/app/run.sh), [copy](legacy/cc-objects/app/run.sh) | Sleep-based persistent runtime | Excluded: master runs a selected operation and exits |
| [Installer](legacy/2install.sh), [copy](legacy/cc-objects/2install.sh) | Docker load/create and optional cron; deployment INI/Linux utilities | No legacy installation/cron workflow; use Git clone/build or Docker save/load |
| [Uninstaller](legacy/2uninstall.sh), [copy](legacy/cc-objects/2uninstall.sh) | Docker stop/remove and cron cleanup | Not an application module; explicit operator container cleanup only |
| [Container wrapper](legacy/run-cc-objects.sh), [copy](legacy/cc-objects/run-cc-objects.sh) | Docker start/exec/stop | Replaced by the on-demand [launcher](run-vision-backup.sh), not invoked |
| [AMS restoration](legacy/AMS-alerts/restore_cfg.py) | Explicitly excluded; not reviewed for integration | AMS-alerts and all normalized naming variants excluded, not backlog |

Read-only SHA-256 comparison confirmed **12 duplicate pairs**, including all
three top-level deployment shell copies. No copies were changed, deleted or
executed. [Legacy deployment config](legacy/cc-objects/config.ini) and the old
image archive are not application API contracts.

Missing bindings: Vision LDAP `vision.ini`; Scheduler `config.ini` containing
login/logout/scheduler endpoint settings; CC object download/upload/update
operation INI profiles (for example `download.ini`). The supplied deployment
INI is not a substitute. The local Vision PDF supplies the current login,
discovery, lookup and device-access model evidence; it does not establish
Vision Physical/Organization or LDAP/Scheduler collection contracts.

Legacy Python dependencies are `requests` and `urllib3`, plus standard-library
JSON/configparser/getpass/logging utilities. Shell helpers depend on Docker and
Linux utilities/cron, not on the master offline application. No runtime dependency
manifest or third-party application dependencies were added.

Additional shared reuse:
[transport](src/cc_vision_import/transport.py) provides the existing HTTP request
interface; [artifacts](src/cc_vision_import/artifacts.py) preserves exported JSON
and validates credential handling; [workflow](src/cc_vision_import/controller_workflow.py)
provides comparison, planning and redacted result/error reports. Offline master
commands never construct sessions, a backend, or production clients. Shared
`read_request_segments` and `adapt_read_response` in
[product_clients](src/cc_vision_import/product_clients.py) consolidate request
binding and JSON response processing for local inspection and mock clients.
No parallel authentication implementation or credential/write retries were added.

## Owner-reviewed publication (instructions only)

No Git commands were executed during this implementation. Review all changes
and already staged content before publishing. The following is the exact
live-backup/launcher file list to stage; existing Dockerfile/.dockerignore are
unchanged by this phase. Legacy references and vendor PDFs are local evidence,
not runtime/build requirements, and must not be added.

On the intended branch, after owner approval:

```sh
git status --short
git branch --show-current
# Stop unless this is the intended branch containing the reviewed changes.
test "$(git branch --show-current)" = feature/ccv-010c-http-safety || exit 1

# Inspect tracked references/history separately; ignore rules cannot untrack them.
git ls-files -- '*.pdf' '*.PDF' '*.tar' '*.tar.gz' '*.ini' '*.pem'
git --no-pager log --all --oneline -- '*.pdf' '*.PDF' '*.tar' '*.tar.gz' '*.ini' '*.pem'
# Stop if secrets/vendor documents/archives require approved cleanup.

git add -- \
  master.py \
  README.md \
  .gitignore \
  .gitattributes \
  run-vision-backup.sh \
  examples/vision-backup/profile.json \
  src/cc_vision_import/authentication.py \
  src/cc_vision_import/sessions.py \
  src/cc_vision_import/transport.py \
  src/cc_vision_import/http_backend.py \
  src/cc_vision_import/product_clients.py \
  src/cc_vision_import/schema_qualification.py \
  src/cc_vision_import/offline_inputs.py \
  src/cc_vision_import/master_cli.py \
  src/cc_vision_import/vision_backup.py \
  src/cc_vision_import/backup_policy.py \
  src/cc_vision_import/backup_setup.py \
  tests/test_vision_backup.py \
  tests/test_backup_setup.py \
  docs/API_MATRIX.md \
  docs/PROGRESS.md
git update-index --chmod=+x run-vision-backup.sh
git --no-pager diff --cached --check
git --no-pager diff --cached --stat
git --no-pager diff --cached
# Review the actual staged contents, including any unrelated prior staging.
git commit -m "Add read-only Vision backup and interactive Docker launcher" \
  -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
git push origin HEAD:feature/ccv-010c-http-safety
```

These commands are not publication evidence. Do not commit runtime JSON,
credentials, local operational settings, controller exports or vendor PDFs.
After publishing, follow the clean-clone update/rebuild commands above; stop
before live collection until the lab target is separately authorized.

## Offline MVP implementation report (historical)

Implemented: unified offline selectors and shared profile validation, source-only
tree/flat export, three CC lookup previews/local-response inspection operations,
shared mock-only lookup GET methods, and preserved manifest
export/comparison/planning/import preview. Existing root entry point is unchanged.

Verification: **76 targeted guarded tests passed** across the existing product
client, controller workflow and mocked integration test modules, including six
focused new regressions; zero guarded network attempts. Master/client syntax and
Pylance checks passed. No legacy execution, live tests, Git operations, new
testing framework, containment-document/PDF changes, or additional milestones.

Remaining: real-controller reads/authentication, approved import execution,
Vision controller adapters/mappings, CC LDAP and Scheduler contracts, and
real-version qualification. All remain unavailable; resolving or enabling them
requires a separate decision, not automatic continuation of this MVP.

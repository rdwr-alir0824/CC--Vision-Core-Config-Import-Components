# CC-Vision Config Import: simplified MVP

This application consolidates the existing code behind [master.py](master.py).
Existing commands remain **offline**. The explicitly selected `backup-vision`
operation adds targeted, read-only Vision 5.4.9 collection; it is not a full
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
TLS certificate verification remains mandatory, including for the explicit
live backup operation; this CLI has no TLS-disable option.

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
permits only its documented login and targeted GETs, not standalone authentication
or configuration writes.

| Workflow | Current support |
|---|---|
| CC site/device lookup | Request preview and supplied single-response inspection; mock client GET methods; no complete-export claim |
| CC source-only tree/flat export | Local adapters, explicit root/context, preservation of incomplete data with invalid status |
| CC-to-CC controller objects | Existing synthetic manifest export, comparison, planning and import preview preserved |
| Vision-to-CC controller objects | Product/profile selection; migration unavailable because source export schemas and mappings are unestablished |
| General live Controller Objects/migration clients | Unavailable; migration capabilities remain default-deny; only the separate targeted Vision backup path below permits live reads |
| Explicit `backup-vision` | Vision 5.4.9 documented login and profile-listed site/device GETs; mocked offline verification only; no discovery or complete-inventory claim |
| Controller imports/updates/deletes | Unavailable; separate execution authorization and explicit action approval still required |
| LDAP, either direction to CC | Same operation selector; unavailable because CC endpoints/contracts and reference mappings are unresolved |
| Scheduler, either direction to CC | Same operation selector; unavailable because configured legacy paths and CC task contracts are unresolved |

The existing [API matrix](docs/API_MATRIX.md) remains the evidence source.
No endpoints, product equivalence, or compatibility claims were invented.

## Read-only Vision 5.4.9 backup

**Implemented and mock tested; not live tested. Do not run against a controller
until the owner explicitly authorizes the lab target and read-only test.**

`--operation backup-vision` authenticates once, collects only explicitly listed
sites/devices, writes new JSON files to an external output directory, and exits.
It does not discover all objects, walk Physical/Organization trees, collect
device configurations from managed appliances, or enable imports.

Evidence: the locally supplied *APSolute Vision 5.4.9 REST API* documents
`POST /mgmt/system/user/login` (PDF pages 156-158), site-by-name GET (141),
site-by-ID GET (146), and device-by-IP GET (143-144). The existing Vision LDAP
and Scheduler scripts supply reusable login/session intent; the object script
supplies read intent but targets CC. Neither establishes full Vision enumeration.
No undocumented tree, LDAP, or Scheduler paths are used.
The old mock-only clients and `VERIFIED_CAPABILITIES` catalogue remain unchanged.

### External profile and selection

Start with [profile.json](examples/vision-backup/profile.json). It contains:

- `source`: role/name, product `vision`, exact version `5.4.9`, HTTPS origin.
- `tls`: `verify: true`; `trusted_ca` is a local PEM CA bundle path, or `null`
  to use system trust. Certificate and hostname verification are mandatory.
- `domains`: requested domains; only `controller-objects` is implemented.
  Other domain identifiers are explicitly reported as unsupported.
- `controller_objects`: explicit arrays `site_names`, `site_ids`, `device_ips`.
  Empty arrays omit that lookup category. No enumeration is inferred.
- `output_directory`: an existing writable external directory.

Replace synthetic device addresses with approved **managed-device IPs**.
Those are not the source Vision management address. Use the approved Vision
address in `source.base_url`. If using an IP, its certificate must have a matching
IP SAN; otherwise use the certified hostname. Never disable verification.
Site IDs must be native source `ormID` values; do not invent or reuse destination
IDs. `Default` is a documented root-name example, not guaranteed on every system.
Relative CA/output paths are relative to the profile file.
At most 100 unique operation/target pairs are accepted.

The example profile is available in the Git clone but intentionally excluded
from the image; the live run uses an external profile. Do not add passwords,
usernames, tokens, or `secret_ref` to it. This workflow accepts credentials only
through the separate `--credentials-file` option.

### Secure credential provisioning

On the approved Linux Docker host, prepare private external directories and copy
the profile and your approved CA bundle (edit the profile outside the Git clone):

```sh
sudo install -d -m 0750 -o 10001 -g 10001 /srv/cc-vision-master-config /srv/cc-vision-master-data
sudo install -m 0640 -o 10001 -g 10001 examples/vision-backup/profile.json /srv/cc-vision-master-config/profile.json
sudo install -m 0644 ./vision-ca.pem /srv/cc-vision-master-config/vision-ca.pem
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
procedure. On POSIX, the application rejects group/world-readable credential
files. On Windows, filesystem ACLs must be secured by the operator.
Do not supply credentials as CLI values or Docker environment variables.

### Docker command (only after lab authorization)

Rebuild the updated application image first. The existing Dockerfile already
copies the new source; no dependency installation or service is needed.

```sh
docker build --tag cc-vision-master:0.1 .

docker run --rm --network bridge --name cc-vision-master \
  --mount type=bind,source=/srv/cc-vision-master-config/profile.json,target=/run/config/profile.json,readonly \
  --mount type=bind,source=/srv/cc-vision-master-config/vision-ca.pem,target=/run/config/vision-ca.pem,readonly \
  --mount type=bind,source=/srv/cc-vision-master-config/credentials.json,target=/run/secrets/vision-credentials.json,readonly \
  --mount type=bind,source=/srv/cc-vision-master-data,target=/data \
  cc-vision-master:0.1 --operation backup-vision \
  --backup-profile /run/config/profile.json \
  --credentials-file /run/secrets/vision-credentials.json
echo "Exit code: $?"
```

Unlike offline smoke tests, this explicit operation needs network connectivity
from the Docker bridge to the approved Vision HTTPS origin. No host networking,
published ports, proxy, cron, persistent process, or configuration-write operation
is needed. UID/GID `10001:10001` must be able to read the three input mounts and
write the output mount. If `trusted_ca` is `null`, omit the CA mount.

### Results and output

Each run creates a new private `vision-backup-<UTC timestamp>-<random suffix>`
directory containing `summary.json` and one file per successfully collected
lookup, such as `site-by-name-001.json`. No existing output is overwritten.
Example **synthetic** lookup file:

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
The documented model subset is checked without inventing full wire-schema
semantics. Device responses must supply nonempty `ormID`/`name` as local identity
evidence; device query-to-response binding remains explicitly unverified.
These files are **not migration inputs** or restorable complete configurations.
Store them as sensitive configuration, even after credential redaction.

Stdout and `summary.json` report collected/failed/uncollected target counts,
per-target indices and filenames, unsupported domains, and stable failure codes.
They omit controller addresses, target values, object contents, credentials,
tokens, and raw server error messages. `execution_authorized: false` means
configuration execution/import remains unauthorized; `live_read_selected: true`
identifies the explicitly selected read workflow.

Exit **0** means all requested target reads were collected, not a complete
backup. Exit **1** means collection/login/cleanup failed or a requested domain
was unsupported; successful partial files are retained and explicitly incomplete.
Existing usage/input/contract exits remain **2/3/4**. Invalid profile, CA, or
output directory fails before controller access. Credential resolution fails
before login dispatch. No successful output is fabricated for a failed read.

### Bounds, verification, and remaining capabilities

Only documented login POST and exact selected GET targets are authorized.
No automatic login renewal, redirects, GET retries, or configuration-write retry
is performed. Authentication cookies are held in memory and cleared locally.
Remote logout is not implemented; the server session may remain until expiry.
Fixed limits: connect timeout 10s, read timeout 30s, checked per-request deadline
60s, response body 16 MiB. The owner's explicit live-transport opt-in accepts that
synchronous DNS and whole-run execution are **not hard-deadline bounded**.
No containment guarantee is claimed; default backend construction remains blocked.

Offline verification: **170 targeted guarded tests passed** across the new
eight-test backup module and existing workflow, product-client, authentication,
and HTTP-backend modules. Mocked responses demonstrated documented cookie
handling, target GETs, parsing, credential redaction, partial/error reporting,
unsupported-domain reporting, TLS/default-deny behavior, no authentication
renewal, and separate non-overwriting run directories. All network guards
reported zero attempts. Windows cannot execute the POSIX credential-mode branch;
that branch and external Linux mount permissions remain unverified.

Still unavailable: automatic full site/device discovery, full configuration
backup, LDAP/Scheduler collection, managed-appliance configuration downloads,
credential backup/portability, Vision-to-CC migration, CC live backup, all
configuration writes/imports/deletes, and live compatibility qualification.
No live controller access, deployment, Git operations, or new-image Docker build
was performed. The previously operator-tested container does not validate this
updated live-read implementation.

## Docker deployment

This replaces the legacy application image with the existing offline
[master.py](master.py), without changing application behavior. The
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

On an authorized Linux lab Docker host, substitute the actual repository URL
and branch (neither is assumed here):

```sh
REPOSITORY_URL='REPLACE_WITH_AUTHORIZED_REPOSITORY_URL'
BRANCH='REPLACE_WITH_INTENDED_BRANCH'
git clone --branch "$BRANCH" --single-branch "$REPOSITORY_URL" cc-vision-master
cd cc-vision-master
```

Select a branch containing the packaging changes on top of master checkpoint
`056e5e0`; checking out that checkpoint alone does not include these changes.
These commands are instructions only, not evidence of a clone or deployment.

### A. Build the image

Run from the clone's repository root on Linux, or from this repository in
PowerShell with Docker configured for Linux containers:

```powershell
docker build --tag cc-vision-master:0.1 .
```

The build needs the official base image available locally or access to its
registry. No controller connection is needed. Build for the lab host's CPU
architecture; `docker save`/`docker load` do not convert architectures.

### B. Run CLI help

```powershell
docker run --rm --network none --name cc-vision-master cc-vision-master:0.1 --help
```

### C. List offline operations

```powershell
docker run --rm --network none --name cc-vision-master cc-vision-master:0.1 --operation operations
```

All offline examples in this section disable networking. No authentication,
controller reads, configuration imports/writes, or production capability
activation occurs during those smoke checks. The explicit live command above
is the sole separate read-only selection.

### D. Mount a local directory for exported JSON

```powershell
New-Item -ItemType Directory -Force -Path .\exports | Out-Null
$exportDirectory = (Resolve-Path .\exports).Path
docker run --rm --network none --name cc-vision-master --mount "type=bind,source=$exportDirectory,target=/exports" cc-vision-master:0.1 --operation operations
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
docker run --rm --network none --name cc-vision-master --mount "type=bind,source=/srv/cc-vision-master-data,target=/data" cc-vision-master:0.1 --operation operations
```

Use `--output /data/<new-file>.json` for a separately selected offline export.
Operator access to the directory must follow the host's approved permissions.
The default smoke operation writes nothing.

### E. Export the image to a TAR archive

```powershell
docker save --output cc-vision-master-0.1.tar cc-vision-master:0.1
```

Transfer the TAR to an authorized lab Docker host. It contains the image, not
bind-mounted inputs or exported configuration. No actual appliance deployment
is part of this task.

### F. Load the image on the lab Docker host

After placing the archive in the host's current directory:

```sh
docker load --input cc-vision-master-0.1.tar
```

### G. Run on demand

```sh
docker run --network none --name cc-vision-master cc-vision-master:0.1 --operation operations
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
docker build --tag cc-vision-master:0.1 .
docker run --rm --network none --name cc-vision-master cc-vision-master:0.1 --help
docker run --rm --network none --name cc-vision-master cc-vision-master:0.1 --operation operations
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
docker run --rm --network none --name cc-vision-master --entrypoint python cc-vision-master:0.1 --version
```

Expected: Python **3.13.x**, help exits **0**, and `operations` exits **0** with
`offline_only: true` and `execution_authorized: false`.
Local packaging verification passed on Python **3.13.14** under `python -S -B`
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
Docker was unavailable in the development environment: the image build,
in-container Python/CLI behavior, bind-mount permissions, and TAR save/load
remain **unverified**, not successful deployment claims.

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
provides comparison, planning and redacted result/error reports. Offline master
commands never construct sessions, a backend, or production clients. Shared
`read_request_segments` and `adapt_read_response` in
[product_clients](src/cc_vision_import/product_clients.py) consolidate request
binding and JSON response processing for local inspection and mock clients.
No parallel authentication implementation or credential/write retries were added.

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

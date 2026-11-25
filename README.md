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

Both are **implemented and mock-tested, not live-verified**. Full Supported
Backup selects both; it does not mean every possible controller configuration
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
Select Backup Components offers **Controller Objects** and **Device Access**;
enter `1`, `2`, or `1,2` (blank selects both). Other selections fail clearly.
Backup from JSON loads an existing non-secret profile and uses the same engine.

Normal setup displays the supported Vision source, then asks for:

1. Vision IP/HTTPS URL (an IP is normalized to an HTTPS origin).
2. Username and hidden password.
3. `Verify HTTPS certificate? [Y/n]:`
4. Persistent external output directory.
5. Optional non-secret settings save.
6. Final read-only backup confirmation.

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
never credentials. No Compose, persistent service, cron or port publishing.

## Discovery, artifacts and results

Vision 5.4.9 evidence supports login POST
`/mgmt/system/user/login`, inventory GET
`/mgmt/system/config/itemlist/alldevices`, and supported site/device GETs.
Normal discovery preserves the recursive thin graph and native
`ormId`/`parentOrmId`; these are not aliased to lookup `ormID`.
Unique valid management IPs receive device-detail GETs. Unknown nonsecret fields
are preserved; passwords, usernames, communities and tokens are null/redacted.

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
    summary.json
```

Only selected module directories appear. Artifacts include source name/version,
timestamp, native identifiers and document evidence. Access object example:
`{"ormID": "device-1", "deviceAccess": {"cliPassword": null}}`.
Redaction counts describe processing of the underlying response.

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

Unsupported: complete Physical/Organization tree enumeration, restorable
credential backup, LDAP and Scheduler collection, live CC backup, appliance
configuration downloads and all configuration writes. Evidence gaps remain
documented internally rather than advertised as working modules.
Authentication is cleared locally; remote logout/renewal is not implemented.
Connect/read timeouts are 10s/30s, checked per-request deadline 60s and response
budget 16 MiB. DNS and whole-run execution are not hard-deadline bounded.
No redirects, automatic renewal or request retries.

Offline test evidence and exact limitations are recorded in
[PROGRESS.md](docs/PROGRESS.md). Updated Linux/Docker/live behavior still requires
owner-supervised validation; previous deployed-image results do not qualify
these changes. No live controller calls, Git operations or deployment were
performed during implementation.

## Owner-reviewed publication commands

Instructions only; review branch, all staged content, sensitive tracked files
and history before committing. The following is the exact 12-file change list.
Wrapper, root master, Dockerfile, original legacy scripts and containment
documentation are unchanged.

```sh
git status --short
git branch --show-current
test "$(git branch --show-current)" = feature/ccv-010c-http-safety || exit 1
git ls-files -- '*.pdf' '*.PDF' '*.tar' '*.ini' '*.pem'
# Stop for approved cleanup if sensitive/vendor files are tracked.
git add -- README.md docs/API_MATRIX.md docs/PROGRESS.md \
  examples/vision-backup/profile.json \
  src/cc_vision_import/backup_policy.py \
  src/cc_vision_import/backup_setup.py \
  src/cc_vision_import/master_cli.py \
  src/cc_vision_import/vision_backup.py \
  src/cc_vision_import/transport.py \
  src/cc_vision_import/http_backend.py \
  tests/test_backup_setup.py tests/test_vision_backup.py
git --no-pager diff --cached --check
git --no-pager diff --cached
git commit -m "Simplify Vision backup TLS and operator workflow" \
  -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
git push origin HEAD:feature/ccv-010c-http-safety
```

Do not stage runtime JSON, credentials, controller exports, vendor PDFs or image
TARs. Rebuild the reviewed image and stop before live testing until separately
authorized.

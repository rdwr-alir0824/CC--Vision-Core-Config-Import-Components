# API Evidence and Compatibility Discovery Matrix

Date: 2026-11-18
Evidence levels: source-observed endpoints; separately scoped offline mock
coverage for authentication and three reads. No official/live qualification.

## CCV-009-A - approved targets and evidence boundaries

Discovery date: **2026-11-18**. Scope: static/read-only evidence analysis and
documentation only. This register does not enable clients or certify products.

| Direction | Source target | Destination target | Evidence and compatibility |
| --- | --- | --- | --- |
| A | APSolute Vision 5.4.x | Cyber Controller 10.10.x | Owner-reported target families/testing; exact patch/builds, per-operation results and provenance of that testing not supplied. Unsupported/unverified by this application. |
| B | Cyber Controller 10.10.x | Cyber Controller 10.10.x | Same owner-reported limitation; source and destination builds/roles require independent qualification even within one family. Unsupported/unverified by this application. |

These are approved discovery targets, **not blanket compatibility certifications**.
No inspected legacy script establishes its exact Radware release/build. In the
tables below, a target family must not be read as the version on which that
script was developed or successfully tested. The owner also reports C3 merged
into main; this is owner-reported project context, not independently checked
through Git during this task.

### Evidence classification and provenance register

| Classification | Available evidence | What it does not establish |
| --- | --- | --- |
| L - source-observed legacy behavior | Static source/call-site inspection on 2026-11-18, line references and byte fingerprints below. 22 files, 13 distinct implementations, nine duplicate copies reconfirmed. | Execution success, vendor support, exact version, complete schema or safe migration semantics. |
| O - owner-reported testing | Owner's CCV-009-A authorization dated 2026-11-18 names the two families and directions above, based on reported testing. | Per-operation pass/fail, exact builds, test dates, authorization scope or sanitized test evidence; none supplied. O applies to target selection, not an operation-level qualification. |
| D - official vendor documentation | **None available in the inspected workspace.** No vendor manual, release/API reference, OpenAPI/Swagger specification or approved vendor document revision identified. | No operation is marked officially documented. Existing project Markdown and synthetic JSON are not vendor references. |
| M - synthetic/mock verification | Existing `0.0-test` authentication contracts and three reads, detailed below; accepted offline C3 evidence E-030/E-031: 321 tests passed. | Any 5.4.x/10.10.x endpoint/schema/credential compatibility or complete migration support. Offline object/reconciliation tests are not HTTP qualification of API-04 through API-09. |
| T - separately authorized live laboratory verification | **None performed or supplied for operation-level verification in this discovery.** | The owner's family-level report is not promoted to T. No lab activity is authorized here. |

Workspace inventory covered the repository root, project documents, legacy
sources and available document/specification extensions. The JSON files found
are existing test/example inputs. The following references are **missing**:

| Missing reference | Required provenance and coverage |
| --- | --- |
| DOC-V54 | Owner-approved APSolute Vision 5.4.x API/authentication/schema reference and applicable release notes. Exact title, publisher, revision/date, patch/build applicability, section/page and local file location are unknown/not supplied. |
| DOC-CC1010 | Equivalent owner-approved Cyber Controller 10.10.x references, including destination writes and completion/read-back behavior. All exact document/version/revision fields remain unknown/not supplied. |
| CFG-SCHED | Sanitized API-path declarations for `login_endpoint`, `logout_endpoint`, `scheduler_endpoint` from the missing scheduler INI. Supply only path/schema evidence, not AUTH, hosts, credentials or session data. |
| TEST-OWNER | Sanitized operation-level test inventory for the owner-reported families: independent source/destination product/build, operation, role, date, expected/actual result and evidence classification. No credentials or raw operational exports. |

For any later vendor document, record publisher/title, exact applicable release,
revision/publication date, chapter/page/operation identifier, local path and
SHA-256, owner approval and review date. A filename or vendor-looking URL alone
is insufficient provenance. No external documentation was fetched here.

### Legacy source revision fingerprints

The [source keys](#source-references) identify the canonical copies. SHA-256
identifies the inspected local bytes; it is **not a vendor document revision**.
Legacy product versions and original authoring/release dates remain unknown.

| Key | SHA-256 of inspected canonical file |
| --- | --- |
| OD | `fba14dc46be4fced131ac45988eb19218e5a490e007f81f5dfae8bbf8d4b0bd6` |
| OC | `35966f6d130b42dc4c01c8f7aaef866a7e2623f35a8a60302aff86556dea5709` |
| OU | `54716f1cc3923f3ea38bd273e420554398f8518293772cba0e41fb9144449148` |
| LD | `8f060c05751ed5046a7a9f28577e85e9501339f9ea06ff6b288e0c7689f26305` |
| LU | `03259b2919509c221c5b30e55940e23017c9caf330c0e40aebc81012d15c3d52` |
| SD | `ff79af7fa4266410d6d567443066f14cca79c8a42581bbf7aee4c9e528fdf8c7` |
| SU | `7e483919828193e915998633180dc87f85c4e524da6cf47ffd9ace559eca069d` |
| DR | `8cbfa2df67cfd3d183c51b1d87f9b5495515faed6111cc0c64df801ae6bcf077` |

### Product-role operation matrix - request and response evidence

This table and the following table join on **Record**, together supplying all
18 required API-matrix fields. There are **17 product-specific rows for the
existing 16 operation records**: API-01 is separated by product/authentication
behavior, not counted as another method/path pair. Product names describe
legacy intent. `V54 target` means 5.4.x target / legacy version unknown;
`CC1010 target` means 10.10.x target / legacy version unknown.

Authentication profiles A/B/C/D are defined [below](#authentication-profiles-observed).
They record client behavior, not proven server requirements or permissions.
GET rows mean no request body supplied, not a documented prohibition on bodies.

| Record | Product | Product version or version family | Source or destination role | Migration direction | Configuration component | Operation | HTTP method | API path | Request schema evidence | Response schema evidence | Authentication requirements |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| API-01-C | Cyber Controller intent | CC1010 target | Source B; destination A/B | A/B | Session | Login | POST | `/mgmt/system/user/login` | A: Basic session credentials plus JSON-text username/password; required combination unknown | Only HTTP 200 checked; body/session schema unvalidated | Profile A; exact mechanism, RBAC and cookie requirements unknown |
| API-01-V | APSolute Vision intent | V54 target | Source A; legacy Vision destination outside A/B | A; legacy destination out of scope | Session | Login | POST | `/mgmt/system/user/login` | B: JSON username/password; JSON/XMLHttpRequest headers | HTTP success and JSON `status=ok`; cookie schema unknown | Profile B; exact server requirements/privileges unknown |
| API-02 | Cyber Controller intent | CC1010 target | Source B; destination A/B inventory/root | A destination; B both roles | Physical hierarchy | Read tree | GET | `/mgmt/system/config/tree/Physical` | No body; fixed tree selection | `meIdentifier.managedElementID`, recursive `children`; partial consumed fields only | A; tree-read privileges unknown |
| API-03 | Cyber Controller intent | CC1010 target | Source B; destination A/B inventory/root | A destination; B both roles | Organization hierarchy | Read tree | GET | `/mgmt/system/config/tree/Organization` | No body; separate fixed tree selection | Same fields consumed as API-02, not proof of equivalent real schema | A; independent tree permissions unknown |
| API-04 | Cyber Controller intent | CC1010 target | Destination A/B; source-B helper defined but unused | A/B diagnostic lookup only | Site identity | Lookup by name | GET | `/mgmt/system/config/tree/site/byname/{site_name}` | Raw concatenated name; URL encoding absent | OD reads `ormID`; OC/OU accept native managed-element ID or `ormID`; absence inferred from text | A; lookup privileges unknown |
| API-05 | Cyber Controller intent | CC1010 target | Source B | B; no Vision source evidence for A | Site parent | Lookup by ID | GET | `/mgmt/system/config/tree/site/byid/{site_id}` | Raw native-ID path parameter | OD consumes `name`; error schema inferred from response text | A; lookup privileges unknown |
| API-06 | Cyber Controller intent | CC1010 target | Source B; destination read-back is only a candidate | B source; A/B destination candidate | Device detail/access | Lookup by IP | GET | `/mgmt/system/config/tree/device/byip/{device_ip}` | Raw address path parameter; no qualified identity in request | OD consumes `deviceSetup.deviceAccess`, deletes its `ormID`; other detail fields not validated | A; secret visibility and device-read privileges unknown |
| API-07 | Cyber Controller intent | CC1010 target | Destination | A/B | Sites | Create site | POST | `/mgmt/system/config/tree/site` | OC JSON: `parentOrmID`, `name`; partial source payload only | HTTP 200; failure JSON `message` assumed; created-ID/completion schema unknown | A; create privilege unknown; async header present |
| API-08 | Cyber Controller intent | CC1010 target | Destination | A/B | Managed devices/access | Create device | POST | `/mgmt/system/config/tree/device` | OC JSON: `name`, `parentOrmID`, `type`, `deviceSetup.deviceAccess` | HTTP 200; failure `message` assumed; destination ID/completion unknown | A; create/access privileges unknown; async header present |
| API-09 | Cyber Controller intent | CC1010 target | Destination | A/B | Managed devices/access | Update device | PUT | `/mgmt/system/config/tree/device` | OU: API-08 fields plus exported device `id` assigned as `ormID` | HTTP 200; failure `message` assumed; update semantics/completion unknown | A; update/access privileges unknown; async header present |
| API-10 | APSolute Vision intent | V54 target | Source A; legacy Vision destination lookup outside A/B | A source; no CC source evidence for B | LDAP permissions | List entries | GET | `/mgmt/system/config/itemlist/ldapobjectpermission` | No body; pagination/filter parameters not observed | LD saves JSON; LU assumes array entries with `attributeValue`; complete schema unknown | B; LDAP-read privileges unknown |
| API-11 | APSolute Vision intent | V54 target | Legacy Vision destination only | Outside approved A/B; CC equivalent missing | LDAP permissions | Create entry | POST | `/mgmt/system/config/itemlist/ldapobjectpermission` | LU selects objectClassName/attributeName/attributeValue, networkPolicies, roleGroupPairList; forces requireDeviceLock | 200/201; error text triggers optional scope-broadening retry; no read-back | B; permission-write and scope authorization unknown |
| API-12 | Auxiliary local document service; Radware ownership unknown | Unknown; no approved target family applies | Auxiliary destination, excluded | Outside A/B | Search documents | Restore individual document | PUT | `/{index}/_doc/{document_id}` | DR sends each hit's `_source`; index/ID from input | Raises on HTTP error, prints parsed JSON; semantic result unvalidated | D; no authentication configured, not proof unauthenticated access is supported |
| CFG-01 | APSolute Vision intent | V54 target | Source A; legacy Vision destination outside A/B | A source; B not evidenced | Session | Configured login | POST | `<API.login_endpoint>` - unresolved, not a literal endpoint | C: JSON username/password; host/port/path from missing INI | `status=ok`; `jsessionid` read for printing; real cookie/token contract unknown | C; exact login and permissions unverified |
| CFG-02 | APSolute Vision intent | V54 target | Source A; legacy Vision destination outside A/B | A source; B not evidenced | Session | Configured logout | POST | `<API.logout_endpoint>` - unresolved | No body supplied; existing session | Response/status ignored, exceptions swallowed | C; logout/session invalidation contract unknown |
| CFG-03 | APSolute Vision intent | V54 target | Source A; legacy Vision destination duplicate lookup | A source; no CC source/destination evidence | Scheduled operations | List/export tasks | GET | `<API.scheduler_endpoint>` - unresolved | No body; no pagination parameters observed | SD saves JSON; SU expects list/dict `name`, otherwise returns empty set | C; scheduler-read privileges unknown |
| CFG-04 | APSolute Vision intent | V54 target | Legacy Vision destination only | Outside approved A/B; CC equivalent missing | Scheduled operations | Create task | POST | `<API.scheduler_endpoint>` - unresolved | Input task minus `ormID`, `taskStatus`, `jobstatus`, `previousFeedMd5`; no type schema | HTTP 200/201 only; activation/result/read-back unknown | C; task-create/activation privileges unknown |

### Product-role operation matrix - qualification and safety

Every `official: none` below means document title/revision/build applicability
were not supplied, not that the vendor has no documentation. Line references
plus the source fingerprints above are the exact available revision provenance.
`O(target only)` never attests a row passed on a target release.
All rows remain **unsupported/unverified for the real targets**; the auxiliary
row is additionally excluded. No production capability is added.

| Record | Dependencies | Read/write classification | Documentation source and revision | Evidence classification | Compatibility status | Validation gaps | Safety considerations |
| --- | --- | --- | --- | --- | --- | --- | --- |
| API-01-C | Independent source/destination profiles; approved CA and session lifecycle | Authentication/session state change | OD 54-85; OC/OU 52-84; fingerprints above; official: none | L + O(target only) + M(`0.0-test` auth) | Unsupported/unverified CC1010 | Mechanism, false-positive HTTP 200, cookies/CSRF, expiry/logout, RBAC, exact build | Never copy disabled TLS, missing timeouts or prematurely closed session; no secret logging |
| API-01-V | Source profile; approved CA/session lifecycle | Authentication/session state change | LD 16-23; LU 13-20; fingerprints; official: none | L + O(target only) + M(`0.0-test` auth) | Unsupported/unverified V54 | Cookie/CSRF/expiry/logout/RBAC, exact build; not equivalent to CC login | Redact credentials/session bodies; never reuse roles/sessions across products |
| API-02 | API-01-C; explicit Physical root/context | Configuration read | OD 180-216; OC/OU 143-150; fingerprints; official: none | L + O(target only) + M(`0.0-test` read) | Unsupported/unverified CC1010 | Completeness/pagination, native root class, stable IDs, unknown node types | Root must exist; preserve unknown fields/order; no Vision inference |
| API-03 | API-01-C; explicit Organization root/context | Configuration read | OD 180-216; OC/OU 143-150; fingerprints; official: none | L + O(target only) + M(`0.0-test` read) | Unsupported/unverified CC1010 | Per-tree schema/authorization, shared-device identity, completeness | Keep trees distinct; no cross-tree merge or guessed parents |
| API-04 | API-01-C; qualified tree/parent context not established by legacy request | Configuration read | OD 88-96; OC/OU 86-120; fingerprints; official: none | L + O(target only) | Unsupported/unverified CC1010 | Duplicate-name multiplicity, tree scoping, encoding, absence/error schema | Never establish identity by name or fall back to root |
| API-05 | API-01-C; independently qualified source site ID | Configuration read | OD 99-107, 124-126; fingerprint; official: none | L + O(target only) | Unsupported/unverified CC1010 | ID alias/scope/lifetime, root lookup response, authorization/errors | Native IDs are provenance, not portable destination IDs; encode parameters |
| API-06 | API-01-C; tree device plus explicit qualified association | Sensitive configuration read | OD 145-157, 195-197; fingerprint; official: none | L + O(target only) | Unsupported/unverified CC1010 | Address ambiguity, detail IDs/type, access schema/ID ownership, masking, completeness | No IP-only matching, first-match merge, field deletion or raw credential retention; bound acknowledgement still required |
| API-07 | Destination root and parent mappings; complete destination evidence; approved semantics | Configuration write | OC 152-175; fingerprint; official: none | L + O(target only) | Unsupported/unverified CC1010 | Allowed fields/classes, duplicate behavior, created IDs, async completion/idempotency | No root CREATE, root fallback, automatic replay or writes authorized by an offline plan |
| API-08 | API-07 dependency order; destination type support; qualified mapping/access policy | Configuration write | OC 177-202; fingerprint; official: none | L + O(target only) | Unsupported/unverified CC1010 | Required fields, credentials, type translation, locks/ownership, completion | No silent field loss/defaults, unresolved secrets, source-ID reuse or unapproved apply |
| API-09 | Existing destination device and independent ID; parent/access mappings | Configuration write | OU 152-184; fingerprint; official: none | L + O(target only) | Unsupported/unverified CC1010 | PUT replace/merge semantics, mutable fields, async completion, read-back | Never reuse source `ormID`; no uncertain-outcome replay; update planner/executor not implemented |
| API-10 | API-01-V; source LDAP semantics; destination CC reference evidence missing | Sensitive authorization-configuration read | LD 17-29; LU 14-24; fingerprints; official: none | L + O(target only) + M(`0.0-test` read) | Unsupported/unverified V54 | Full list/error/pagination schema; roles/scopes/policies; CC equivalent | Attribute-value equality is not permission equivalence; no CC endpoint/schema copying |
| API-11 | Vision auth; role/group/network-policy resolution; CC target API missing | Authorization configuration write | LU 28-39; fingerprint; official: none | L + O(target only) | Unsupported/unverified V54; outside A/B destination | CC target path/payload, scope mapping, lock semantics, verification | Never broaden to all-scope, force device locks or repeat unsafe write retry |
| API-12 | Independent service/index ownership and restore authorization, neither supplied | Auxiliary data write | DR 8-11; fingerprint; official: none | L only | Excluded; service/version unknown | Product ownership, schema/index compatibility, transport/authentication, restore safety | Not a product configuration backup/restore API; no integration or execution authorized |
| CFG-01 | Sanitized path evidence, host/port declaration, approved CA/session | Authentication/session state change | SD 23-26, 41-70; SU 23-26, 46-75; fingerprints; official: none | L + O(target only) | Unsupported/unverified V54; path unresolved | Cannot assert API-01 alias; exact auth/result/RBAC unknown | Never print session IDs or raw login failure bodies |
| CFG-02 | CFG-01; literal logout path and invalidation semantics | Authentication/session state change | SD 28-31, 73-81; SU 28-31, 78-86; fingerprints; official: none | L + O(target only) | Unsupported/unverified V54; path unresolved | Logout success/expiry/error schema; CC logout not established | Report failures safely; do not infer a conventional logout URL |
| CFG-03 | CFG-01; literal task path and task-type inventory | Configuration read | SD 33-36, 84-117; SU 33-36, 89-108; fingerprints; official: none | L + O(target only) | Unsupported/unverified V54; path unresolved | Pagination/full task schemas, CC equivalents, IDs/timezones/dependencies | Unexpected schema is an error, not empty inventory; name alone cannot establish equivalence |
| CFG-04 | CFG-03; mapped device/site/policy references; explicit activation/timezone policy | Configuration write; may schedule later execution | SU 111-123, 157-197; fingerprint; official: none | L + O(target only) | Unsupported/unverified V54; outside A/B destination | Literal path, CC payloads, required/server-owned fields, activation and completion | No blindly dropped fields, immediate task activation or production execution |

### Direction-specific coverage and unsupported edges

| Component | A: Vision 5.4.x to CC 10.10.x | B: CC 10.10.x to CC 10.10.x |
| --- | --- | --- |
| Sessions | Vision and CC login code observed separately; neither real version qualified. Vision logout is unresolved; CC logout not observed. | CC login intent observed; both builds/roles, expiry and logout unverified. |
| Physical/Organization export | **Vision tree/export endpoints and schemas not established.** CC API-02/API-03 are only destination inventory candidates. | API-02/API-03 source and destination candidates; no real completeness/identity qualification. |
| Site/device create/update | CC API-07/API-08/API-09 destination candidates; Vision-to-CC type/field/identity transformations unestablished. | Same CC destination candidates; native IDs must still be independently mapped and patch-level differences qualified. |
| Device detail/access | Vision source detail/access API missing; CC API-06 alone cannot bridge A. | API-06 source-observed; standalone access endpoint not established. Qualified association and credential portability remain gates. |
| LDAP | Vision API-10 source observed; CC source/reference/create/read-back equivalents missing. API-11 is Vision-destination evidence only. | CC LDAP read/write/reference APIs and schemas not established at all by these scripts. |
| Scheduler | Vision source CFG-03 path unresolved; no CC target task APIs/types established. | CC scheduler APIs/types not established. Vision configurable paths cannot be reused as CC evidence. |
| Backup/export/other management | JSON object/task/LDAP exports are partial exports, not full product backups. Additional documented management/backup APIs unknown because vendor references are absent. | Same boundary; API-12 document restore and shell Docker/cron operations remain excluded. |

Manual automation opportunities and prioritized evidence/lab questions are
tracked in the [CCV-009 roadmap register](ROADMAP.md#ccv-009---api-discovery-and-automation-expansion).
No additional endpoint, product schema or supported version is asserted.

## Counting and evidence rules

**16 operation records** are catalogued:

- **12 concrete unique HTTP method/path-template pairs**, across 10 path templates.
  Eleven are management API operations and one is an auxiliary document-store
  operation outside the proposed initial application scope.
- **Four configuration-resolved scheduler operation references** whose literal
  paths are unavailable. These are not four proven additional unique endpoints:
  the configured login might overlap an already observed path.
- Byte-identical scripts, repeated calls, retry branches, products, and trees'
  repeated call sites are not counted again. Physical and Organization are two
  concrete source-selected paths, not an unrestricted `{tree_type}` capability.

Every row is **source-observed**. For every row: official documentation **not
reviewed**, live testing **not performed**, and real supported versions
**unknown**. Mock coverage exists only where explicitly recorded below; all
other records remain mock-untested. Script labels suggest product intent; they
do not certify compatibility. No official endpoint, logout path, polling path,
or capability is inferred from convention.

## Source references

Line references refer to canonical inspected copies; the [inventory](PROJECT.md#script-inventory)
lists identical copies.

| Key | Source |
| --- | --- |
| OD | [Object downloader](../legacy/app/download_cybercontroller_objects.py) |
| OC | [Object creator](../legacy/app/upload_cybercontroller_objects.py) |
| OU | [Object updater](../legacy/app/update_cybercontroller_objects.py) |
| LD | [LDAP downloader](../legacy/download_ldap_permissions%20%281%29.py) |
| LU | [LDAP uploader](../legacy/upload_ldap_permissions%20%281%29.py) |
| SD | [Scheduler downloader](../legacy/download_scheduler.py) |
| SU | [Scheduler uploader](../legacy/upload_scheduler.py) |
| DR | [Document restore](../legacy/AMS-alerts/restore_cfg.py) |

## Authentication profiles observed

| Profile | Source behavior | Limitations |
| --- | --- | --- |
| A - object scripts | HTTPS session; `session.auth` Basic credentials plus JSON-text login body; session carries subsequent state. Login accepts HTTP 200. | TLS verification disabled; no timeout; session context exited before login/use; no explicit logout; exact required auth mechanism unconfirmed. |
| B - LDAP scripts | HTTPS session; JSON username/password login; JSON and XMLHttpRequest headers; HTTP success plus body `status == "ok"`. | TLS controlled by missing INI; warnings suppressed; no timeout or explicit logout. |
| C - scheduler scripts | HTTPS host/port and paths from INI; JSON login, same header style and `status == "ok"` check; session followed by attempted logout. | Literal paths unknown; logs session identifier; configurable TLS; no timeout; logout errors swallowed and status unchecked. |
| D - document restore | Plain HTTP to local document service on port 9200; JSON content header; no authentication configured in source. | No transport security or timeout; not evidence that unauthenticated access is supported or appropriate. |

Session-cookie behavior is implied by use of `requests.Session`; cookie names and
server session semantics are not verified. No credential, cookie, host address,
or operational payload values are reproduced here.

## Concrete method/path operations

All management paths are relative to the selected HTTPS controller base URL.
Document-store path is relative to the local HTTP service, not a Vision/CC URL.

| ID | Method | Path template | Functions / source location | Intended product; auth | Operation and observed limitations |
| --- | --- | --- | --- | --- | --- |
| API-01 | POST | `/mgmt/system/user/login` | `login_cyber_controller` (OD 54-85, OC 52-84, OU 52-84); module-level LD 16-23, LU 13-20 | Cyber Controller-labeled objects: A; Vision-labeled LDAP: B | Authenticate. Body/status checks differ; not proof of shared cross-product behavior. |
| API-02 | GET | `/mgmt/system/config/tree/Physical` | OD `main` 180-185, invocation 212-213; OC/OU `upload_configuration` 143-150 | Cyber Controller intent; A | Export tree or obtain destination root ID. Assumes children and `meIdentifier` response shape. |
| API-03 | GET | `/mgmt/system/config/tree/Organization` | OD `main` 180-185, invocation 215-216; OC/OU `upload_configuration` 143-150 | Cyber Controller intent; A | Same tree/read-root flow for Organization. No proof arbitrary tree names work. |
| API-04 | GET | `/mgmt/system/config/tree/site/byname/{site_name}` | OD `get_parent_site_id` 88-96; OC/OU `get_parent_site_id` 86-120 | Cyber Controller intent; A | Resolve parent ID. OD helper is defined but not used in downloader main flow; OC/OU call it. Names concatenated without URL encoding; missing/error cases collapse to false; duplicate-name behavior unknown. |
| API-05 | GET | `/mgmt/system/config/tree/site/byid/{site_id}` | OD `get_parent_site_name` 99-107 | Cyber Controller intent; A | Resolve parent name while extracting sites. Expects `name`; response-text error matching rather than validated error schema. |
| API-06 | GET | `/mgmt/system/config/tree/device/byip/{device_ip}` | OD `extract_device_access_data` 145-157 | Cyber Controller intent; A | Read `deviceSetup.deviceAccess`, remove nested `ormID`, merge into export. Field presence and secret portability assumed. |
| API-07 | POST | `/mgmt/system/config/tree/site` | OC `upload_configuration` 152-175 | Cyber Controller intent; A | Create site with name and parent ID. Missing parent falls back to root; only HTTP 200 is considered success. |
| API-08 | POST | `/mgmt/system/config/tree/device` | OC `upload_configuration` 177-202 | Cyber Controller intent; A | Create device with name, parent, type, and device access. Only HTTP 200 checked; async header present without completion verification. |
| API-09 | PUT | `/mgmt/system/config/tree/device` | OU `upload_configuration` 152-184 | Cyber Controller intent; A | Update device including exported `ormID`. Source-ID reuse unsafe across destinations; async completion unverified. |
| API-10 | GET | `/mgmt/system/config/itemlist/ldapobjectpermission` | LD module-level 17-29; LU module-level 14-24 | Vision intent; B | Export entries or collect existing `attributeValue` values. Assumes list shape; no pagination handling observed. |
| API-11 | POST | `/mgmt/system/config/itemlist/ldapobjectpermission` | LU module-level 28-39 | Vision intent; B | Create selected permission fields; considers 200/201 success. Forces device lock; optional all-scope retry defaults enabled. Retry is the same API operation, not another endpoint. |
| API-12 | PUT | `/{index}/_doc/{document_id}` | DR module-level 8-11 | Local document service, product ownership unknown; D | Write each `_source` from `hits.hits` using `_index` and `_id`. Raises for HTTP error; no target checks or semantic verification. Outside initial migration scope. |

## Unresolved scheduler operation references

Paths are taken from the absent `config.ini` API section. Angle-bracket notation
below denotes a configuration reference, **not an API endpoint**.

| ID | Method | Unresolved path source | Functions / source location | Intended product; auth | Operation and limitations |
| --- | --- | --- | --- | --- | --- |
| CFG-01 | POST | `<API.login_endpoint>` | SD `vision_login` 41-70; SU `vision_login` 46-75; URLs 23-26 | Vision intent; C | Login. Cannot assert it equals API-01. |
| CFG-02 | POST | `<API.logout_endpoint>` | SD `vision_logout` 73-81; SU `vision_logout` 78-86; URLs 28-31 | Vision intent; C | Attempt logout in `finally`; exceptions suppressed and response unchecked. |
| CFG-03 | GET | `<API.scheduler_endpoint>` | SD `main` 84-117; SU `get_existing_tasks` 89-108; URLs 33-36 | Vision intent; C | Export tasks or enumerate names for skipping. Unexpected list shape returns an empty set on import; no pagination observed. |
| CFG-04 | POST | `<API.scheduler_endpoint>` | SU `main` 157-197; `sanitize_task` 111-123 | Vision intent; C | Create tasks after dropping four selected fields. Accepts 200/201; no schema, activation, timezone, reference mapping, or read-back verification. |

## Capability and verification gaps

- No DELETE operations or concrete logout/polling/version-discovery endpoints
  were found. No site update, LDAP update/delete, or scheduler update/delete
  capability is established.
- Offline credential transformation and shell helpers add no HTTP operations.
- Shared URL prefixes are not evidence of equivalent Vision/CC schemas.
- JSON parse success and HTTP acceptance do not establish completed migration.
- Official compatibility, pagination, rate limits, idempotency, async status,
  permission requirements, error schemas, and secrets behavior remain unknown.

## Implemented offline mock coverage - CCV-003-A/B/C

The owner approved an explicitly synthetic **`0.0-test`** marker for C's client
capability declarations. It is not a vendor release or supported-version claim.
Every other version and unknown/cross-product capability is rejected by these
clients. Scheduler references remain unavailable; no arbitrary tree operation
is exposed.

### Enforced synthetic-only boundary

- `0.0-test` is reserved for mocked development/testing, never a supported
  Vision or Cyber Controller release.
- Synthetic declarations live separately in
  [mock_capabilities.py](../src/cc_vision_import/mock_capabilities.py).
  [capabilities.py](../src/cc_vision_import/capabilities.py) has an empty
  `VERIFIED_CAPABILITIES` catalogue. Default lookup uses that production
  catalogue only, with no synthetic fallback. It rejects `0.0-test` even if a
  synthetic entry is mistakenly placed there.
- Explicit `mock_only=True` selects mock metadata only; it is not permission
  to perform IO. Clients additionally require an injected backend explicitly
  implementing the nominal
  [MockSessionBackend](../src/cc_vision_import/sessions.py) contract, checked
  at construction and before every read. A general injected backend or an
  `is_mock` attribute is insufficient.
- The mock workflow enforces `SessionManager(..., mock_only=True)` for both
  roles: a non-mock factory result is rejected and locally cleaned up before
  that role resolves credentials or sends authentication/API requests.
- No real version is enabled in either catalogue. A future real HTTP adapter
  implementing only the normal backend protocol receives no synthetic
  permissions. It must never implement/register as `MockSessionBackend`.
  Future production capabilities require separately approved evidence and
  explicit implementation; mock entries must not be copied into production.
- The nominal mock declaration is a trusted developer assertion, not a sandbox
  or proof of arbitrary injected code's behavior. Only in-memory fakes belong
  behind it. No concrete HTTP backend is implemented.

Boundary regressions and full-suite evidence are recorded in
[E-011](PROGRESS.md#e-011---ccv-003-c-synthetic-backend-boundary-2026-11-17).

| Record | Implemented mock behavior | Evidence and limits |
| --- | --- | --- |
| API-01 | B's distinct Vision JSON-status and Cyber Controller HTTP-200-only strategies; independent managed roles and local cleanup | Authentication/session tests and C integration tests. No cookie/token/server-TTL schema, remote logout, renewal, or genuine authentication qualification. Controller HTTP-200-only evidence remains deliberately weak. |
| API-02 | `CyberControllerClient.export_physical_tree()`; GET through injected managed transport | Client and read-to-plan integration mocks only. Synthetic minimum tree shape: object with nonblank `meIdentifier.managedElementID` and recursive `children` object array; depth bounded to 64. No portable site/device transformation or completeness claim. |
| API-03 | `CyberControllerClient.export_organization_tree()`; separate explicit operation | Same synthetic minimum shape as the Physical mock, not proof both real schemas are equivalent. Independently asserted exact path and integration case. |
| API-10 | `VisionClient.list_ldap_permissions()` | Mock array of opaque objects; empty list permitted. No field semantics, pagination, permission changes, or LDAP migration implementation. |

Tests: [authentication/session](../tests/test_authentication.py),
[clients](../tests/test_product_clients.py), and
[mocked integration](../tests/test_mocked_integration.py).
Mock declarations are in [mock_capabilities.py](../src/cc_vision_import/mock_capabilities.py);
production/default lookup is in [capabilities.py](../src/cc_vision_import/capabilities.py).
Full command/results and zero guarded attempts are recorded in
[E-010](PROGRESS.md#e-010---ccv-003-c-mocked-client-and-integration-verification-2026-11-17).
Evidence classifications remain separate: **source-observed + mock-tested does
not mean officially documented, live-tested, or compatible**. The baseline
endpoint counts and supported real versions have not changed.

## Source object structures and offline schema coverage - CCV-004-A

Static source evidence is extended here, **not upgraded to official or live
verification**. Endpoint counts remain 16 records / 12 concrete operations;
no client operation or supported real product/version is added.

| Source | Observed structure/behavior | New offline handling; unresolved evidence |
| --- | --- | --- |
| OD `extract_sites_and_devices`, 110-142 | `children`; exact managed-element Site/Device classes; ID in `meIdentifier.managedElementID`; flat sites/devices with `parentOrmID`, site parent name, device type/address | Synthetic typed roots/sites/devices, explicit controller/tree references, and strict hierarchy validation. Native root class and complete real schemas remain unknown. Unknown classes fail, unknown JSON fields are preserved. |
| OD `extract_device_access_data`, 145-163 | Separate API-06 result `deviceSetup.deviceAccess` merged by address; access `ormID` deleted | No API-06 client or enrichment added. Preserve supplied access configuration/`ormID` as source provenance, distinguish access location/absence/null, reject conflicting locations. Portability and reference semantics remain unresolved. |
| OC `get_parent_site_id`, 86-120; upload 143-202 | Parent name lookup accepts managed-element ID or `ormID`; failed parent lookup may fall back to tree root | No name lookup/root fallback. Every normalized root/site/device needs explicit qualified mapping against a separate supplied destination inventory and matching parent dependency. Alias equivalence is not assumed. |
| OU upload 152-184 | Device update reuses exported device ID as `ormID` | No update implementation. Destination ID must independently exist under the supplied destination context; equal source/destination ID strings alone establish nothing. |
| [Credential transformer](../legacy/app/update_json_credentials.py), 47-134 | CLI/HTTP/HTTPS usernames/passwords and `snmpV3Username`, `snmpV3AuthenticationPassword`, `snmpV3PrivacyPassword` | Field names inspected only; raw values rejected by normalized artifact validation, null/reference values permitted. No credential lookup, replacement, migration, or transformer execution. |

[Controller-object tests](../tests/test_controller_objects.py) cover two synthetic
tree fixtures and derived simple, nested, duplicate-name, missing-parent, cyclic,
conflicting-reference, and ambiguous-destination cases. This is local schema/
mapping coverage, **not mocked or live coverage for API-04 through API-09**.
Under the owner's Option 1 clarification, duplicate names do not reject exports:
all distinct-ID objects/configuration survive artifact round-trips. Same-type
sibling collisions are reported separately as identity ambiguity; equal names
under different parents/trees or across object types are not such collisions.
Explicit controller/tree/type/stable-ID mappings to independently supplied
destination records may resolve ambiguous objects. Names alone and automatic
source-ID reuse never resolve targets; unresolved/ambiguous mapping decisions
remain blocked. This offline policy is not evidence of real product duplicate-name
semantics or support.
The existing three mock read clients and production/default-deny catalogue are
unchanged. Domain artifact version syntax is a declaration, not product support;
`0.0-test` remains a mocked-development marker, never a real supported release.
No future real HTTP adapter gains permissions from these offline contracts.
Initial evidence is in
[E-013](PROGRESS.md#e-013---ccv-004-a-offline-object-and-mapping-verification-2026-11-17);
the superseding name-policy evidence/results are in
[E-014](PROGRESS.md#e-014---ccv-004-a-option-1-duplicate-name-clarification-2026-11-17).

## Legacy representation adapters - CCV-004-C1

Read-only reinspection of OD/OC/OU adds these representation-loss/context
observations, not new endpoints or official/live verification:

| Static evidence | Confirmed source observation | C1 offline handling / limits |
| --- | --- | --- |
| OD `extract_sites_and_devices`, 110-142, and `main`, 189-222 | Recursive tree becomes flat `sites`/`devices`; selected name/type/address/id/parent fields retained, original root omitted, other configuration omitted | Recursive adapter preserves supplied unknown configuration. Flat adapter requires explicit source-root response and tree; it cannot recover discarded fields or infer roots from names. |
| OD `extract_device_access_data`, 145-163 | Separate detail response's `deviceSetup.deviceAccess` attached as flat `deviceAccess`; source access `ormID` deleted and devices joined by IP | Preserve supplied embedded access and any access ID without deletion. No API-06 capability/client or by-IP join added. Missing/null/empty access yields invalid preserved artifact; all reported completeness remains unverified. |
| OC upload and OU update | Name-based parent resolution, root fallback, source ID reused on updates | Neither unsafe behavior is inherited. Flat `parentOrmID` must resolve to a supplied same-tree source object/root; explicit independent destination mappings are still mandatory. |

[Adapters](../src/cc_vision_import/controller_exports.py) consume supplied JSON
objects or existing mock-client read results for API-02/API-03. Both operations
retain their prior capability declarations and synthetic schema classifications.
The adapter version gate is `0.0-test` only, not a real supported release.
No Vision schema support is inferred. No product/version or API count changes:
production remains default-deny; 16 records / 12 concrete operations remain the
static baseline. API-06 is still source-observed only, not client-implemented.

The flat root-only context, detailed typed fields, structural-access minimum,
and response fixtures are explicit local/synthetic contracts, not vendor
requirements. In particular, nonempty access does not prove complete access
configuration. Local adapter/mock integration coverage is recorded separately in
[E-020](PROGRESS.md#e-020---ccv-004-c1-offline-export-adapters-2026-11-18);
none of it establishes live compatibility.

## Device-detail reconciliation evidence - CCV-004-C2

Read-only reinspection of OD `extract_sites_and_devices` (110-142),
`extract_device_access_data` (145-163), and `main` (180-202) confirms:

- Native tree device IDs come from `meIdentifier.managedElementID`; `type`
  and `managementIp` are selected from tree nodes, and containment supplies
  `parentOrmID`.
- The existing API-06 by-IP request is followed by extraction of
  `deviceSetup.deviceAccess`. The script deletes access `ormID`, joins by
  `managementIp`, updates the first match, and stops.
- It does **not** inspect detail-response native device ID, type, class, other
  attributes, or controller/tree provenance. It proves neither address
  uniqueness nor a relationship between access `ormID` and tree device ID.

These are refinements of existing source evidence, not additional endpoints.
The [C2 reconciler](../src/cc_vision_import/controller_reconciliation.py)
accepts supplied synthetic data with explicit qualified associations; it does
not implement API-06 or copy the by-IP merge/deletion behavior. Detail aliases,
record envelopes, independent access payloads, and per-device evidence references
are local offline contracts, not documented vendor schemas.
Unknown attributes/access IDs are preserved. Recognized credential material
must use existing safe contracts, and unresolved/masked/null credential values
block eligibility. An evidence reference acknowledges offline reconciliation;
it does not certify complete access or credential portability.

Mock coverage: 27 new reconciliation tests; 271 total offline tests passed,
zero guarded network attempts; see
[E-022](PROGRESS.md#e-022---ccv-004-c2-offline-device-reconciliation-2026-11-18).
API-06 remains source-observed only at the HTTP/schema compatibility level:
no client/backend, official documentation review, live testing, real
product/version capability, or Vision support is added. Operation counts
remain 16 records / 12 concrete operations; production stays default-deny.

## Evidence needed next

1. Target families/directions are now owner-approved for CCV-009-A discovery.
   Obtain exact source/destination patch/builds and operation-level provenance
   for the owner-reported testing; do not call the families certified.
2. Obtain approved version-specific vendor references; record title, version,
   section/link, and what each reference establishes.
3. Supply sanitized scheduler API path configuration and representative synthetic
   or sanitized response schemas. Never supply credentials or live exports here.
4. Extend scoped mock contracts only after separate authorization/evidence;
   current authentication/read mock coverage is recorded above.
5. Only under separate authorization, record lab tests with product/version,
   operation ID, date, expected/actual result, and sanitized evidence location.

Preserve separate source-observed, officially documented, mock-tested, and
live-tested statuses when this matrix evolves.

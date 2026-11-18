# Legacy API Evidence Matrix

Date: 2026-11-18
Evidence levels: source-observed endpoints; separately scoped offline mock
coverage for authentication and three reads. No official/live qualification.

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

1. Approve target products, source/destination versions, and migration directions.
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

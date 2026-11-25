# API Evidence and Compatibility Discovery Matrix

Date: 2026-11-18
Evidence levels: source-observed endpoints; separately scoped offline mock
coverage for authentication and three reads; owner-provided vendor PDF evidence
for selected exact method/path pairs; E-036 synthetic offline subset regressions.
Runtime compatibility remains unverified.

## Vision supported read-only backup - 2026-11-24

Current implementation overlay; historical evidence/acceptance below is unchanged.
The owner authorized `backup-vision`, then documented managed-device discovery
and selected supported modules; advanced profile-listed targets remain supported. No live
controller access or deployment is authorized by this implementation record.

| Operation | Existing evidence | Current implementation | Verification |
| --- | --- | --- | --- |
| POST `/mgmt/system/user/login` | API-01-V; Vision PDF 156-158; legacy LDAP login | Existing login JSON/session strategy plus required `status: ok` and validated `jsessionid` sent as `Cookie: JSESSIONID=...` | Mock tested; not live tested |
| GET `/mgmt/system/config/itemlist/alldevices` | Separate `VISION-MANAGED-DEVICES` evidence; Vision PDF 119-120, recursive ThinSiteTransformerDTO 263 | Preserve native `ormId`/`parentOrmId` and unknown fields, deduplicate valid management IPs for detail reads; optional strings/booleans/children validated | Mock tested; pagination, empty sites/all trees and complete inventory unverified |
| GET `/mgmt/system/config/tree/site/byname/{name}` | API-04; Vision PDF 141; SitePojo 255 | Explicit profile site names only; matching response name; documented model subset, unknown fields retained | Mock tested; not live tested |
| GET `/mgmt/system/config/tree/site/byid/{id}` | API-05; Vision PDF 146; SitePojo 255 | Explicit native source IDs only; matching response `ormID` | Mock tested; not live tested |
| GET `/mgmt/system/config/tree/device/byip/{ip}` | API-06; Vision PDF 143-144; Device 219-220, DeviceSetup 224, DeviceAccess 220-222 | Discovered or explicit managed-device IPs; identity/document subset checks; optional separate device-access artifacts; credentials redacted | Mock tested; query binding, access completeness/portability and live compatibility unverified |

Implementation: [backup orchestration](../src/cc_vision_import/vision_backup.py),
[document-bound client](../src/cc_vision_import/product_clients.py), existing
authentication/session/HTTP components, and [master selector](../src/cc_vision_import/master_cli.py).
No `VERIFIED_CAPABILITIES` entries were added; default clients remain mock-only.
Only the selected workflow creates a live-opt-in backend with an exact origin,
login POST and finite selected/discovered GET allowlist. System trust verification
defaults true; optional custom CA. Unverified TLS requires an isolated Vision
lab transport plus explicit backend/request permission and warning; unrelated
operations remain strictly verified. Owner-approved transport limitation:
existing socket timeouts/checked per-request deadlines do not hard-bound DNS or
whole-run execution. Default backend dispatch remains blocked.

Output is explicitly supported-scope, credential-redacted, completeness-unverified
inventory and not a complete configuration backup or migration input. No full tree
enumeration, LDAP/Scheduler API binding, configuration write, import, delete,
async follow-up, retry, authentication renewal or remote logout was added.
Login session state is cleared locally; server expiry is not verified.
AMS-alerts naming variants are explicitly excluded, never backlog modules.
Unsupported module selections fail before access. Evidence: 238 targeted offline
guarded tests passed across launcher, backup and directly related existing
client/session/backend/transport/workflow/schema modules; zero guarded network
attempts. Linux permissions, live RBAC/cookie behavior, installed-build
compatibility, and the updated Docker image remain unverified.

## CCV-009-B - implemented offline subsets - E-036

The independent E-035 technical review recommended **Evidence accepted; proceed
with bounded offline tests**. The owner then authorized this implementation,
not milestone acceptance. E-035 below remains the vendor-document checkpoint;
E-034 and the original source inventory remain historical.

[Offline qualification](../src/cc_vision_import/schema_qualification.py) reuses
the existing strict JSON reader, artifact envelope, structured validation errors,
controller credential safeguards and supplied `HttpResponse` values. It adds
no CLI operation, client, transport adapter, capability, mapping or executor.
The existing planner explicitly rejects the new evidence-only artifact domain,
both when constructing a plan and when parsing a supplied plan.
[Permanent synthetic tests](../tests/test_schema_qualification.py) cover only
the bounded contracts below.

### Exact evidence bindings

| Reference passed to the offline API | Product/version | Document scope |
| --- | --- | --- |
| `DOC-V549` | `vision` / `5.4.9` | V bytes, title/date/hash and pages recorded below. |
| `DOC-CC10107` | `cyber-controller` / `10.10.7` | C's **10.10.7-labelled content**, not unambiguous runtime applicability. Every qualification retains the 10.10.6 metadata discrepancy. |

`require_document` rejects other versions/products, mismatched references,
adjacent patches, family wildcards and `0.0-test`. These bindings do not enable
5.4.x, 10.10.x or 10.10.6 support. They are a reviewed static evidence catalogue:
the APIs do not reopen/authenticate the PDFs or discover/verify installed builds.
Both local SHA-256 values were independently rechecked for E-036 and agree with
E-035. Document provenance and runtime compatibility remain separate.

`operation_evidence` exposes method/path/classification/page facts for all
12 existing pairs, plus separate API-01-V/API-01-C records, independently per
document: **5 documented / 7 not-found in each**. Not-found does not mean product
non-support. All four CFG references return **unresolved-binding**, with no bound
path. CFG-01/CFG-02 have explicitly named login/logout **candidate** paths only;
CFG-03/CFG-04 have none. This registry cannot dispatch operations and supplies
no missing INI paths or replacement endpoints.

### Qualified model and response subsets

| Offline entry point / cited PDF pages (printed = PDF minus 10) | Implemented scope | Explicit limits |
| --- | --- | --- |
| `qualify_login_response`; V/C 156-158 | Synthetic HTTP 200 `status: ok` plus nonempty session string, or 401 `status: error` plus nonempty message. Missing/wrong fields, malformed UTF-8/JSON, duplicate keys and nonfinite JSON constants fail with sanitized structured errors. No session/error body is returned or logged. | Example-shape qualification only, not a complete response/error schema or live authentication. Nonempty printable session/message checks are conservative local policy. "No Content" versus examples remains unresolved. Existing CC **HTTP-200-only** strategy is unchanged and separately regression-tested. |
| `qualify_schema`, `SchemaSubset.SITE`; V/C 255 | Required presence of `ormID`, `name`, `type`; documented non-null string types; optional string `description`, `parentOrmID`. Native strings are preserved without aliasing, trimming or invented IDs/defaults. | Lookup-model subset only; no site-create, name uniqueness or by-name extraneous-`id` repair. Required presence does not settle nullability. |
| `qualify_schema`, `SchemaSubset.DEVICE`; V 219-220/224, C 219-221/224 | Optional documented identity/text fields, signed int32 `ormVersion`, nested `deviceSetup` scalar fields and `deviceSetup.deviceAccess`. License/software/driver/hardware references receive object-shape checks only. | Not a complete Device model, response envelope/error validator or DevicePojo creation schema. Other fields, including opaque status/parent models, are preserved outside this validator's scope. Optional response fields never become create requirements. |
| `qualify_schema`, `SchemaSubset.DEVICE_ACCESS`; V 220-222, C 221-222 | All 40 optional field names accounted for: 8 int32, 9 boolean, 19 string, 4 enum references. No string/int/bool coercion; booleans are not integers; signed int32 bounds enforced. | All four enum value sets remain unqualified; no primitive enum representation is inferred. No defaults, null acceptance, complete access configuration or credential portability established. |

Schema qualification requires a caller-supplied **version-1 artifact envelope**
with domain `api-schema-evidence`, explicit source product/version, export
metadata, objects and existing offline-contract validation metadata. No envelope
metadata is fabricated by a wire-response adapter. Example Python use:

```python
result = qualify_schema(
    supplied_artifact_payload, SchemaSubset.SITE, evidence_reference="DOC-V549",
)
```

`status: documented-subset` means only the selected non-null field subset passed.
It is **not** complete vendor-schema validation, migration eligibility or runtime
qualification. `unqualified` issues explicitly retain present-null values,
unknown enum semantics, credential uncertainty and C's provenance discrepancy.
Null is neither certified as accepted nor rejected by the product. Missing
optional fields remain missing. Unknown permitted JSON, nested object/array
order, exact JSON types and native IDs survive a deep-copied artifact and
serialization; unknown fields remain outside schema qualification.
The existing artifact validation metadata is not silently upgraded to `valid`.

Existing-code changes are limited to order-preserving serialization for the new
`api-schema-evidence` domain and explicit planner rejection of that domain.
It cannot become a planning input even with a caller-asserted validation status.
Other generic domains keep sorted serialization and existing planning behavior;
existing controller behavior is unchanged.

Existing credential rules take precedence over vendor primitive types.
Recognized raw usernames/passwords/communities/tokens remain rejected, including
inside unknown configuration. Local `secret_ref` values are preserved but
explicitly **not vendor wire-qualified or portable**. The existing conservative
classifier also recognizes `verifyHttpCredentials`/`verifyHttpsCredentials`:
their documented raw booleans are therefore blocked by local protection, not
declared invalid vendor values. Null/protected representations remain uncertain.
No classifier, access acknowledgement, retention or comparison policy is weakened.

### Synthetic asynchronous trace qualification

`qualify_async_trace` consumes a finite, caller-supplied tuple of responses:
202/Location -> zero or more tracking 200s -> 303/result Location -> final result.
V/C 11/1 supplies the lifecycle, not tracking/result HTTP methods or final body
schema. Accepted, in-progress and result-available states all report
`not-complete`; neither 202, tracking 200 nor 303 means operation success.

The final observation determines the limited report: 4xx/5xx is `http-failure`;
an example-style JSON `status: error` is `reported-failure`; `status: ok` is only
`reported-success-unverified`; other well-formed results are
`unqualified-result`. The final body's status convention is **local reporting
policy**, not a newly inferred vendor async-result schema. No outcome verifies
configuration, read-back or migration completion. Malformed JSON and incomplete
or out-of-sequence terminal responses fail safely.

Exact trusted HTTPS origin, conservative status/result URI shapes, a single
Location, same opaque request ID, and rejection of missing/foreign/ambiguous
tracking are **local safety policies**, not established vendor acceptance rules.
The tuple assumes supplied responses belong to the observed exchange; it cannot
prove which requests occurred, authentication or actual Location traversal.
There is no network dispatch, polling, redirect handling, credential forwarding,
renewal, write retry or replay. Existing transport redirect rejection is unchanged.
Polling timing/limits, expiry, cancellation and actual final/error semantics
remain unverified.

### Verification and remaining gates

- Required full command: `python -B -m unittest discover -s tests -v`, using the
  existing interpreter and source path. **350 passed in 48.098s, exit 0**:
  all **321 existing regressions freshly rerun + 29 new test methods**.
  No failures/errors/skips. Focused new suite: **29 passed in 0.268s**.
- Python **3.13.14**, Windows AMD64. Pylance syntax checks and per-file
  diagnostics for the four touched Python files: no errors/diagnostics.
- The new tests explicitly measured **0 guarded network attempts across
  435 entrypoint observations (29 cases x 15 existing guard mocks)**, including
  imports. Existing suite guard cleanups also passed, but E-036 adds no aggregate
  counter for other tests/CLI subprocesses. This is Python-entrypoint measurement,
  **not OS-level isolation or proof about uninstrumented calls**.
- Production remains empty/default-deny, mocks remain exact `0.0-test` only,
  and real-version capabilities remain rejected even with mock opt-in.
  Existing authentication, identity namespaces, destination mapping, C2
  acknowledgements and C3 retention/execution protections remain unchanged.

Both migration directions remain blocked for runtime use. Obtain corrected C
provenance, defined DevicePojo/create results, consistent examples, by-name
parameter clarification, nullable/enum/error/completeness rules, credential
portability evidence, actual independent builds and missing tree/site-create/
PUT/LDAP/scheduler contracts. Destination preflight/read-back/recovery still
requires separate qualification. Owner acceptance and another milestone are
not recorded or started. See [E-036](PROGRESS.md#e-036---ccv-009-b-offline-subset-qualification-2026-11-18).

## CCV-009-B - approved vendor reference analysis

**E-035 documentation checkpoint.** Its independent technical review is now
complete; the later implementation and actual test results are recorded above.
The original PDF/source findings and historical test boundary remain intact.

Follow-up review: **2026-11-18**, after the owner supplied two approved local
PDFs. This section supersedes E-034's missing-document assessment, **not its
historical evidence**. Five of the 12 legacy pairs are documented in both PDFs;
seven are documented in neither. Endpoint evidence is not complete schema
qualification, production support, runtime verification or migration acceptance.
The CC reference has an unresolved version-provenance conflict.
**No owner acceptance recorded; subsequent review/implementation: E-036 above.**

### Approved PDF inventory and provenance

Page references below use **PDF page / printed page** (printed = PDF minus 10
for the cited numbered pages). The cover is PDF page 1, unnumbered. `V` and `C`
identify these exact local bytes, not any other release or future file revision.
The owner approved these files for offline review in the current conversation.

These vendor PDFs are access-controlled reference documents supplied separately
through approved organizational channels and are not included in the source
repository.

| ID / local document | Product, cover title and declared release | Date / sections | Provenance and limitations |
| --- | --- | --- | --- |
| V / `APSolute-Vision-5.4.9-REST-API.pdf` | APSolute Vision; exact title **APSolute Vision 5.4.9 REST API**; 5.4.9 | Overview/access/async: 11/1; overview states **April 2025**. HTTPS/licensing/API version: 12/2. General-SystemConfigTree starts 139/129; General-SystemUser starts 155/145; relevant models below. | 272 PDF pages, 7,604,887 bytes. Info Title agrees with cover. CreationDate and ModDate: `2025-04-09 11:09:09 +03:00`. No independent build identifier or external vendor authenticity check supplied. |
| C / `Cyber-Controller-10-10-7-Rest-API.pdf` | Cyber Controller; cover title **Cyber Controller 10.10.7 REST API**; cover and overview identify 10.10.7 | Overview/access/async: 11/1; overview states **September 2026**. HTTPS/licensing/API version: 12/2. General-SystemConfigTree starts 140/130; General-SystemUser starts 155/145. | 272 PDF pages, 7,662,043 bytes. **Active Info Title says Cyber Controller 10.10.6 REST API**, not 10.10.7. CreationDate: `2026-03-18 14:24:40 +02:00`; final ModDate: `2026-09-22 15:07:57 +03:00`. Version discrepancy unresolved. |

SHA-256:

- V: `827d4954cf5390f3a242e8bbb0af4dc7dd9ce68f5c17eba19449cf45a8d9d5c4`.
- C: `f6c7e474cb2df25d5d1b7b52da94f13f9b5013649419fc4276f49bd153e2d587`.

C's final PDF trailer selects `/Info 3189 0 R`; its latest dictionary contains
the 10.10.6 title above. Earlier incremental revisions retain other title strings,
including 10.10.5 and 10.10.7; they are **not separate approved references or
support evidence**. Some C operation descriptions also retain APSolute Vision
wording. Preserve these discrepancies; obtain corrected vendor provenance or an
authoritative version-applicability clarification before treating C as an
unambiguous exact-release schema authority. Do not silently relabel C, certify
10.10.6/10.10.5, or generalize either document to its whole version family.
Both references' "Version information: 1.0" (12/2) is not the product release.

### All 12 legacy method/path pairs versus both references

`Both` means an explicit operation declaration was found independently in each
PDF; placeholder names are normalized only for comparison (`name`/`site_name`,
`id`/`site_id`, `ip`/`device_ip`). It does **not** mean compatible contracts.
`Neither` means not documented in these supplied references, not vendor
non-support. C findings are attributed to its **10.10.7-labelled content with
the unresolved metadata conflict** throughout this report.

| Legacy ID | Exact legacy method/path template | Vision 5.4.9 evidence (PDF/printed) | CC 10.10.7-labelled evidence (PDF/printed) | Classification |
| --- | --- | --- | --- | --- |
| API-01 | POST `/mgmt/system/user/login` | Server Login, 156-158/146-148 | Server Login, 156-158/146-148 | Both |
| API-02 | GET `/mgmt/system/config/tree/Physical` | Not found | Not found | Neither |
| API-03 | GET `/mgmt/system/config/tree/Organization` | Not found | Not found | Neither |
| API-04 | GET `/mgmt/system/config/tree/site/byname/{site_name}` | Get Site by Name, 141/131; documented placeholder `{name}` | Get Site by Name, 152/142; `{name}` | Both |
| API-05 | GET `/mgmt/system/config/tree/site/byid/{site_id}` | Get Site by Id, 146/136; `{id}` | Get Site by Id, 146/136; `{id}` | Both |
| API-06 | GET `/mgmt/system/config/tree/device/byip/{device_ip}` | Get Device Data, 143-144/133-134; `{ip}` | Get Device Data, 143-144/133-134; `{ip}` | Both |
| API-07 | POST `/mgmt/system/config/tree/site` | Not found | Not found | Neither |
| API-08 | POST `/mgmt/system/config/tree/device` | Add Device to the Server, 148-150/138-140 | Add Device to the Server, 141-143/131-133 | Both |
| API-09 | PUT `/mgmt/system/config/tree/device` | Not found | Not found | Neither |
| API-10 | GET `/mgmt/system/config/itemlist/ldapobjectpermission` | Not found | Not found | Neither |
| API-11 | POST `/mgmt/system/config/itemlist/ldapobjectpermission` | Not found | Not found | Neither |
| API-12 | PUT `/{index}/_doc/{document_id}` | Not found; auxiliary service excluded | Not found; auxiliary service excluded | Neither |

Totals: **Both 5; Vision-only 0; CC-only 0; Neither 7**. The baseline stays
**12 concrete pairs / 16 logical records / 17 product-specific rows**, not a
new endpoint inventory. A's API-01-V and API-01-C now each have independent
document-content evidence, not just legacy authentication observations.
API-04/API-05/API-06/API-08 likewise gain document evidence; other legacy rows
retain their prior evidence only. Vision documentation for these operations is
new evidence for that product, not retroactive proof of legacy Vision use.

### All four scheduler references

| Existing reference | Method / unresolved path | V and C documentation | Disposition |
| --- | --- | --- | --- |
| CFG-01 | POST `<API.login_endpoint>` | Both explicitly document POST `/mgmt/system/user/login`; V 156-158/146-148, C 156-158/146-148 | Candidate counterpart in both; **configured legacy path still unresolved**, since the INI is absent. Do not assert alias identity. |
| CFG-02 | POST `<API.logout_endpoint>` | Both explicitly document POST `/mgmt/system/user/logout`; V and C 156/146 | Candidate counterpart in both; **configured path still unresolved**. Documentation does not authorize remote logout implementation. |
| CFG-03 | GET `<API.scheduler_endpoint>` | No scheduler/task-list operation found in either reference | Unresolved; no literal endpoint or task schema established. |
| CFG-04 | POST `<API.scheduler_endpoint>` | No scheduler/task-create operation found in either reference | Unresolved; task types, activation, timezone and references unknown. |

All four configured references therefore remain unresolved as legacy bindings.
The documented logout counterpart is supplementary evidence, **not a thirteenth
legacy pair**. No LDAP or scheduler topic occurs in either extracted reference;
generic item-list operations do not establish the missing named LDAP operations.

### Documented request, response and identity contracts

All operations below use the general HTTPS/session requirements in V/C 11-12/1-2.
Request fields not explicitly qualified by the reference remain unknown; a
response-model Required flag is not an allowed-create-field rule. Neither
reference specifies nullability, unknown-member acceptance, ordering semantics,
full pagination/completeness or idempotency for this selected slice.

| Contract / document pages (PDF/printed) | Request and required/optional evidence | Response, errors, identity and limitations |
| --- | --- | --- |
| Login, API-01-V/API-01-C; V/C 156-158/146-148 | POST exact path above; body required, containing `username` and `password`; no per-member optionality/nullability schema. Configured Local/TACACS+/RADIUS mechanism described. JSON consumed/produced; cookie session described. Basic-plus-JSON is legacy behavior, **not a documented requirement**. | 200 example has `status: ok`, `jsessionid`; 401 example has `status: error`, `message`. Tables also say "No Content" despite JSON examples: retain discrepancy, do not implement bodyless defaults. Overview requires `JSESSIONID` in Cookie on subsequent requests for authentication/RBAC. No TTL, renewal, CSRF, least-privilege role or exhaustive failure schema established. |
| Site by name, API-04; V 141/131, C 152/142 | GET exact path with required string `name`; tables also declare required path `id`, although **no `{id}` occurs in this URL**. No query/body schema given. Do not invent a second segment or query parameter to repair the table. | 200 `SitePojo`, JSON produced. No operation-specific not-found/duplicate/authorization/error contract. Name uniqueness, qualified tree/parent context and `ormID` versus managed-element alias equivalence not established. |
| Site by ID, API-05; V/C 146/136 | GET with required string `id`, described as server-retrieved item ID (`ormID`). No query/body schema given. | 200 `SitePojo`, JSON produced. Native ID use is documented, **cross-controller portability is not**. No complete error contract. |
| Device by IP, API-06; V/C 143-144/133-134 | GET with required path `ip`; schema column says `ref`, not a fully specified address grammar. No query/body schema given. | 200 `Device`; 500 failure example `status: error`, `message`, while schema column says "No Content". Response supplies device/properties/status information. The address lookup does not prove unique migration identity, detail-to-tree association or readable/portable credentials. |
| Create device, API-08; V 148-150/138-140, C 141-143/131-133 | POST exact path; JSON example has `name`, `parentOrmID`, `type`, `deviceSetup.deviceAccess`. Table has optional string `body` and required `requestBody` typed `[DevicePojo]`; **DevicePojo has no definition in either PDF**, and the example is an object. vADC prose explicitly requires `physicalParentId`, but does not settle its wire nesting. | 200 references **UserPojo**, an account-oriented model, not an evidenced created-device identity result. Duplicate device name and duplicate address errors are described (M_00023 / M_00302), without definitive HTTP statuses/body schema. Cannot qualify created-ID extraction, completion, safe write replay, required access fields or a complete request validator. |
| Logout candidate for CFG-02; V/C 156/146 | POST exact `/mgmt/system/user/logout`; no body/parameters specified; general authenticated-session context applies. Distinct GET Azure logout is not a POST alias. | 200 success JSON example `status: ok`, again paired with "No Content". No expiry, session-invalidation extent or error contract. No remote call implemented. |

#### Relevant model fields and remaining schema ambiguity

The following are field/type facts, not copied operational payloads. Model
optional means **Required=false in that model**, not permission to send null,
omit every creation field, or overwrite an existing destination.

| Model / pages (PDF/printed) | Documented field facts | Qualification limit |
| --- | --- | --- |
| `SitePojo`, V/C 255/245 | Required string `ormID`, `name`, `type`; optional string `description`, `parentOrmID`. | Describes site lookup result. Does not qualify absent POST site creation, roots, duplicate-name behavior or portable parent IDs. |
| `Device`, V 219-220/209-210, C 219-221/209-211 | Relevant fields all optional in model: string `ormID`, `name`, `description`, `type`, `treeType`, `physicalParentId`, `externalId`, `hierarchyPath`; integer(int32) `ormVersion`; `parent: SiteTreeNodeIfc`; `deviceSetup: DeviceSetup`; `deviceStatus: DeviceStatus`; boolean monitor/registration-related flags and other referenced configuration/status objects. `lockState` is `[Object]`, not a typed lock protocol. | No full recursive legacy tree/children response is established. Some referenced types remain opaque. Response-model optionality cannot resolve undefined DevicePojo creation requirements. |
| `DeviceSetup`, V/C 224/214 | All optional: `license: License`, `ormVersion: integer(int32)`, `ormID: string`, `deviceSoftware: Software`, `deviceDriver: DeviceDriver`, `name: string`, `description: string`, `deviceAccess: DeviceAccess`, `hardware: Hardware`. | Setup/access IDs are separate occurrences; no documented equality to device ID or removal permission. |
| `DeviceAccess`, V 220-222/210-212, C 221-222/211-212 | **40 fields, all Required=false**, in both references; grouped below. | No nullable/default/unknown-field policy, masking/encoding/export completeness or credential portability rules. Undefined enum value sets cannot be invented from example values. |
| `ManagedElementIdentifierPojo`, V/C 243/233 | Optional `managedElementClass: [Class]`, `managedElementID: [Serializable]`, `dbId: integer(int64)`. Nearby required `meIdentifier` belongs to a logical-group member model. | Not a documented schema for API-02/API-03; neither a string-only managedElementID guarantee nor a device-ID/access-ID alias rule. |
| `SiteTreeNodeIfc`, V/C 255/245 | Optional `parent: SiteTreeNodeIfc`, `name: string`. | Does not establish legacy tree root classes, native identifiers or child ordering. |
| `UserPojo`, V/C 270-271/260-261 | User/account fields, including credential and role/policy-related fields. | Its create-device response reference is inconsistent with device creation semantics; do not treat account `ormID` as the new device ID or infer a device response. |

DeviceAccess field groups (same documented names/types in the selected V/C models):

- **integer(int32):** `cliPort`, `httpsSocketTimeout`, `httpsPort`,
  `httpSocketTimout` (spelling as documented), `ormVersion`, `httpPort`,
  `httpsConnectionTimeout`, `httpConnectionTimeout`.
- **boolean:** `useHttpsAuthentication`, `useSnmpV3Authentication`, `isSsh`,
  `verifyHttpCredentials`, `useSnmpV3Privacy`, `exclusivelyReceiveDeviceEvents`,
  `useHttpAuthentication`, `verifyHttpsCredentials`, `registerDeviceEvents`.
- **string:** `description`, `cliUsername`, `ormID`, `snmpV3PrivacyPassword`,
  `httpsUsername`, `snmpV3AuthenticationPassword`, `snmpV2WriteCommunity`,
  `snmpV3Username`, `httpPassword`, `managementIp`, `httpsPassword`, `name`,
  `httpUsername`, `cliPassword`, `snmpV2ReadCommunity`, `snmpV1WriteCommunity`,
  `mgt2Ip`, `snmpV1ReadCommunity`, `mgt1Ip`.
- **Referenced enum types:** `snmpV3PrivacyProtocol`, `snmpV3AuthenticationProtocol`,
  `visionMgtPort`, `snmpVersion`; allowed-value sets are not established here.

Both create examples use strings for ports and boolean-like settings, whereas
DeviceAccess model tables say integer/boolean. Preserve that **example-versus-
model discrepancy**; no implicit coercion/defaulting is authorized. The selected
models and five matched operation declarations show no established material
cross-product wire transformation, but their similarities are not a complete
schema-equivalence proof. C's retained Vision wording and metadata conflict add
provenance uncertainty. Obtain authoritative clarification rather than silently
choosing whichever representation makes a validator pass.

### Documented asynchronous lifecycle

V and C, **Overview / Asynchronous Operations**, 11/1, independently describe:

1. Some operations return **202 Accepted**, not completed success. The initial
   **Location** identifies a status command associated with a unique request ID.
2. The example status URI shape is `/mgmt/asyncoperations/status/{id}`.
   The status command returns **200 OK while processing**; this 200 is not
   final operation success.
3. Completion of processing is signalled by **303 See Other** with another
   **Location** identifying the result command; example URI shape:
   `/mgmt/asyncoperations/result/{id}`.
4. The result command supplies the operation's relevant response code/body.
   A 303 alone means processing finished, **not that the requested change
   succeeded**. Classify the final result/error separately.

The overview supplies no explicit HTTP method for either tracking/result
command, exhaustive error state machine, polling interval, Retry-After policy,
retention/expiry/cancellation, maximum duration, or per-operation async list.
It does not document legacy `supportasync: true`. Do not infer that every
API-08 request is async or fabricate such requirements from its 200 table.
Authentication/RBAC still apply; no automatic renewal or mutation replay follows.

Any future separately authorized backend must validate Location origin/scheme/
path and request-ID correlation before sending credentials, use bounded
tracking, and surface malformed/missing/expired tracking or final errors safely.
These are **application safety requirements**, not vendor-documented error
semantics. Existing transport rejects redirects; this report changes neither
that policy nor implements polling, automatic 303 following or result fetching.
Loss of tracking does not establish a safe-to-retry write.

### Independent migration assessments and preflight gaps

**A: Vision 5.4.9 to CC 10.10.7-labelled content - unverified, blocked.**
Both references document the five matched operations, providing Vision
site/device lookup evidence that E-034 lacked. Neither provides the legacy
Physical/Organization export operations, LDAP endpoints, scheduler paths, site
creation or device PUT. Thus source root/hierarchy/completeness and destination
site creation still lack qualification. Device creation has the unresolved
request/response/type contradictions above. No field/type/enum, hierarchy,
access-secret, permission or task transformation is established; absence of a
documented difference is not an identity transform. Partial device lookup
coverage does not constitute a complete migration source.

**B: CC 10.10.7 to CC 10.10.7-labelled content - unverified, blocked.**
The same five documented pairs are available as content evidence for both
roles, subject to the unresolved C provenance. Independently declare and
qualify actual source/destination versions/builds; a shared PDF or matching
release strings do not prove equal state, native IDs, permissions or schemas.
Missing tree/export/site-create/update/LDAP/task contracts still block a full
workflow; undocumented patch-level behavior must not be generalized.

**Both directions:** destination preflight must independently establish native
root/parent/device IDs, hierarchy/type and reference compatibility, destination
inventory completeness, name/address conflicts, authorized roles, license
eligibility, credential policy, supported completion/read-back and recovery.
V/C 12/2 document RTU limits and inability to configure invalid-license devices;
they do not supply a complete preflight implementation. Name/address uniqueness
error prose is not proof of name/IP migration identity or tree scope. Root-name
examples are not authorization for name matching or fallback-to-root placement.
Require explicit qualified destination mappings; never copy source `ormID`,
merge by IP, equate nested access IDs, overwrite/delete, or strip unknown fields.

Passwords, usernames, SNMP communities/authentication/privacy material and
session IDs remain sensitive. A string schema does not establish plaintext
export permission, masking interpretation, encryption compatibility or
credential portability. Local `secret_ref` is an application contract, **not a
documented vendor wire representation**. Bound device-access acknowledgements
and existing secret-retention protections remain mandatory.

### Proposed offline validation tests and implementation gate

Historical E-035 proposals; see E-036 above for the implemented subset, measured
tests and remaining unqualified behavior. These proposal rows are not claims
that every suggested validator, hash check or live policy is now implemented.

No application code, validator, fixture or capability is changed in this
documentation task. Proposed tests, **not implemented or executed**:

| Proposed coverage | Expected assertion / prerequisite |
| --- | --- |
| Provenance and product/version binding | Correct V/C file hashes and cited page/operation bindings; reject nonexistent references, wrong product/version, changed bytes and wildcard/adjacent-release inheritance. Preserve C's conflict and block unambiguous exact-release qualification until clarified. |
| Inventory and scheduler binding | All 12 pairs and 17 product-specific rows accounted for; 5 Both / 7 Neither; all four INI bindings unresolved until sanitized literal paths are supplied. Do not activate absent methods or infer scheduler aliases. |
| Documented lookup/model subsets | Synthetic SitePojo required/optional fields and nested DeviceSetup/DeviceAccess field types; reject malformed shapes while preserving permitted unknown JSON. Model-only checks must not masquerade as full endpoint/create validators. |
| Missing/null, ordering and JSON types | Preserve existing missing/null and dictionary/array-order behavior; no string-to-number/boolean coercion, fabricated defaults or guessed enum values. Null policy awaits evidence; Required=false does not mean nullable. |
| Authentication and secrets | Synthetic 200/401 examples; reject/sanitize malformed session evidence, never retain credentials/session values in errors/reports. No actual login, renewal or remote logout. |
| Async state transitions | Model 202/Location -> tracking 200 -> 303/result Location -> final result/error entirely in memory. Cases for missing/wrong-origin Location, mismatched IDs, final failure, timeout/expiry uncertainty and no write replay; distinguish app safety policy from undocumented vendor behavior. |
| Identity and cross-product separation | Explicit independent destination IDs and role/build contexts; reject by-name/IP guessing, source-ID reuse, access-ID aliasing and credential portability assumptions. |

Complete endpoint validators must wait for resolution of undefined DevicePojo,
create-result UserPojo, model/example and by-name parameter contradictions,
null/unknown-field/completeness rules and C provenance. Do not weaken existing
contracts to accommodate incomplete documentation. Production capability
catalogue stays **empty/default-deny**, synthetic mocks remain `0.0-test` only,
and runtime behavior stays UNVERIFIED. See
[E-035](PROGRESS.md#e-035---ccv-009-b-approved-vendor-pdf-analysis-2026-11-18).

## CCV-009-B - offline schema qualification result

**Historical pre-PDF checkpoint (E-034).** The absent-document findings and
zero-documented-operation statements in this section and the original A
register below describe the material available then. The approved vendor
reference analysis above is the current evidence overlay; it preserves legacy,
mock and runtime classifications rather than rewriting historical observations.

Review date: **2026-11-18**. Owner-authorized scope is offline documentation
analysis and version-specific schema qualification only. **Partial qualification
report delivered; vendor/schema qualification blocked; technical review pending.
No owner acceptance is recorded.**

### Available documentation inventory

The workspace file inventory was repeated, including hidden root entries and
the project instruction file, without reading Git metadata or using Git.
The six project Markdown documents, Python/shell sources, and 20 JSON test/example
inputs are the available reference material. **Zero approved vendor documents,
OpenAPI/Swagger specifications, vendor KB articles, or exact product/build
declarations were found.** No PDF, HTML, Word, YAML or INI reference files were
present. This is a workspace-local result, not a claim about vendor availability
or files outside the workspace. No external material or private portal was
accessed. The supplied B authorization is scope evidence, not vendor evidence.

The project documents reviewed are [PROJECT](PROJECT.md),
[API_MATRIX](API_MATRIX.md), [ARCHITECTURE](ARCHITECTURE.md),
[DECISIONS](DECISIONS.md), [PROGRESS](PROGRESS.md) and [ROADMAP](ROADMAP.md).
Existing synthetic inputs and historical test results cannot qualify a vendor
schema. The baseline revision `ae06e0f` and requested branch
`feature/ccv-009b-api-schema-evidence` are owner-supplied context, **not verified**:
Git operations are prohibited in B.

### Evidence vocabulary and version binding

These labels expand, rather than replace, A's evidence terminology:

| B classification | Existing equivalent | B result and limits |
| --- | --- | --- |
| LEGACY_OBSERVED | L / source-observed | Canonical sources below re-read statically; eight of eight existing fingerprints reconfirmed. No source establishes an exact product release/build. |
| OWNER_REPORTED | O | Target families/directions and baseline context only; no exact per-operation build/result evidence supplied. |
| VENDOR_DOCUMENTED | D / officially documented | None available; zero operations qualified. |
| MOCK_VERIFIED | M / mock-tested | Existing `0.0-test` authentication and API-02/API-03/API-10 contracts only; historical results, not rerun in B. Not vendor schemas. |
| LIVE_LAB_VERIFIED | T / live-tested | None supplied at operation/build level; none performed. |
| UNVERIFIED | Existing unknown/unverified status | Every real-target request/response schema, compatibility and operational behavior without supporting evidence. This is a qualification status, not positive evidence. |

| Product / role | Exact version/build evidence | Operation scope | Qualification |
| --- | --- | --- | --- |
| APSolute Vision source A | Not supplied; `5.4.x` is only an OWNER_REPORTED target | API-01-V, API-10, CFG-01 through CFG-03; additional source object/access APIs unknown | UNVERIFIED; no exact supported version |
| Cyber Controller source B | Not supplied; `10.10.x` is only an OWNER_REPORTED target | API-01-C, API-02/API-03/API-05/API-06; other source-domain APIs missing | UNVERIFIED; no exact supported version |
| Cyber Controller destination A/B | Not supplied independently of source | API-01-C, API-02/API-03/API-04 inventory candidates; API-07/API-08/API-09 write candidates | UNVERIFIED; no exact supported version |
| Vision legacy destination / auxiliary service | Not an approved A/B destination | API-11, CFG-04 / API-12 | Outside direction scope / excluded |

No `5.4.x`, `10.10.x`, wildcard, inferred patch, or synthetic marker is an exact
vendor compatibility binding. The same CC family on both sides supplies no
schema-equivalence evidence.

### Request/response field evidence ledger

This ledger supplements the existing method/path, authentication, dependency
and safety tables; it introduces **no new operation or schema**. All entries are
**LEGACY_OBSERVED, exact product version unknown, vendor qualification
UNVERIFIED**. Field paths are source expressions, not vendor-required fields.
Direct indexing means the script expects a field; `.get` or a constructed
default means client behavior, **not documented optionality or server defaults**.
For every row, vendor-required, optional and nullable field sets are **unknown**.
Missing and explicit null are not interchangeable; neither can be accepted or
defaulted on the strength of these scripts.

| Record | Request structure / parameters observed | Response structure / status checks observed | Evidence / unresolved schema semantics |
| --- | --- | --- | --- |
| API-01-C | JSON-text `username`, `password`; Basic credentials also assigned | Client accepts 200; no body schema checked | OD 54-85; OC/OU 52-84. Required auth combination, cookie/CSRF/token format and error bodies unknown. |
| API-01-V | JSON object `username`, `password` | HTTP error check then JSON object `.get("status") == "ok"` | LD 16-23; LU 13-20. Login status is a client check, not a complete response schema. |
| API-02 | No body/query parameters supplied; fixed Physical path | OD traverses `children[]`; node `meIdentifier.managedElementClass`, `managedElementID`; `name`; devices additionally `type`, `managementIp`; destination reader consumes root ID | OD 110-142, 180-216; OC/OU 143-150. Root class, complete fields, cardinality, nullability and HTTP success contract unknown. |
| API-03 | No body/query parameters supplied; fixed Organization path | Same client field selections as API-02, independently selected tree | Same source ranges as API-02. Shared traversal is not documented cross-tree schema equivalence. |
| API-04 | Raw `site_name` path parameter; no qualified tree/parent selector supplied | Parsed object; OD reads `ormID`; OC/OU try `meIdentifier.managedElementID`, then `ormID`; text used for absence | OD 88-96; OC/OU 86-120. No documented success/absence/error status, alias equivalence or duplicate-name behavior. |
| API-05 | Raw `site_id` path parameter from source hierarchy | Parsed object `name`; response text checked for absence | OD 99-107, 124-126. Native identifier scope and response/error contract unknown. |
| API-06 | Raw `device_ip` path parameter | Object `deviceSetup.deviceAccess`; nested `ormID` deleted by script | OD 145-163. Native detail device ID, access field types, masking, missing/null and errors unknown; deletion is not an allowed transform. |
| API-07 | Object `parentOrmID`, `name` | Client accepts 200; on failure assumes JSON `message` | OC 152-175. Created ID, body, completion, duplicate behavior and error schema unknown. |
| API-08 | Object `name`, `parentOrmID`, `type`, nested `deviceSetup.deviceAccess` copied from flat input | Client accepts 200; failure `message` assumed | OC 177-202. Full access schema, accepted fields/types and created-ID/completion contract unknown. |
| API-09 | API-08 fields plus `ormID` from exported `id` | Client accepts 200; failure `message` assumed | OU 152-184. PUT replace/merge, field mutability and destination identity binding unknown; source-ID reuse prohibited. |
| API-10 | No body/query parameters supplied | LD saves parsed JSON after HTTP error check; LU iterates entries and indexes `attributeValue` | LD 17-29; LU 14-24. List-of-objects is consumer expectation, not a qualified full response/pagination schema. |
| API-11 | Object `objectClassName`, `attributeName`, `attributeValue`; `requireDeviceLock` forced true; `networkPolicies` defaults to []; `roleGroupPairList[]` selects `groupName`, `roleName` and defaults to [] | Client accepts 200/201; response text may trigger scope-changing retry | LU 28-39. Defaults/lock/scope changes are unsafe legacy behavior, not vendor requirements. Vision destination only, not a CC schema. |
| API-12 | Raw `index`, `document_id` path parameters; opaque `_source` object from `hits.hits[]` | HTTP error check, then parsed JSON printed | DR 8-11. Auxiliary service/version/schema unknown; excluded from product qualification. |
| CFG-01 | Configured path unresolved; JSON `username`, `password` | HTTP error check; JSON `.get("status")`; `.get("jsessionid")` printed | SD 23-26, 41-70; SU 23-26, 46-75. Session identifier is sensitive; name alone does not establish a cookie/session contract. |
| CFG-02 | Configured path unresolved; no body supplied | Status/body ignored; exceptions suppressed | SD 28-31, 73-81; SU 28-31, 78-86. No logout/invalidation/error contract established. |
| CFG-03 | Configured path unresolved; no body/query parameters supplied | SD saves parsed JSON after HTTP error check; SU expects list of objects with truthy `name`, otherwise returns empty set | SD 33-36, 84-117; SU 89-108. Empty fallback is not completeness evidence or valid malformed-response handling. |
| CFG-04 | Configured path unresolved; task copied minus `ormID`, `taskStatus`, `jobstatus`, `previousFeedMd5` | Client accepts 200/201 only | SU 111-123, 157-197. Task types, required/server-owned fields, activation, timezone and nested references unknown; no stripping authorized. |

For **all 17 rows**: no vendor-required headers, query parameters, pagination,
ordering rules, unknown-field policy, missing/null behavior, complete nested
schemas or error responses are documented. GET call sites supply no body, which
is not a vendor prohibition on GET bodies. Observed headers are only the client
choices in authentication profiles A/B/C/D: JSON Accept/Content-Type and, for
Vision scripts, XMLHttpRequest; OC/OU also set `supportasync: true`. Browser-style
headers in object scripts do not become requirements. The async header and a
200/201 check establish neither asynchronous behavior nor completion.

Authentication requirements, session lifetime/renewal/logout, RBAC,
preconditions, pagination, asynchronous result/completion, idempotency and error
behavior remain **UNVERIFIED** for every target operation. Dependencies recorded
in A are client workflow observations or application safety prerequisites, not
vendor-proven dependency contracts. No behavior is inferred from HTTP verbs.

### Identity and credential field qualification

| Field / context | Available evidence | Qualification / offline boundary |
| --- | --- | --- |
| `meIdentifier.managedElementID` | OD tree extraction and OC/OU root/name lookup | Native source identifier candidate, not portable identity; scope/stability/alias semantics unverified. Keep controller/tree/type context. |
| `ormID` / `parentOrmID` | OD/OC/OU lookups, constructed payloads and access-ID deletion | Object, parent and nested access occurrences must not be conflated. Equivalence to managed-element ID and cross-controller reuse are unverified. |
| Flat `id`, `parentOrmID`, `parent_site_name` | OD constructs export fields | Legacy export representation, not an independently documented wire schema; parent name/IP cannot establish destination identity. |
| LDAP `attributeValue`, `groupName`, `roleName`, `networkPolicies` | LU selected fields and equality-based skipping | Authorization/reference fields; native identity and permission equivalence unknown. Explicit destination reference mappings required. |
| Scheduler `ormID`, `name`, removed status fields | SU task selection/sanitization | Native identity candidate versus display name/status semantics unqualified; field removal and name-only equivalence prohibited. |
| Login `username`, `password`; Basic/authorization/cookie/session material, `jsessionid` | OD/LD/SD authentication source | Sensitive identity/credential/session material; never reproduce values, log bodies, or collect real credentials. |
| `cliUsername`, `cliPassword`, `httpUsername`, `httpPassword`, `httpsUsername`, `httpsPassword`, `snmpV3Username`, `snmpV3AuthenticationPassword`, `snmpV3PrivacyPassword` | [Credential transformer](../legacy/app/update_json_credentials.py), lines 47-134, static only | Sensitive access fields, not complete version-qualified lists. Server representation, masking, encryption, requiredness and portability unknown. |
| `secret_ref` | Existing application artifact/controller contracts | Local protected-reference representation, **not a vendor API field**. It does not resolve a credential or establish migration eligibility. |

The transformer SHA-256 inspected in B is
`efc935bcfd32e14b40960f1a37f93906e54b07dacc5faaabb9253cef447990a3`;
the eight original fingerprints below were also reconfirmed. No legacy code was
imported, executed or modified.

### Direction-specific schema qualification

**Vision to CC (A): UNVERIFIED / blocked.** Source Vision tree/root/site/device
and detail/access export paths and schemas are absent. API-10 is a legacy LDAP
read candidate, not a qualified 5.4 release schema; CFG-03 is unresolved.
Destination CC requires independently versioned root/inventory, object types,
parent/identity/reference, access/secret, creation-result and completion schemas.
CC LDAP and scheduler equivalents are missing. No documented field/type/enum,
hierarchy, permission-scope, credential or task transformation is available.
Their differences are **unknown**, not established equivalences or an invitation
to invent transforms. Controller objects/access, LDAP and scheduler migration
all remain unsupported for the target direction.

**CC to CC (B): UNVERIFIED / blocked.** Legacy source candidates API-02/API-03/
API-05/API-06 and destination API-07/API-08/API-09 require separate exact
source/destination build schemas, including within 10.10.x. Tree completeness,
native detail association, secret portability, device types, allowed writes,
read-back and completion remain unknown. CC LDAP/task contracts are missing.
No patch-level equality, automatic source-ID reuse, name/IP guessing, overwrite
or delete is permitted; explicit independently established destination mappings
remain mandatory. Even identical declared build strings would not establish
portable native identifiers or verified backend behavior.

### Missing evidence and next gate

DOC-V54, DOC-CC1010, CFG-SCHED and TEST-OWNER above remain requests, not evidence
references that can support an assertion. Exact document titles cannot honestly
be supplied from available material. Request owner-approved **REST API references
and schema/specification appendices** for the selected exact Vision 5.4 patch/build
and independently selected source/destination CC 10.10 patch/builds, plus applicable
authentication/session, tree/site/device/access, LDAP and task sections, release
schema changes, and KB articles relevant to the canonical legacy scripts.
Include result/error, completeness/pagination, identity, sensitive-field,
dependency, write completion and idempotency sections; full backup coverage is
still unestablished. Supply only sanitized scheduler path declarations and
operation-level testing provenance, not AUTH sections, hosts or operational data.

For each supplied approved reference, record actual title, publisher/product,
exact version/build applicability, revision/date (or explicitly unavailable),
section/page/operation, local file and SHA-256, approval/review provenance and
limitations. An assertion must reference an existing reviewed source that
supports that operation/field/version; a missing ID, title, family label,
synthetic fixture or unrelated section cannot qualify it.

**No schema validator or new evidence registry is introduced:** zero exact
vendor schemas meet the implementation gate. Existing strict parsers,
order-preserving controller artifacts, missing/null distinctions, secret
protections, qualified mappings and sanitized errors are reused unchanged, not
relabeled vendor-qualified. Production capabilities remain empty/default-deny,
and `0.0-test` stays mock-only. No application/tests/fixtures, HTTP backend,
credential transformation or production activation change is warranted.
Documentation-only verification and test-execution limits are recorded in
[E-034](PROGRESS.md#e-034---ccv-009-b-offline-partial-schema-qualification-2026-11-18).
Stop for technical review and missing evidence; do not begin another milestone.

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

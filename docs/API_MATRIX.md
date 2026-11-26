# API Evidence and Compatibility Discovery Matrix

Date: 2026-11-18
Evidence levels: source-observed endpoints; separately scoped offline mock
coverage for authentication and three reads; owner-provided vendor PDF evidence
for selected exact method/path pairs; E-036 synthetic offline subset regressions.
Runtime compatibility is scoped; current owner-reported evidence and remaining
qualification limits are recorded below.

## CCV-012 recovery / CCV-013 Device qualification

- Owner evidence on CC 10.15.0-2: one Site POST, visible root-child Site,
  subsequent name/type/nonempty destination ormID lookup with null parent.
  Original POST response/journal are unavailable here. The exact
  `site_identity_missing_or_ambiguous` rejection validates name/ormID, not parent.
  Missing POST identity reproduces that code; the actual response is unknown.
- Read-only reconciliation now requires fresh exact Site type/name/identity,
  by-ID agreement and independent Organization membership. Explicit null parent
  is accepted only for proven direct root-child placement. Historical POST
  evidence is retained; no additional create during reconciliation.
- Device evidence: original `upload_cybercontroller_objects.py` 177-202:
  POST `/mgmt/system/config/tree/device` with `name`, destination `parentOrmID`,
  `type`, `deviceSetup.deviceAccess`. Original
  `download_cybercontroller_objects.py` 110-157: Organization Device projection
  and GET `/mgmt/system/config/tree/device/byip/{ip}` access extraction.
  Legacy HTTP-200-only success and first-IP/root fallback are not reused.
- Organization Device inventory, separate controller/access lookup inventories,
  deterministic hash binding, conservative association candidates, Site-journal
  parent dependencies and read-only existing Device qualification implemented.
  Existing qualification checks name/type/IP/native identity and actual parent
  membership; inventory-only verification is not access/connectivity completion.
- `DestinationReadAuthorization` permits only finite selected Site/Device GETs,
  Organization GET and login POST. Existing SingleSiteAuthorization is unchanged.
  Explicit origin-bound lab TLS consent uses the existing discovery policy;
  ordinary discovery does not gain additional permissions.
- Device execution/resume remains blocked: an access-free inventory-only POST
  schema, returned identity and bounded independent completion contract are not
  established. No Device/access POST, PUT, automatic update/reparent or retry.
  Synthetic tests do not qualify a create response by inventing a payload.
- CC 10.10.x remains primary; owner evidence on CC 10.15.0-2 is not universal
  certification. No live controller operations performed during development.

## CCV-012 - shared hierarchical Site orchestration

Implementation extends the existing finite Site API, not its endpoint scope:
login, selected parent/candidate by-name GET, Organization GET, one reserved
Site POST and exact by-ID readback. Ordinary discovery and single-Site scopes
are unchanged. One runtime batch authorization binds the recomputed ordered
input list and displayed destination; children consume only verified destination
identities. Existing Sites require fresh exact identity/parent/hierarchy evidence.

| Capability | Evidence / qualification |
| --- | --- |
| Full hierarchy | Synthetic 30-Site, 22-parent-dependency mocked graph; parent verification precedes dependent POST |
| Missing candidate | Existing strict HTTP 404 / legacy HTTP 200 / exact name-bound HTTP 400 M_00734 handling, corroborated by fresh Organization tree; M_00734 observed by owner on 10.15.0-2 only |
| Durable resume | Protected hash/origin-bound journal, destination mappings and pre-POST identity baseline; per-origin process lock and shared per-Site reservations; uncertain absent/mismatched operations never blindly retried |
| Completion | Returned new identity plus bounded by-ID and hierarchy readback; configurable 1-10 rounds and 0-60-second delays; errors/ambiguity stop the batch |
| CC 10.10.x primary | Shared experimental implementation; no target-verified POST/completion claim |
| CC 10.15.x lab | Owner-reported single-Site dry-run success on 10.15.0-2; no live batch or POST/readback executed during development |

No new version endpoint, per-version client, Device API or bulk write endpoint.
No automatic rollback, root renaming/fallback or source-native-ID reuse.
Implementation approval is not authorization to modify a controller.

## CCV-011 - implemented experimental controlled single-Site operation

Owner approval now covers implementation and mocked verification of the bounded
write path, **not live execution**. This supersedes historical statements below
that a write backend is not implemented. Ordinary discovery/root-only scopes and
offline comparison remain unchanged and never gain write permission.

| Contract/capability | Source evidence | Current implementation / target evidence |
| --- | --- | --- |
| Site POST `/mgmt/system/config/tree/site` | Original uploader and official Radware cloner; minimal `name`, `parentOrmID` | Explicit one-Site operation only; runtime consent, one-attempt backend and durable reservation; mock-tested, no target POST performed |
| Parent resolution | Destination by-name lookup consumes destination ormID | Fresh selected-parent GET plus Organization identity/placement crosscheck; rejects source IDs; Default must be tree root with null own parent. Saved artifact references are never native IDs |
| Source fields | Original minimal projection; four unprojected fields documented below | Only source name projected; opaque data/counters/dbId omitted experimentally, not proven optional on target |
| Collision evidence | By-name read plus Organization tree | Exact legacy HTTP-200 not-found signature or HTTP-404, corroborated by structurally valid fresh tree; normalized name/identity ambiguity blocks. Completeness and not-found semantics still experimental |
| Create outcome | Legacy checks HTTP 200 only | Require 200/201, exact expected name and usable new ormID absent from the final preflight identities. Missing/pre-existing identity, 202, timeout or error remains indeterminate; no invented response wrapper/job API |
| Completion | Legacy does not establish | At most 3 exact returned-by-ID GET + Organization rounds; consistent returned/new identity, expected name and actual parent placement required. Unknown schemas fail closed |
| Failure policy | Legacy unsafe continuation rejected | No POST retries, rollback, second ambiguous create, root rename/fallback, Devices or bulk. Persistent per-canonical-origin/name guard blocks reexecution in shared report directory |
| CC 10.10.x (primary) | Legacy/PDF evidence, unresolved exact patch/provenance | Shared experimental code; no target-verified POST/absence/completion contract or certification |
| CC 10.15.x (additional) | Owner's successful Default GET on GUI-observed 10.15.0-2 | Root read evidence retained; not proof of Site-create compatibility. No target POST/readback test performed |
| Other CC 10.x | Published cloner compatibility stops at 10.5.0 | No family-wide claim or hardcoded version branches |

Implementation: `src/cc_vision_import/single_site.py`, strict
`SingleSiteAuthorization`, existing CLI/Compose/launcher. Dry-run loads immutable
hash-bound source/snapshot/comparison, recomputes selected evidence and requires a
confirmed parent mapping; unresolved child dependencies cannot be created.
Exact login/selected reads are scoped to one approved HTTPS origin. A Site POST
is armed only after separate interactive approval and fresh same-session checks.
Only returned-ID readback is subsequently added. Credentials/session/TLS cleanup,
default verified TLS and explicit session-only certificate consent are reused.
Reports contain static field references/presence/results, never native values.

Remaining live prerequisites: separately authorize the exact controller/account,
restricted egress and single candidate; rebuild reviewed shared image; pass real
read-only preflight with matching source/snapshot hashes and parent/tree identity;
freeze competing writers, explicitly accept the target contract risks and arrange
manual reconciliation. Missing parent/tree correspondence or unrecognized
absence/response schema must be resolved through separately approved read evidence,
not bypassed. A controlled test can qualify only its exact observed release/case.
See README for exact dry-run and separately authorized execution commands.

## CC-DESTINATION-DISCOVERY - approved tree-only, version unknown

Owner authorizes implementation of separately selected, read-only destination
discovery, not live execution during development. Existing network-disabled
destination service and six source collectors must remain unchanged.

Established references:

- API-01-C: POST `/mgmt/system/user/login`; observed original CC downloader
  lines 53-96, independently documented CC PDF pages 156-158. Original Basic+
  JSON and HTTP-200-only acceptance are not a fully qualified login/session
  validator; new discovery must not silently treat them as such.
- API-03: GET `/mgmt/system/config/tree/Organization`, observed downloader
  lines 180-185/215-216 and uploader root read 143-150. Legacy traversal consumes
  children and Site meIdentifier.managedElementID/name, but exact destination
  release/schema applicability and enumeration completeness remain unqualified.
  The reviewed CC PDF does not declare this exact tree GET.
- API-04/API-05: Site-by-name/by-ID reads are documented, but do not independently
  enumerate the root/hierarchy or establish product version.

Current code/reference search found no concrete product-version discovery
endpoint. A fresh offline scan of all 272 pages of the approved local CC PDF
also found no product-release/build read contract. Page 12 "Version: 1.0" is
API specification metadata, not installed CC version. The existing document
cover/metadata 10.10.7-versus-10.10.6 provenance conflict is unchanged.

Owner explicitly approved reduced tree-only discovery with destination release/
build **unknown/unverified**. No environment-declared or specification version
is treated as discovered. Product-version discovery remains blocked pending
an exact evidenced method/path, response schema and target applicability.

Default `destination-discovery` uses only the two established login/Organization
paths. Explicit `--qualify-default-root` instead uses login and the exact
Default by-name GET, with a separate sanitized, non-executable report; it never
widens the tree-mode allowlist.
Basic+JSON login also requires a successful JSON status and validated session
identifier, using the existing session validator; HTTP 200 alone is rejected.
TLS/hostname verification starts TRUE on every launcher execution. The single
deployment control CCV_ALLOW_INSECURE_TLS_EXCEPTION defaults true, permitting
the default-NO interactive choice without operator setup. An administrator's
explicit false prohibits exceptions for production. A verified pre-auth
certificate failure offers one choice unless locked. Explicit approval permits one new attempt for the same
selected origin/execution, using a private temporary exception rather than
persistent per-controller policy. HTTPS, warnings, sanitized TLS status/scope and
generic transport's verification-only gate remain intact. No credentials are
transmitted before the TLS handshake completes; unverified transmission requires
approval. Post-authentication/partial operations are never restarted.
HTTPS port 443 only, no automatic HTTP retries/redirects,
bounded responses and exact application origin/method/path authorization.
The optional Compose discovery bridge requires administrator-managed egress
restrictions; it is not itself a firewall. Offline destination remains network-none.

Snapshot projection retains only native root/Site identity, name and explicit
parent fields, plus observed containment references. Device records and unknown
field values are excluded. Full-response recognized credential redaction counts
are reported before projection; missing fields, duplicates, unknown classes and
conflicting/ancestor dependencies remain explicit. Nesting/root semantics are
legacy-inferred, enumeration completeness and target compatibility unverified.
The distinct snapshot domain is rejected by the existing import-artifact parser.
No version request, configuration write, live controller call, deployment or Git
operation was performed during implementation. Mocked offline evidence is
recorded in PROGRESS.md; it does not qualify the actual destination release.

## SOURCE-DESTINATION-SITE-COMPARISON - offline saved evidence

Implemented `site-comparison` using the source Site-readiness validator and the
existing destination Site projection applied only to retained, observed
root-connected Site containment. Orphans, explicit parent conflicts, missing/
duplicate identities and names remain blocked/ambiguous; no root attachment or
identity substitution is invented. Source/destination references are separate
artifact-local namespaces, bound to whole-input SHA-256 in the CLI report.
Native values remain in unchanged inputs; safe counts/static issue codes only.

Explicit root-name declarations propose an association. `--confirm-root-mapping`
records operator confirmation after checking both snapshots, not root identity
equivalence, renaming, or write approval. Unique exact-name/parent candidates
are only possible existing Sites; duplicate names, conflicting parents and
ambiguous native identities are not silently mapped. Zero retained destination
Sites permits conditional creation candidates, not verified absence/completeness.
Source parent-before-child order and future parent destination-ID requirements
are exposed without create payloads or assigned destination IDs.

Owner now reports a successful real comparison: 30 source Sites, zero discovered
destination Sites, confirmed Bell Canada -> Default root association, 30
conditional creations and 22 future parent destination-identity dependencies.
No ambiguous or unresolved comparison classifications were reported. The attached
sanitized report at `C:\CCV-Evidence\site-comparison-confirmed-20261126.json`
has now been inspected and supports these counts and confirmed root references.
The underlying source/destination snapshots were not supplied or independently
reconciled here; report inspection is not a reproduction of the comparison.
Destination 10.15.0-2 is GUI-observed only. No alternate backups were substituted.
Synthetic fixtures are test evidence, not observed controller data.

Destination create/schema/version qualification, native identity to create-parent
field correspondence, inferred root/parent semantics, incomplete enumeration and
unprojected fields remain blockers before any separately authorized Site-create
test. The comparison is always non-executable/migration-blocked and rejects live
options. Existing offline Compose passthrough provides network-none/incoming-RO
execution, without launcher/service/authentication/TLS/discovery changes.
No endpoints, configuration writes, Device associations or capability activation
are added. Test evidence is recorded in PROGRESS.md.

## LEGACY-CC-OBJECTS-COMPATIBILITY-REUSE - primary implementation reference

Current destination priority: **CC 10.10.x**. CC 10.15.x and other CC 10.x are
additional compatibility targets only where exact operation behavior is verified.
A family label is not a tested release; the primary target's precise patch/build
and live contract evidence have not been supplied. Earlier 10.15.0-2 results
remain valid for the observed read, not evidence for every 10.x release.

On 2026-11-26 the following original workspace files were read in full, without
executing/importing their code or authentication functions. They are the primary
implementation reference; repository legacy copies and the public cloner are
corroborating/historical evidence, not substitutes for these inspected files:

- **U**: [upload_cybercontroller_objects.py](<../../CC -Master Config Migration/cc-objects/app/upload_cybercontroller_objects.py>).
- **D**: [download_cybercontroller_objects.py](<../../CC -Master Config Migration/cc-objects/app/download_cybercontroller_objects.py>).
- **X**: [update_cybercontroller_objects.py](<../../CC -Master Config Migration/cc-objects/app/update_cybercontroller_objects.py>).

### Exact reusable contracts and function anchors

| Original function / lines | Observed method/path and data flow | Reuse decision |
| --- | --- | --- |
| U/X `login_cyber_controller` 52-84; D same function 54-85 | POST `/mgmt/system/user/login`; Basic auth plus manually concatenated username/password JSON; HTTP-200-only acceptance. U/X advertise supportasync=true. | Do not transplant. Existing master validated authentication/session/TLS/secret lifecycle replaces it. Async header is a request preference, not completion evidence. |
| D `main` 180-202; U `upload_configuration` 143-150; X same 143-150 | GET `/mgmt/system/config/tree/{tree_type}` for Physical/Organization; native root identity from meIdentifier.managedElementID. D entrypoint 205 onward invokes both trees. | Retain separate tree/role concepts, not presumed root equivalence. First test Organization only, explicit root association; do not broaden current allowlists. |
| D `get_parent_site_name` 99-107 | GET `/mgmt/system/config/tree/site/byid/{device_parent_id}`; consumes response name; error-text detection only. Called for Site parent naming in extraction. | Readback path evidence, not post-create verification. Do not equate passed managedElementID with lookup ormID without evidence; reuse existing qualified request/schema helpers, not this unchecked request. |
| D `get_parent_site_id` 88-96; U/X same 86-120 | GET `/mgmt/system/config/tree/site/byname/{parent_site_name}`. D consumes ormID; U/X prefer meIdentifier.managedElementID, then ormID; broad errors return False. | Adapt to explicit destination parent resolution and ambiguity checks. Never treat missing/malformed/error/duplicate as permission to choose root; no implicit ID alias. D helper is defined but not used by its main export path. |
| D `extract_sites_and_devices` 110-142 | Walks children by native Site/Device class. Site record has name, source id, parent_site_name, source parentOrmID. Appends Site before recursion, then extends child Sites; Device records retain name/type/managementIp/source id/source parentOrmID. | Reuse field roles and dependency concept. Existing source parser/order handles immutable native backup, duplicates, unknown classes and graph blockers more safely; no second traversal/parser is needed. |
| U `upload_configuration` 152-175 | For every sites[] entry in input order: destination parent-name lookup; falsy result substitutes tree root; POST `/mgmt/system/config/tree/site` with name/parentOrmID. HTTP 200 success, other responses assumed JSON message. | Reuse two-field construction as an unqualified contract candidate only. Reject fallback, unchecked payload/error body and continue-on-failure. No returned-ID extraction/readback in this loop. |
| U `get_site_name_by_id` 122-128; U `upload_configuration` 177-202 | Match Device's source parentOrmID against source sites[].id to find parent name; resolve destination parent, otherwise root. POST `/mgmt/system/config/tree/device` with name,parentOrmID,type,deviceSetup.deviceAccess. | Future Device association depends on verified destination Site/root mapping, target type/access schema and independent Device identity. Excluded from next Site milestone; do not copy source IDs or root fallback. |
| D `extract_device_access_data` 145-157 | GET `/mgmt/system/config/tree/device/byip/{device_ip}`; consumes deviceSetup.deviceAccess, removes only its ormID, attaches to first matching managementIp. | Evidence for source enrichment only, not post-create readback or sufficient credential/identity sanitation. Do not modify the six working collectors or infer IP uniqueness/portable secrets. |
| X `upload_configuration` 152-184 | Device loop only: input device.id becomes PUT body ormID; name,parentOrmID,type,deviceSetup.deviceAccess also sent to `/mgmt/system/config/tree/device`. X main uses an Organization `_updated` file. | No Site update/readback exists here. Filename does not prove Device IDs were remapped; reject input-ID reuse on a different destination without independent mapping. No update feature authorized. |
| U `main` 204-225; X `main` 186-207; D `write_json_to_file` 169-177 | Local flat files, Physical then Organization; separate invocations/sessions; generic exceptions/logging. U/X load_config 27-50 and D 28-51 read plaintext INI credentials. | Keep export/plan/import/verification separate. Reject plaintext credential persistence, raw response logging, insecure TLS, unbounded requests and missing lifecycle/validation guarantees. Original files remain read-only. |

### How legacy child-Site restoration actually works

1. D appends a parent Site before recursively extracting that Site's descendants;
   this produces parent-before-child Sites in observed child order. It does not
   sort arbitrary imported JSON or validate a dependency graph.
2. U consumes the supplied sites[] order unchanged. A child's destination parent
   is looked up by the exported source parent's **name** after the earlier
   parent's POST; the returned create identity is never captured or cached.
3. This works only if parent creation has completed and name lookup is unique/
   correctly scoped. U does not prove either. A failed parent POST does not stop
   the loop; a later unresolved child can be silently created under root. An
   async delay has the same hazard. Both paths are rejected for the master.
4. Devices are submitted after the entire Site loop, even if some Sites failed.
   Missing source parent names choose destination root; a failed non-root lookup
   can yield False as Device parent. Device association is therefore not safe
   merely because Sites were attempted first.
5. These original U/D/X files contain no automatic root-rename request and no
   Site post-create readback. The public cloner's root PUT is separate evidence
   and remains prohibited. No automatic request-retry loop was observed, but
   repeated manual runs are not idempotent and can duplicate configuration.

### One version-aware compatibility matrix

Evidence labels: source-observed is implementation intent, documented is the
previously reviewed PDF contract, owner-live is the owner's sanitized result;
none implies target write qualification. No version branches are justified by
the current evidence.

| Operation / dependency | Original code evidence | Primary CC 10.10.x | Additional CC 10.15.x | Other CC 10.x |
| --- | --- | --- | --- | --- |
| Login/session | U/D/X functions above | Documented older CC login plus mock evidence; exact primary patch/build/live acceptance unknown | Owner-live validated session enabled Default read on GUI-observed 10.15.0-2 only | Unknown until exact-release validation |
| Organization/Physical tree | D main, U/X root GET | Source-observed; exact tree schema/root identity and completeness unqualified | Organization discovery succeeded; zero discovered Sites does not prove complete absence. Physical not qualified by that result | Unknown |
| Default/name lookup | D 88-96, U/X 86-120 | CC PDF by-name operation documented; 10.10.7 cover versus 10.10.6 metadata conflict still unresolved; no primary live result | Owner-live on 10.15.0-2: Default matches, usable string ormID, string type, null parentOrmID; no write acceptance inferred | Unknown; no family wildcard |
| By-ID lookup | D 99-107 | Documented SitePojo read candidate; native-ID correspondence and primary live response unqualified | Not qualified by Default read; returned-new-ID readback still unverified | Unknown |
| Site create/name+parent | U 152-175; public example corroborates | Legacy intent, not target-tested schema. Parent/root acceptance, unknown-field omission, result/async contract unqualified | Same unqualified write candidate; root read does not prove create compatibility | Unknown; public testing through 10.5.0 is not 10.x certification |
| Child-Site parent binding | D 110-142 then U parent lookup | Order/name dependency observed, destination created-ID/readback contract missing | Same dependency; no child create performed | Unknown |
| Device enrichment/create/association | D 145-157; U 177-202 | Device read/create documented subsets do not qualify full access/type/identity semantics; destination IDs required | No Device compatibility established by root/Site evidence | Unknown |
| Device update | X 152-184 | PUT source-observed only; independent destination identity mandatory | No write evidence | Unknown |

Use one shared contract-oriented implementation and per-exact-release evidence/
capability gates, not parallel CC1010/CC1015 code copies or numeric >=10
assumptions. Introduce a version-specific adapter only after an observed schema/
behavior difference requires it. Do not bypass current exact-version capability
gates or label all CC 10.10.x verified because it is the priority.

### Smallest safe next development step (proposal, not implemented)

**Mock-only one-Site candidate/readback contract rehearsal**, using existing
[source readiness](../src/cc_vision_import/vision_tree_preview.py),
[comparison](../src/cc_vision_import/site_comparison.py),
[identity mappings/dependency_order](../src/cc_vision_import/mappings.py),
[read response/request helpers](../src/cc_vision_import/product_clients.py) and
the existing exact-origin session/transport infrastructure. Existing lookup
helpers are capability/mock-gated, not authorization for new live reads.

- Keep all 30 source Sites/order, root confirmation and immutable input bindings.
  Selected source:node-2 has no intermediate Site dependency; 22 descendants
  still require future destination parent-ID resolution. No Device action.
- After separate development approval, add a focused offline assessment within
  the existing Site workflow, not an import engine/new deployment. Consume the
  existing selected report and protected evidence; expose source reference,
  candidate name/parent field provenance, exact target version and blockers,
  never a sendable body or native IDs in shared output.
- Reuse legacy name plus destination-parent projection, but require protected
  destination ormID from a validated mapping, not managedElementID alias/name
  fallback. A missing parent, unverified contract or duplicate mapping blocks.
- Rehearse a pure response/readback assessor with synthetic success/error/timeout
  and identity/hierarchy evidence. Require verified destination-ID resolution
  before a parent binding can release any child dependency; no automatic reads
  or broadened runtime allowlist. Keep completion unknown where contract unknown.
- First establish primary exact CC 10.10 patch/build and obtain applicable
  payload/parent/results/readback evidence. The successful 10.15.0-2 root read
  can exercise the common read design but is not primary-target qualification.
- A future one-create test still needs separate authorization for one controller,
  field set, reviewed name/parent, collision baseline, deadlines, readback and
  recovery. No automatic retry, blind rollback or second ambiguous create.
  All create features remain disabled here.

Recommended focused mocked cases, preferably extending existing Site comparison/
destination discovery tests rather than introducing a framework:

1. Parent/child/grandchild plus interleaved Device nodes: preserve existing
   source references, parent-before-child order, 30/0 counts and 22 dependencies.
   Shuffled/cyclic/duplicate/unknown parents block or order explicitly; never
   inherit legacy flat-array assumptions or process Devices.
2. Root-child uses only confirmed protected destination-root mapping; source
   dbId/ormID/managedElementID and artifact-local node refs rejected as destination
   values. Distinct lookup ormID/managedElementID never silently aliased.
3. Parent rejection, timeout/async-pending, failed/malformed/ambiguous name lookup
   keeps children/Devices blocked; zero fallback to root and no root rename.
4. Exactly name/destination parent are candidate fields, not target-qualified
   payload. All four source-field omission rules and unknown naming/type rules
   stay blocked until evidence; inputs remain byte/object immutable.
5. Hypothetical HTTP 200 without identity/completion stays unverified; explicit
   error, malformed JSON, contradictory readback, duplicate-name or wrong-parent
   response never becomes success. Ambiguous create yields no replay/rollback.
6. Exact target releases with absent evidence stay unqualified; common schema
   behavior uses the shared path. Existing 10.15 root evidence cannot unlock
   10.10 writes or a family-wide capability.
7. Existing TLS/session/credential cleanup and finite sanitized reports remain;
   no real dispatch, forbidden methods, arbitrary origin/path or leaked values.

Validation this task: read-only full source review and AST function-range
inspection (no legacy code imports/execution). Documentation-only change; no
runtime tests or controller requests needed. All reference/test proposals above
are future work, not new verified implementation.

## SITE-CREATE-API-QUALIFICATION - historical 10.15.0-2 evidence, writes blocked

Scope: qualify one future Organization Site create, not implement or authorize
writes. Existing discovery, comparison, Docker deployment and launcher remain
unchanged. The confirmed root association is not root identity equivalence.

### SINGLE-SITE-CONTRACT-EVIDENCE - official example versus target

Reviewed 2026-11-26, without executing or copying the external application:

- Radware-published [cloner source, main](https://github.com/Radware/Cyber-Controller-Sites-and-Devices-Cloner/blob/main/copy_cyber_controller_objects.py),
  specifically `get_parent_site_id` and the root/Site portions of `main`.
  [Raw source](https://raw.githubusercontent.com/Radware/Cyber-Controller-Sites-and-Devices-Cloner/refs/heads/main/copy_cyber_controller_objects.py)
  was inspected because the HTML file view omitted source content.
- [Repository README](https://github.com/Radware/Cyber-Controller-Sites-and-Devices-Cloner#readme)
  reports testing from Vision 4.85 through CC 10.5.0 and instructs GUI refresh/
  verification. This is published example coverage, not certification of every
  intermediate version or of target CC 10.15.0-2.
- References address mutable `main`, not a pinned release/commit; no commit
  identity or target write result was obtained. Radware publication strengthens
  provenance of the example, not its target applicability. Existing approved
  PDFs still do not document the exact Site POST.

| Contract point | Radware published example | Repository legacy uploader | CC 10.15.0-2 evidence / remaining gate |
| --- | --- | --- | --- |
| Method/path/body | Site loop POST `/mgmt/system/config/tree/site`; JSON name and parentOrmID | Same method/path and two fields | Corroborated example construction, not target-verified create schema or minimal-field sufficiency. |
| Parent resolution | `get_parent_site_id` reads destination by-name response ormID | Helper prefers destination managedElementID, falls back to ormID | Live Default GET yielded usable destination ormID. Do not copy legacy preference or assume identifier equivalence; POST acceptance still unverified. |
| Root handling | `main` PUT-renames destination root to source name if different; failed parent lookup falls back to tree managedElementID | Failed parent lookup also falls back to root; selected uploader loop does not qualify that choice | Both behaviors prohibited. Preserve confirmed Bell Canada -> Default association without rename; unresolved parent blocks. Default's own parent null does not authorize child parent null. |
| Four source fields | Site request omits data, both child counters and meIdentifier.dbId | Same omissions | Independent source examples, not proof of target optionality/server generation. Existing four-field matrix remains unqualified for omission; source identity reuse forbidden. |
| Allowed values/tree semantics | Uses source name and destination parent result; no complete validator | Same incomplete field checks | Name grammar/length/case, duplicates, allowed parents/root IDs and Organization placement require target evidence. |
| Success | HTTP 200 considered success; no successful Site body parsing | Same | No target write performed; do not promote legacy HTTP check into verified creation. |
| Error/timeout | Assumes failure JSON message; no explicit bounded timeout on Site POST | Assumes JSON message; no complete result contract | Neither establishes exhaustive errors, no-mutation semantics, completion or safe replay. Never print raw messages or adopt unbounded calls. |
| Destination created identity | Does not extract newly created Site identity | Does not extract it | Target returned ormID/authoritative identity-resolution contract required; no source-ID reuse. |
| Completion/readback | No per-Site post-create readback/completion check; README asks operator GUI verification | None in create loop | Target by-ID/hierarchy verification and any async completion protocol still required; GUI visibility alone is not full API acceptance evidence. |
| Release coverage | README's upper tested release CC 10.5.0 | Legacy target intent alone gives no 10.15 qualification | GUI version 10.15.0-2 and live Default GET are established owner evidence only for that read, not POST. |

#### Sanitized single-Site request assessment - NOT a sendable request

This descriptor intentionally has no request body or substituted native values.
Protected references below describe future local resolution, not existing
profile keys, API values, executable templates or an enabled import format.
The successful sanitized root report contains no recoverable native ormID;
future use requires protected destination evidence or a separately approved
fresh root read, not an identifier reconstructed from a report.

```json
{
  "domain": "single-site-contract-evidence-preview",
  "execution_authorized": false,
  "configuration_writes_authorized": false,
  "import_file_compatible": false,
  "request_body_generated": false,
  "source_reference": "source:node-2",
  "source_parent_reference": "source:node-1",
  "mapped_destination_root_reference": "destination:node-1",
  "observed_method": "POST",
  "observed_path": "/mgmt/system/config/tree/site",
  "field_sources": {
    "name": {
      "protected_reference": "reviewed-bound-source-node-2-native-name",
      "transformation": "none",
      "target_allowed_value_contract": "unqualified"
    },
    "parentOrmID": {
      "protected_reference": "selected-destination-origin-validated-Default-lookup-ormID",
      "server_assigned_destination_identity_only": true,
      "native_value_included": false,
      "target_create_acceptance": "unqualified"
    }
  },
  "root_rename_allowed": false,
  "unresolved_parent_fallback_allowed": false,
  "source_identifier_reuse_allowed": false,
  "four_field_omission_contract": "unqualified",
  "creation_result_and_readback_contract": "unqualified"
}
```

#### Future test acceptance and failure requirements - approval gates

| Outcome/stage | Exact acceptance requirement / safe action |
| --- | --- |
| Before transmission | Approve exact target origin/account, selected bound Site/name, destination parent, qualified field set, collision baseline, response/identity protocol, readback endpoints and recovery owner. Predetermine numeric connect/read/overall deadlines and, if applicable, bounded completion polling interval/attempts from target-supported behavior. Missing limits or contracts block execution, not trigger defaults. |
| Success response | Match target-qualified HTTP status and application success/body/header schema; validate returned destination identity or evidenced authoritative resolution mechanism. Legacy HTTP 200 alone is insufficient; an undocumented 201/202 or bodyless response is not automatically accepted. Keep result pending until completion and readback pass. |
| Explicit error | Static sanitized category/status only in shared reports; protected local evidence for investigation. Do not assume even 4xx/5xx guarantees no mutation without contract/readback evidence. Stop; no resubmission or automatic corrective write. |
| Timeout/disconnect/unparseable or contradictory result | Treat as indeterminate whenever server execution cannot be excluded. No automatic retries, second create, fallback parent or blind delete/rollback. Only separately approved read-only reconciliation can resolve outcome. Definite pre-send failure also requires review before any new attempt, not an automatic retry. |
| Async response | Accept only an evidenced job/operation mechanism with qualified terminal states and bounded read polling. Do not invent status endpoints, follow arbitrary response URLs or equate HTTP acceptance with completion. Deadline expiry leaves indeterminate status. |
| Readback | Target-qualified by-ID lookup using new destination identity; exact local checks for name, parent identity and supported type plus Organization hierarchy/placement versus baseline. Name-only match or root GET is insufficient; missing/duplicate/conflicting objects remain unresolved. No automatic write follows a readback failure. |
| Verified test outcome | Only after qualified terminal success and consistent identity/hierarchy readback: report one test Site verified, not bulk migration ready. Keep native values/credentials/tokens/raw bodies out of logs/reports; no Device/child/root changes. |
| Recovery | No blind rollback. Any deletion/correction requires distinct authorization, proven ownership/identity, reviewed dependencies and evidence; never infer that approval from the one-create approval. |

**Smallest remaining evidence/approval:** target-applicable clarification that
the two-field Site body is valid (or its exact additional required fields), that
the destination Default ormID is an allowed Organization parent, and that the
four omitted fields are server-managed/optional or otherwise accounted for;
plus the target success/error/identity/completion/readback contract and a fresh
collision baseline. An existing approved 10.15 transaction with authoritative
schema clarification can supply evidence; the older public example alone cannot.
Then request one explicitly scoped create and its bounded readback, not general
write enablement. If static evidence cannot settle a particular semantic, obtain
an explicit vendor-supported experimental test protocol acknowledging that
uncertainty; no such approval is inferred here. Existing application has no
Site-create capability, and its root-only allowlist remains unchanged.

### Compatibility matrix

| Question | Exact evidence | Qualification for CC 10.15.0-2 |
| --- | --- | --- |
| Create method/path | [Legacy uploader](../legacy/app/upload_cybercontroller_objects.py), lines 162-168: POST `/mgmt/system/config/tree/site` with JSON; corroborated by Radware's public cloner above | Published example plus local source evidence. API-07 is absent from both reviewed PDFs; 10.15.0-2 support remains unqualified, not proven unsupported. |
| Create payload | Uploader lines 162-165 and Radware public cloner submit only `name` and `parentOrmID` | Corroborated field construction, not a target-qualified list of required/allowed fields, types, defaults or nullability. No complete create schema established. |
| Parent reference | Uploader lines 86-105: GET `/mgmt/system/config/tree/site/byname/{parent_site_name}`, then prefer `meIdentifier.managedElementID`, otherwise `ormID` | Name is a lookup input, not the submitted parent field. A returned destination identifier is submitted as `parentOrmID`; the two identifier types' equivalence is unqualified. Never substitute a source ID. |
| Root parent | Uploader lines 146-160: GET `/mgmt/system/config/tree/{tree_type}`, take `meIdentifier.managedElementID`; failed/falsy parent lookup falls back to that root | Root-ID acceptance in `parentOrmID` is unqualified. The silent fallback is unsafe and must not be adopted. A confirmed Bell Canada -> Default association does not qualify the Default identifier for POST. |
| Live Default lookup | Owner-reported successful GET `/mgmt/system/config/tree/site/byname/Default` on GUI-identified CC 10.15.0-2; name match true; usable string ormID; string type; null parentOrmID; exit 0; no configuration writes | Destination-native candidate identity is observed, not a source ID or artifact reference. Actual type value, create-parent acceptance, uniqueness/root correspondence and create contract remain unqualified. Null describes the root's own parent, not the parent field for a new child Site. |
| Source projection | Uploader lines 154-165 consumes source `name` and `parent_site_name`; existing source-readiness projection distinguishes source `id`/`parentOrmID` | Preserve `name` unchanged only conditionally, pending target naming/collision rules. Source `parent_site_name` is dependency evidence, not a create field. Source `id`/`parentOrmID` are not destination identifiers. |
| Other fields | Lookup `SitePojo`, V/C PDF 255 (printed 245): required strings `ormID`, `name`, `type`; optional strings `description`, `parentOrmID` | Lookup-model Required flags do not qualify create fields. Do not add `ormID`, `type`, `description`, tree selectors or unknown fields from this model. Unprojected source fields remain unchanged and unresolved, not silently discarded as irrelevant. |
| Creation response/identity | Uploader lines 169-175 considers only HTTP 200 successful; no success-body parsing or returned-ID extraction | Success statuses, response schema, destination identity field, asynchronous completion and failure contracts unknown. HTTP acceptance alone cannot prove creation. No automatic write retry. |
| Readback | API-05: GET `/mgmt/system/config/tree/site/byid/{id}`, V/C PDF 146 (printed 136), ID described as server `ormID`; API-04 by-name lookup also documented | Candidate readback paths, not target-qualified verification. By-ID requires an evidenced returned destination identity. By-name alone cannot prove unique identity/parent or completion; its documentation has an unresolved extra `id` parameter. |
| Hierarchy verification | API-03 Organization GET is legacy-observed and used by current read-only discovery. Snapshot projection retains `native`, `reference`, `observed_container_parent`, parent relationship and issue codes | Future readback must verify one destination native identity, unchanged reviewed name, intended root/parent and Organization placement against baseline. Tree/lookup identity correspondence and enumeration completeness remain unqualified. |
| Site update | [Legacy updater](../legacy/app/update_cybercontroller_objects.py), lines 143-191 updates Devices via PUT `/mgmt/system/config/tree/device` | This updater supplies no Site-update operation or contract; do not infer PUT Site support from Device behavior. Devices are excluded from this task. |
| Target version | Owner GUI observation: 10.15.0-2. Discovery reports installed version unknown/unverified. Reviewed CC PDF is 10.10.7-labelled with conflicting 10.10.6 metadata | No target-specific Site-create, parent identity, response or completion qualification. Prior PDF evidence and successful read-only discovery do not certify writes on this target. |

### Additional root evidence and four unresolved fields

Owner supplies additional Radware evidence: GET
`/mgmt/system/config/tree/site/byname/Default` can return `ormID`, `name`, `type`
and `parentOrmID`. A destination server-assigned root `ormID` is the candidate
create-parent identifier, never the Vision root ID or `destination:node-1`.
The subsequent owner-reported live lookup succeeded with exact Default name,
usable string ormID, string type and present-null parentOrmID, exit 0 and no
configuration writes. This is observed target read evidence, not proof that
POST accepts this root identifier. Version 10.15.0-2 remains GUI-observed, not
API-discovered. No native identifier value was supplied or recorded here.

The protected snapshots exist only on the Linux destination. No root response
was inspected here. Current discovery projection
(`destination_discovery.py:216-239`) retains name, managed-element identity/class
and optional parentOrmID, **not top-level ormID or type**. Therefore their absence
in the projected snapshot cannot prove absence in the server response. Comparison
reprojection also does not establish either field. No equality between
managedElementID and ormID is assumed.

| Evidence item | Current qualification |
| --- | --- |
| Intended root name | Live lookup name matched Default, owner-reported. Name alone does not establish uniqueness or equality with earlier tree identity. |
| Root type | Live lookup type is a string; expected value/root semantics unqualified. No type enum is inferred. |
| Root ormID | Live lookup returned usable string, owner-reported; destination-native candidate identity. Correspondence to earlier tree identity and acceptance as child create parentOrmID unverified. |
| Root parentOrmID | Present null in live lookup. This is the root's own parent relationship; never copy null as the new child's parent. |
| Four source fields | Real Linux diagnostic succeeded with source SHA-256 binding/root/candidate checks; paths/types classified below. Required/optional/create omission rules remain unknown. |
| Future identity/readback | Need target create success/error and returned server-ID contract, then by-ID readback matching reviewed name, expected parent ormID and Organization placement. By-name root read alone does not qualify creation/completion. |

Owner-reported Linux inspection: exactly one Default name match; name present
as str; type, ormID, managedElementID and parentOrmID absent from the inspected
root representation. This is snapshot-representation evidence only. Discovery
stores the native name at `organization_root.native.name` and managed identity
at `organization_root.native.meIdentifier.managedElementID`, not directly on the
root record. The supplied results do not establish which nesting level was
inspected; do not infer server absence, valid native identity or root-ID equality.
The later live lookup supersedes this earlier snapshot-only limitation for
lookup field presence/types, but does not qualify any create-parent acceptance.

### SITE-CREATE-CONTRACT-QUALIFICATION - real diagnostic and contract gate

Evidence provenance: owner reports the existing source-only diagnostic completed
on the Linux destination against the real protected Vision backup and confirmed
comparison report. Source SHA-256 binding, confirmed root mapping and
`source:node-2` selection passed there. This workstation received only sanitized
field-path/type results; it did not rerun Linux extraction or inspect native
values. Source/destination IDs remain separate and protected inputs unchanged.

| Actual field path | Observed evidence | Interpretation, not established target semantics | Target Site-create classification and remaining evidence |
| --- | --- | --- | --- |
| `source:node-2.data` | Python NoneType / JSON null | Opaque field with null in this one record; null is not evidence that it is irrelevant, optional or defaulted | **Unqualified/unsupported by available create evidence**, not proven rejected by the product. Required versus optional unknown. Need meaning, nullability and omission/default behavior before approving omission; never replace unknown configuration with a guessed value. |
| `source:node-2.dynamicViewChildrenNumber` | Python int / JSON number; value not supplied | Name suggests a derived dynamic-view child count; neither derivation nor configuration relevance is proven | **Derived candidate only; create support/requiredness unqualified.** Need target evidence that server computes it or omission is valid; no source count copying, zeroing or assumptions about contained Devices. |
| `source:node-2.totalChildrenNumber` | Python int / JSON number; value not supplied | Name suggests an aggregate child count; definition, scope and derivation unknown | **Derived candidate only; create support/requiredness unqualified.** Need server-managed/omission evidence and scope definition; do not copy source hierarchy counters into a destination Site. |
| `source:node-2.meIdentifier.dbId` | Python int / JSON number; value not supplied. Existing V/C ManagedElementIdentifierPojo PDF 243/printed 233 lists optional integer(int64) dbId in that model | Likely source-local persistence identity metadata. The model optional flag does not specify Site-create behavior or cross-controller identity | **Source identifier, prohibited for destination-ID reuse; target create support/requiredness unqualified.** Need target-managed identity/allowed-field contract. Do not send source dbId, ormID or managedElementID, even if a target field has the same spelling/type. |

None of the four fields is established as required, optional or safely omittable
for target POST Site. They are absent from the legacy two-field request, which
is evidence of client construction only, not a tested omission contract on this
release. Unknown omission rules remain explicit blockers; no Device processing
or source identity migration is implied by these field classifications.

Legacy reinspection confirms only `name` and destination-resolved `parentOrmID`
are submitted. It supplies no allowed-name grammar/length/case normalization,
tree-selection rule, required `type`, nullability/default schema, created-ID
extraction or post-create verification. The supplied PDFs do not document this
POST. SitePojo lookup required flags cannot fill the gap. Existing root read and
source diagnostic add no target write-contract evidence.

### Single-Site validation plan - sanitized and NON-EXECUTABLE

Scope: one real root-child `source:node-2`, source parent `source:node-1`,
operator-confirmed association to `destination:node-1`. No intermediate Site
dependency; no root creation/rename, Device association or bulk execution.

1. **Contract gate, still blocked:** obtain target-applicable vendor contract or
   an already authorized sanitized target transaction with schema clarification
   for exact Site POST, allowed/required fields and values, four-field omission/
   server-generation behavior and Organization placement. Confirm destination
   root ormID is accepted as new child's parentOrmID. Do not use the legacy
   managedElementID preference/root fallback or set child parent to null.
2. **Identity gate:** preserve immutable source bindings. Resolve the reviewed
   source name only within protected inputs; no name transformation. Resolve
   destination root identity only within the selected destination origin/session
   and approved evidence. A native value must never be replaced with
   `source:node-1`, `destination:node-1`, or a source identifier.
3. **Collision/baseline gate:** refresh/review authorized destination evidence for
   that exact name and intended parent, including case/normalization, namespace,
   uniqueness, permissions and not-found semantics. Zero Sites in the earlier
   incomplete projection does not prove absence; a successful root lookup adds
   no Site enumeration. Duplicate-name groups zero means only none in the saved
   projection. Ambiguous/error/not-authorized is not "not found". Qualify the
   intended readback coverage rather than asserting global enumeration.
4. **Separate authorization gate:** only after gates 1-3 and response/completion
   evidence below, request approval for one named controller, reviewed Site,
   parent, payload field set, maintenance window, account and recovery procedure.
   Current application cannot execute creation; a future bounded write mechanism
   and any required read allowlist changes need their own explicit approval.
5. **Smallest future lab transaction (description only):** one Site-create
   submission, no retry/replay, using only the qualified unchanged name and
   destination-native parent plus any additional contract-required fields.
   Stop on rejection, timeout or indeterminate result. Do not repeat a possibly
   successful create, attach Devices, or create children.
6. **Returned identity/completion gate:** require documented success/error
   statuses and body/headers, created destination ormID or an authoritative
   identity-resolution mechanism, and synchronous/asynchronous semantics. If
   asynchronous, require the exact evidenced completion read, terminal states,
   bounded polling and timeout behavior; do not invent a job endpoint.
7. **Readback acceptance:** after the one authorized create, use target-qualified
   by-ID lookup for the newly assigned destination identity (API-05 candidate)
   and approved hierarchy evidence. Confirm usable destination identity,
   unchanged reviewed name/type and parent matching the protected destination
   root ormID, intended Organization placement and absence of unexpected changes
   against baseline. By-name alone cannot distinguish a pre-existing duplicate;
   by-ID GET alone need not prove tree placement. Actual equality checks stay
   local; reports expose only booleans/types and provenance.
8. **Failure/recovery:** contradictory, missing or timed-out completion/readback
   leaves status indeterminate/failed, not migration-ready. Escalate for manual
   review using protected evidence. Recovery/deletion is separately authorized,
   never an automatic cleanup write. Close/clear sessions and temporary
   credentials through the existing security lifecycle.

This plan does not generate an HTTP body, enable a capability or authorize a
write/readback request. Root-only mode still permits just login and Default GET;
it does not currently permit Site-create, by-ID readback or generic polling.

Field classification after local key/type extraction: source-specific identity,
version or runtime metadata must not be copied without portability evidence;
configuration fields require target create optionality/default/preservation
evidence; hierarchy fields require explicit destination mapping; opaque/nested
fields remain blocked pending schema evidence. These are classification rules,
**not findings about the four unknown fields**. Even `type` is excluded from the
preview's unknown count by the source parser but is not thereby create-qualified.

### Standalone offline extraction on the destination (no host Python)

Run from the standard checkout using the existing shared Compose image. Set
these three variables to the actual saved container-visible paths; the comparison
must be the original report containing the two whole-input bindings. The command
uses network-none, UID 10001 and existing mounts, makes no writes, and prints only
match/presence results and the selected Site's unknown field paths/types. Reports
are already writable in Compose, but this helper opens all inputs read-only.
If Docker access needs approved sudo, authenticate normally; do not change
permissions or run the application as root to bypass an input permission error.

```bash
SOURCE=/incoming/vision-backup-20261125T122823Z-3ad1c37f503d/organization-tree/tree.json
SNAPSHOT=/reports/cc-destination-20261126T001502Z-c71a84af2691/organization-sites.json
COMPARISON=/reports/source-destination-site-comparison.json
# Adjust SNAPSHOT and COMPARISON to the actual existing saved files.
docker compose --profile destination run --rm -T --entrypoint python \
  ccv-destination -B - "$SOURCE" "$SNAPSHOT" "$COMPARISON" <<'PY'
import hashlib
import json
import sys
from pathlib import Path
from cc_vision_import.capabilities import ProductClientError
from cc_vision_import.contracts import ContractValidationError
from cc_vision_import.site_comparison import _destination
from cc_vision_import.vision_tree_preview import _tree_rows, inspect_site_migration_readiness

def require(condition):
    if not condition:
        raise ValueError("Evidence check failed")

def read(path):
    raw = Path(path).read_bytes()
    return raw, json.loads(raw)

def main():
    require(len(sys.argv) == 4)
    source_raw, source = read(sys.argv[1])
    snapshot_raw, snapshot = read(sys.argv[2])
    _, report = read(sys.argv[3])
    require(report.get("domain") == "source-destination-site-comparison-report")
    require(report.get("execution_authorized") is False)
    require(report.get("configuration_writes_authorized") is False)
    for slot, raw in (("source-organization-tree", source_raw),
                      ("destination-organization-sites", snapshot_raw)):
        bindings = [b for b in report["input_bindings"] if b["slot"] == slot]
        require(len(bindings) == 1)
        require(bindings[0]["sha256"] == hashlib.sha256(raw).hexdigest())
    readiness = inspect_site_migration_readiness(source)
    _, root, _ = _destination(snapshot)
    mapping = report["root_mapping"]
    require(mapping["status"] == "confirmed" and mapping["operator_confirmed"] is True)
    require(mapping["source_reference"] == "source:" + readiness["root_assessment"]["reference"])
    require(mapping["destination_reference"] == "destination:" + root["reference"])
    records = [r for r in report["site_comparisons"] if r["source_reference"] == "source:node-2"]
    require(len(records) == 1)
    record = records[0]
    require(record["classification"] == "candidate_for_creation")
    require(record["source_order_eligible"] is True and record["missing_source_fields"] == [])
    require(record["source_parent_reference"] == mapping["source_reference"])
    require(record["observed_source_container_parent"] == mapping["source_reference"])
    require(record["parent_destination_reference_candidate"] == mapping["destination_reference"])
    require(record["requires_destination_identity_from_source_parent"] is None)
    candidates = [r for r in readiness["site_candidates"] if r["reference"] == "node-2"]
    require(len(candidates) == 1 and candidates[0]["source_order_eligible"] is True)
    row = _tree_rows(source["tree"])[1]
    identifier = row.get("meIdentifier", {})
    known = {"meIdentifier", "children", "name", "type", "managementIp", "parentOrmID"}
    fields = [(key, row[key]) for key in sorted(set(row) - known)]
    fields += [("meIdentifier." + key, identifier[key]) for key in
               sorted(set(identifier) - {"managedElementID", "managedElementClass"})]
    require(len(fields) == record["unprojected_source_field_count"] == 4)
    json_types = {str: "string", int: "number", float: "number", bool: "boolean",
                  dict: "object", list: "array", type(None): "null"}
    native = root["native"]
    root_identifier = native["meIdentifier"]
    print(json.dumps({
        "root_checks": {
            "name_matches_Default": native.get("name") == "Default",
            "managedElementClass_matches_Site": root_identifier.get("managedElementClass")
                == "com.radware.insite.model.device.Site",
            "type_present_in_snapshot": "type" in native,
            "type_match": "unverified_expected_lookup_type_not_qualified",
            "ormID_present_in_snapshot": "ormID" in native,
            "managedElementID_present_in_snapshot": "managedElementID" in root_identifier,
            "managedElementID_usable": isinstance(root_identifier.get("managedElementID"), str)
                and bool(root_identifier["managedElementID"].strip())
        },
        "unprojected_fields": [
            {"path": "source:node-2." + key, "python_type": type(value).__name__,
             "json_type": json_types[type(value)]} for key, value in fields
        ]
    }, indent=2))
    require(native.get("name") == "Default")
    require(root_identifier.get("managedElementClass") == "com.radware.insite.model.device.Site")

try:
    main()
except (OSError, ValueError, KeyError, TypeError, IndexError, RecursionError,
        ContractValidationError, ProductClientError) as error:
    print("Offline extraction failed: " + type(error).__name__
          + ". Check permissions, JSON shape, input bindings and root evidence locally.",
          file=sys.stderr)
    sys.exit(1)
PY
```

Numbering exactly follows the source parser's depth-first traversal of **all**
nodes, including Devices; `_tree_rows(...)[1]` is native node-2, not the second
Site in a filtered array. Unknown paths use the same top-level/identifier
exclusion sets as `inspect_vision_tree`, not the narrower legacy create payload.
No child values or nested unknown values are printed. Missing projected ormID
is reported only as missing in this snapshot, never missing on the controller.

### Pending source-only inspection (independent of destination root fields)

The four real field paths/types have not been supplied. They cannot be derived
from the sanitized count or inspected on this workstation. Run the following
source-only variant on Linux: it does not depend on the destination root having
a managedElementID, unlike the combined command above. Set COMPARISON to the
actual original comparison report; input bytes must match its source binding.
No controller credentials, network or host Python are required.

```bash
SOURCE=/incoming/vision-backup-20261125T122823Z-3ad1c37f503d/organization-tree/tree.json
COMPARISON=/reports/source-destination-site-comparison.json
docker compose --profile destination run --rm -T --entrypoint python \
  ccv-destination -B - "$SOURCE" "$COMPARISON" <<'PY'
import hashlib
import json
import sys
from pathlib import Path
from cc_vision_import.contracts import ContractValidationError
from cc_vision_import.vision_tree_preview import _tree_rows, inspect_site_migration_readiness

def require(condition):
    if not condition:
        raise ValueError("Source evidence check failed")

def main():
    require(len(sys.argv) == 3)
    raw = Path(sys.argv[1]).read_bytes()
    source = json.loads(raw)
    report = json.loads(Path(sys.argv[2]).read_bytes())
    require(report.get("domain") == "source-destination-site-comparison-report")
    require(report.get("execution_authorized") is False)
    require(report.get("configuration_writes_authorized") is False)
    bindings = [b for b in report["input_bindings"] if b["slot"] == "source-organization-tree"]
    require(len(bindings) == 1 and bindings[0]["sha256"] == hashlib.sha256(raw).hexdigest())
    readiness = inspect_site_migration_readiness(source)
    mapping = report["root_mapping"]
    require(mapping["status"] == "confirmed" and mapping["operator_confirmed"] is True)
    require(mapping["source_reference"] == "source:" + readiness["root_assessment"]["reference"])
    records = [r for r in report["site_comparisons"] if r["source_reference"] == "source:node-2"]
    require(len(records) == 1)
    record = records[0]
    require(record["classification"] == "candidate_for_creation")
    require(record["source_order_eligible"] is True and record["missing_source_fields"] == [])
    require(record["source_parent_reference"] == mapping["source_reference"])
    require(record["observed_source_container_parent"] == mapping["source_reference"])
    require(record["parent_destination_reference_candidate"] == mapping["destination_reference"])
    require(record["requires_destination_identity_from_source_parent"] is None)
    candidates = [r for r in readiness["site_candidates"] if r["reference"] == "node-2"]
    require(len(candidates) == 1 and candidates[0]["source_order_eligible"] is True)
    require(candidates[0]["source_parent_reference"] == readiness["root_assessment"]["reference"])
    row = _tree_rows(source["tree"])[1]
    identifier = row.get("meIdentifier", {})
    known = {"meIdentifier", "children", "name", "type", "managementIp", "parentOrmID"}
    fields = [(key, row[key]) for key in sorted(set(row) - known)]
    fields += [("meIdentifier." + key, identifier[key]) for key in
               sorted(set(identifier) - {"managedElementID", "managedElementClass"})]
    require(len(fields) == record["unprojected_source_field_count"] == 4)
    types = {str: "string", int: "number", float: "number", bool: "boolean",
             dict: "object", list: "array", type(None): "null"}
    print(json.dumps({"unprojected_fields": [
        {"path": "source:node-2." + key, "python_type": type(value).__name__,
         "json_type": types[type(value)]} for key, value in fields
    ]}, indent=2))

try:
    main()
except (OSError, ValueError, KeyError, TypeError, IndexError, RecursionError,
        ContractValidationError) as error:
    print("Source inspection failed: " + type(error).__name__
          + ". Check local permissions, JSON shape, source binding and selected reference.",
          file=sys.stderr)
    sys.exit(1)
PY
```

Return only this field-path/type output for classification. The command is an
offline inspection, not completion evidence until run on the real hash-bound
source. No field value or native identifier is printed.
Source-only helper validation passed: Python/Bash syntax and synthetic execution
for four fields including a nested identifier field, Python/JSON types,
no native value output, unchanged inputs and sanitized hash-mismatch failure.
Real source inspection remains pending; proposed live lookup tests remain unrun.

### Implemented root-only lookup - offline mock qualification only

Current enforcement is `DestinationAuthorization` exact `(method, target)` plus
normalized HTTPS origin/443 (`http_backend.py:99-127`). Discovery `_backend`
permits only:

- POST `/mgmt/system/user/login` (existing authentication, not configuration).
- GET `/mgmt/system/config/tree/Organization`.

The default pair list is unchanged. Explicitly selected root-only
mode permits **only** existing login plus GET
`/mgmt/system/config/tree/site/byname/Default`; no automatic Organization GET,
by-ID GET, arbitrary name/path/query, redirects or additional write capability.
Configuration POST, PUT, PATCH and DELETE remain disabled. Existing login POST
must remain for session establishment; zero POST of any kind would prevent reuse
of current authentication.

| Implemented file change | Minimal purpose |
| --- | --- |
| `destination_discovery.py` | Add default-false `qualify_default_root` selector to runner/backend. Root-only allowlist, one GET after validated login, strict bounded JSON validation and sanitized field assessment. Retain default tree-only path and snapshot format unchanged. |
| `master_cli.py` | Optional `--qualify-default-root`, valid only with existing destination-discovery operation; no arbitrary lookup target or user-supplied expected type. Pass explicit boolean to runner. |
| `compose_entrypoint.py` | Accept/forward this flag only for discovery/discover-sites, retaining private credential/profile setup and cleanup. |
| `ccv.sh` | Optional explicit qualification flag forwarded only for menu choice 2, including the existing approved pre-auth TLS retry. Reject other role selections with the flag. Keep menu/default workflows, secret handling and cleanup unchanged. |
| `http_backend.py` | Existing unverified discovery TLS guard accepts either the exact login/tree pair or exact login/Default pair, never their union or arbitrary endpoints. Necessary for the existing session-only root-mode TLS consent; normal verified transport/origin enforcement remains unchanged. |
| `launcher_helper.py` | Validate and display only finite field-presence/type/identity assessments and the sanitized report path; no raw identifier values. Preserve pre-auth certificate prompt eligibility and cleanup. |
| Existing discovery/launcher/Compose tests | Focused mocked cases listed below; no new framework. |

No Dockerfile, Compose service/network, authentication, TLS policy module,
generic transport policy or source collector change. The flag is now available
as `./ccv.sh --qualify-default-root` (choose 2); existing menu/defaults unchanged.

Use `_DiscoveryAuthentication` and `SessionManager` unchanged: validated
application login status/session identifier, exact destination scope, HTTPS/443,
10/30/60-second timeouts, zero read retries, existing bounded response limit,
trusted CA and default verified TLS. Preserve production exception lock and
single-origin/current-execution approval; no unverified authentication before
consent, automatic downgrade or restart after authentication. Always clear
strategy/session state on success/failure. Network policy remains administrator
managed; an application allowlist does not replace egress filtering.

Implemented response assessment contract:

- Require HTTP 200 and strict JSON object; reject duplicate keys, invalid JSON,
  application error status and unsupported envelope/array shapes, without logging
  bodies or guessing a nested wrapper.
- For exactly `ormID`, `name`, `type`, `parentOrmID`, emit only `present`,
  JSON/Python type from a finite type map and a static `usable` outcome.
  Absent is distinct from null, empty and wrong type. No dynamic error text,
  field values, identifiers, arbitrary unknown keys or API headers in reports.
- Require name to be usable string exactly Default (no normalization), and
  ormID to be usable nonempty printable string. Missing/wrong/mismatched evidence
  yields explicit partial/blocked result, never qualified success.
- Emit `name_matches_Default`. Emit `type_match=unverified` until vendor evidence
  establishes expected root type; do not invent a Site/root enum or equate
  managedElementClass with type. parentOrmID presence/type can be assessed, but
  allowed root-parent absence/null/value remains unverified.
- Native ormID is server-assigned candidate identity, not `destination:node-1`.
  Do not persist the value in this sanitized report. Return
  `root_correspondence=unverified` where immutable prior identity evidence is
  absent; a name match alone is insufficient. Keep
  `site_create_parent_acceptance=unverified`, `migration_ready=false` and
  `configuration_writes_authorized=false` even with valid name/ormID.
- Write only a distinct sanitized root-qualification report under existing
  destination-reports, exclusive create, not a tree/import snapshot. Record
  request method/path, collection time and existing sanitized TLS scope.

Mocked acceptance cases:

1. Default discovery still makes only login/Organization GET and unchanged
   snapshots; explicitly selected root mode makes only login/Default GET.
2. Reject other origins, ports, schemes, names, query/path variants, by-ID/tree
   requests in root mode and all configuration writes before opening a connection.
3. Valid lookup emits finite presence/type/usability/name-match results only.
   Missing/null/empty/wrong-type ormID/name/type/parentOrmID, name mismatch,
   error JSON, duplicate keys, malformed/oversized JSON, arrays and non-200
   responses fail or remain blocked with static sanitized issue codes.
4. Credentials, cookies, tokens, native IDs, response fields/headers/error bodies
   never appear in stdout/stderr or saved report; reports stay non-importable.
5. Failed/HTTP-200-only login does not permit lookup. Cookie/session cleanup on
   success, authentication/transport/validation/output failure and interruption.
6. Trusted TLS needs no prompt; untrusted fails closed; explicit lab approval
   retries only pre-auth for same origin/execution; rejection/production lock
   prohibits lookup. No post-auth retry or cross-origin exception reuse.
7. CLI/Compose reject flag on other operations/roles; launcher menu and cleanup
   preserved; source-only helper validates traversal/count/binding and never
   prints native values. No mocked root result enables parent-ID or write readiness.

### Authorized runtime validation - not executed during development

First run the offline extraction; inspect any separately saved protected lookup
evidence before requesting again. If no such evidence exists, propose exactly
one authenticated GET `/mgmt/system/config/tree/site/byname/Default` through the
existing discovery session. Require successful JSON, exact name Default, usable
server ormID and qualified expected type/root parent semantics. Correlate with
the saved Organization root using evidenced identity rules; equal names or two
present identifiers are not proof of equivalence. Report booleans/match outcomes
only, retaining any native identifiers exclusively in protected local evidence.

The discovery backend now selects login/Organization or login/Default according
to the explicit flag, with no shared union. Implementation/mock tests are
authorized; live execution still needs controller authorization. Reuse existing credentials,
verified-first session-only TLS consent and administrator egress restrictions;
no new service, fallback curl, TLS bypass or broad endpoint authorization.
No live network request or deployment was performed during implementation.
Sanitized root results cannot be substituted for the Organization snapshot or
used as an import artifact; no native ormID value is retained in this report.

Exact operator commands, after approved checkout provisioning:

```sh
cd /opt/radware/storage/scripts/CC--Vision-Core-Config-Import-Components
docker compose --profile destination-discovery config --quiet
docker compose --profile destination-discovery build ccv-destination-discovery
./ccv.sh --qualify-default-root
```

Select 2. Existing credentials/CA/TLS exception and private temporary-file cleanup
are reused. The one-shot container exits and is removed. A sanitized
`cc-destination-*/root-qualification.json` remains under destination-reports.
Exit 0 means Default name/usable candidate ormID observed, not create-qualified;
partial evidence exits 1. No new installation procedure or image.

Helper verification on Windows: Python compilation and Git Bash syntax passed.
Synthetic offline inputs exercised four field paths/types (including an
identifier subfield), Default root matching, projected ormID absence, suppression
of native IDs/values, unchanged input bytes and hash-mismatch failure with a
sanitized error. These fixtures do not identify the real four fields. Actual
Linux/Docker execution and protected-root matching remain unverified.

Root-mode implementation verification: 139 launcher/HTTP backend/transport/TLS/
comparison regressions passed in 427.770s. Final destination/Compose and added
root-lock/leakage checks: 31 tests in 33.689s, 30 passed and one Docker availability
skip. Combined final coverage: 170 tests, 169 passed, one skip; no real dispatch.
Five runtime AST checks, launcher and 25 documented shell blocks passed.
Four runtime Pylance files have no diagnostics; backend has unused-code hints,
no error/warning diagnostics. The first shell-block scanner incorrectly consumed
indented Markdown closing fences; corrected bounded fence extraction passed
without changing the existing runbook. Docker/controller validation remains
unverified. No live calls, deployment, Git writes or Site-create activation.

### Single-Site request preview - NON-EXECUTABLE, genuine root-child selected

Evidence: owner-attached sanitized report
`C:\CCV-Evidence\site-comparison-confirmed-20261126.json`, root mapping at lines
36-46, selected record at lines 101-121 and input bindings at lines 766-775.
Select `source:node-2`, the first eligible root-child in the saved source order.
Its explicit and observed parent references both equal confirmed source root
`source:node-1`; its proposed destination parent is confirmed root
`destination:node-1`. It has a source identity, no missing source fields, is
source-orderable and requires no future destination identity from a source
parent Site. Eight report records meet these root-child selection checks.

Selection is sufficient for this qualification preview, **not for execution**.
The Site retains four unprojected fields and three issue codes shown below.
Zero discovered destination Sites is not verified absence or complete
enumeration. The destination root also has five unprojected fields. Artifact-local
references are not native IDs and must never be sent as `parentOrmID`.
This JSON describes field assessments, not a request body; null version evidence
is unknown evidence, not a value to send.

```json
{
  "domain": "site-create-qualification-preview",
  "status": "blocked",
  "execution_authorized": false,
  "configuration_writes_authorized": false,
  "import_file_compatible": false,
  "target": {
    "product": "cyber-controller",
    "gui_observed_version": "10.15.0-2",
    "api_verified_version": null
  },
  "snapshot_provenance": {
    "source_product": "vision",
    "source_version": "5.4.9",
    "source_collected_at": "2026-11-25T12:28:29.852332+00:00",
    "destination_collected_at": "2026-11-26T00:15:02.139394+00:00",
    "complete_destination_site_enumeration": false
  },
  "observed_legacy_operation": {
    "method": "POST",
    "path": "/mgmt/system/config/tree/site",
    "target_contract_qualified": false
  },
  "selection": {
    "status": "selected_genuine_root_child_for_qualification_only",
    "source_reference": "source:node-2",
    "source_parent_reference": "source:node-1",
    "observed_source_container_parent": "source:node-1",
    "source_parent_relationship": "inferred-from-legacy-nesting",
    "destination_root_reference": "destination:node-1",
    "root_association": "operator-confirmed-not-identity-equivalence",
    "classification": "candidate_for_creation",
    "source_identity_present": true,
    "source_order_eligible": true,
    "missing_source_fields": [],
    "destination_candidates": [],
    "destination_identity_assigned": false,
    "requires_destination_identity_from_source_parent": null,
    "unprojected_source_field_count": 4,
    "issue_codes": [
      "absence_in_incomplete_snapshot_not_verified_absence",
      "additional_site_fields_not_projected",
      "unknown_fields_unverified"
    ]
  },
  "input_bindings": [
    {
      "slot": "source-organization-tree",
      "sha256": "5d7e911b1d72c59d8265eace3684ea1a556bd4491f8393f4650e539613cafcee"
    },
    {
      "slot": "destination-organization-sites",
      "sha256": "8b36ad23bbabb235317996fe0ec325b4a47932a6d0725475f9f3a0e4047feb26"
    }
  ],
  "field_assessments": [
    {
      "field": "name",
      "value_included": false,
      "status": "conditional_unchanged_source_name_target_rules_unqualified"
    },
    {
      "field": "parentOrmID",
      "value_included": false,
      "status": "blocked_destination_root_identifier_contract_unqualified"
    }
  ],
  "request_body_generated": false,
  "root_parent_qualification": {
    "candidate_identifier_kind": "destination_server_assigned_ormID",
    "candidate_lookup": "GET /mgmt/system/config/tree/site/byname/Default",
    "native_identifier_value_included": false,
    "saved_root_ormID_presence": "unverified_projector_does_not_retain_field",
    "live_lookup_evidence": {
      "basis": "owner-reported-live-CC-10.15.0-2-GUI-observed",
      "name_matches_Default": true,
      "ormID_present": true,
      "ormID_type": "string",
      "ormID_usable": true,
      "type_present": true,
      "type_json_type": "string",
      "parentOrmID_present": true,
      "parentOrmID_json_type": "null",
      "exit_status": 0,
      "configuration_writes_occurred": false
    },
    "managedElementID_equals_ormID": "unverified_not_assumed",
    "lookup_name_type_root_correspondence": "unverified",
    "post_parentOrmID_acceptance": "unverified"
  },
  "unprojected_fields": {
    "count": 4,
    "extraction_basis": "owner-reported-real-Linux-diagnostic-source-binding-root-selection-validated",
    "fields": [
      {"path": "source:node-2.data", "python_type": "NoneType", "json_type": "null", "interpretation": "opaque-null-semantics-unqualified"},
      {"path": "source:node-2.dynamicViewChildrenNumber", "python_type": "int", "json_type": "number", "interpretation": "derived-count-candidate-not-proven"},
      {"path": "source:node-2.totalChildrenNumber", "python_type": "int", "json_type": "number", "interpretation": "derived-count-candidate-not-proven"},
      {"path": "source:node-2.meIdentifier.dbId", "python_type": "int", "json_type": "number", "interpretation": "source-identity-metadata-candidate-no-destination-reuse"}
    ],
    "target_required_optional_and_omission_contract": "unqualified-for-all-four-fields"
  },
  "returned_destination_identity_contract": "unqualified",
  "readback_and_completion_contract": "unqualified",
  "devices_processed": false
}
```

Both whole-input bindings are copied exactly from the sanitized report and pass
64-character hexadecimal SHA-256 syntax checks here. Owner reports the source
binding was additionally validated against the real backup on Linux. Neither
binding was independently recomputed on this workstation; destination binding
revalidation was not reported. This is not an independent authenticity check.
No native IDs, names, credentials or raw configuration values are needed to
establish this reference-based selection.

### Smallest remaining prerequisite before a separately authorized lab test

Obtain target-applicable vendor evidence for POST Site: accepted/required fields,
the exact destination root identifier accepted by `parentOrmID`, success/error
and returned-identity schema, plus a completion/readback contract. An approved,
sanitized existing target transaction may supplement that evidence; this task
does not authorize capturing one through a new write. Resolve the selected
root-child's now-identified four fields' target omission/requiredness rules and
naming/parent collision checks from the actual bound inputs. Then seek separate approval for one create and readback,
with least-privilege access, a fresh reviewed baseline and a documented recovery
procedure. Do not enable bulk creation or infer permission to delete.

Verification: source/document inspection, offline JSON parsing, root-child
selection predicates, binding syntax checks and evidence-file SHA-256 before/
after read (unchanged). No reusable Python validation was added, so no new tests
or regression run were needed. Documented preview JSON parses and its selected
reference/parent/classification/order/unknown count and bindings match supplied
evidence; non-executable guards remain false. No legacy
execution, live calls, configuration writes, deployment or Git operations.

## SITE-MIGRATION-READINESS - source Sites only

Implemented `tree-readiness-preview --site-readiness` using the existing native
Vision envelope validator, source containment/dependency checks, local input
reader, safe text/JSON reports and exclusive report writer. Organization only;
no device/access inputs or associations, credentials, API calls or executable
payloads. The report has a distinct domain, no top-level sites/devices arrays
and is rejected by the existing controller import-artifact parser.

Legacy evidence: `legacy/app/upload_cybercontroller_objects.py:143-175` reads
sites in supplied order, consumes name and parent_site_name, resolves the latter
using destination Site lookup, then submits name plus destination parent ID.
Flat source id and parentOrmID are not read by this Site-create loop. Original
downloader traversal establishes their separate source-reference roles.

| Legacy field | Supported source-side preparation | Qualification boundary |
| --- | --- | --- |
| name | Direct native name, unchanged; nonempty printable text required | Destination allowed names, normalization/case rules and collisions unverified |
| id | Rename meIdentifier.managedElementID to conceptual flat source id; require usable unique identity | No alias to destination ormID; no actual flat import object emitted |
| parentOrmID | Derive containing Site/root native source ID when dependency is unambiguous | Source nesting inference only; not a destination parent ID; conflicting explicit parents block instead of reparenting |
| parent_site_name | Derive observed containing Site/root name | Original downloader obtains this via Site-by-ID lookup; equivalence to the observed tree name and destination lookup behavior remains unqualified |

Real Organization result: 30 Site candidates; 30 have sufficient source fields;
zero missing source-field records or unresolved parent dependencies. All 30 are
orderable from the single source Site-root context in observed depth-first,
parent-before-child order. Zero duplicate source Site names or ambiguous exact
parent-name candidates. All 30 have additional fields outside the legacy
projection; these remain unqualified and untouched in the source backup.
The root's identity/name/class are structurally usable, but its semantic root
role remains legacy-inferred. It is not emitted as a Site candidate.

Source-field sufficiency and source ordering do not imply migration readiness.
All 30 Sites and the root require explicit destination mapping/resolution.
Missing fields, duplicate IDs, unknown parents, conflicting explicit references
and invalid root context block source ordering where appropriate; duplicate
names are reported separately from valid source hierarchy. No global-name
fallback, source-ID reuse, automatic root rename or unsupported field deletion.
Enumeration completeness, native parent semantics and exact destination
Site/create/lookup schemas remain unqualified. Source ordering is not a
destination write plan.

Verification: 127 existing/focused offline tests passed in 34.491 seconds
(tree preview, inventory reconciliation, controller exports/workflow, Vision
backup and setup). Five new Site tests cover valid projection/ordering,
unprojected fields, name ambiguity, missing/duplicate identities, parent/root
blockers, safe text/JSON, non-importability, exclusive output and unchanged
inputs. Pylance syntax checks passed for all three changed Python files; both
changed source files have empty diagnostics. The real source assessment ran
under network guards, verified every reported parent-before-child dependency,
and confirmed the original backup hash unchanged with zero network attempts.

Smallest next step: an authorized offline destination Site/root snapshot and
exact CC version/build/schema evidence, followed by an explicit root/Site
mapping and collision-resolution preview. Qualify parent-name lookup scope and
missing/duplicate behavior; do not activate creation or treat source IDs as
destination identities. No new device identity investigation is required.

## Device-access association qualification - offline evidence only

Authorized inputs: Organization tree and the 36 controller-detail plus 36 access
artifacts in the owner's local backup directory. All 73 files were inspected
read-only under existing network guards; before/after hashes matched and zero
network attempts occurred. Only aggregate counts/static labels were displayed.
No native tree/detail identifiers were compared across namespaces.

### Source contract and saved provenance

- Original downloader `extract_device_access_data` (repository reference
  `legacy/app/download_cybercontroller_objects.py:145-157`) queries
  GET `/mgmt/system/config/tree/device/byip/{ip}` using the tree managementIp,
  extracts deviceSetup.deviceAccess, deletes the access object's ormID, then
  attaches it to the first flat device with that managementIp. It does not
  verify the tree managedElementID against the detail ormID. This is observed
  address-based behavior, not an explicit native identity-equivalence contract.
- Current collector (`src/cc_vision_import/vision_backup.py:329-365`) makes one
  detail read and writes both outputs from the same result. Access objects are
  projected as `{ormID: detail.ormID, deviceAccess: detail.deviceSetup.deviceAccess}`;
  access-envelope ormID is therefore a copied device ID, not an independently
  observed access ID or a newly established alias for tree managedElementID.
  The nested access object's own ormID is preserved with its separate role.
- All 36 pairs match that exact projection and every other envelope field
  except domain/objects, including source, timestamp, request, evidence,
  identity-binding assertion, scope, redaction count and issues. All source
  declarations also match the tree's declaration. Pairing compared all records,
  not filenames, names, list positions or equal device IDs alone.
- Both artifact groups record the expected distinct domains, GET by-IP template
  and queried-management-IP/unique-response-ID binding assertion. The client
  checks query/address consistency and rejects duplicate response IDs across
  different queries (`src/cc_vision_import/product_clients.py:435-503`).
  This protects query binding, not tree identity. Matching saved metadata is
  derivation-consistent provenance, not signed/raw-response attestation or
  proof of an atomic tree/detail snapshot.
- Detail and access objects contain no ormId/meIdentifier/managedElementID
  fields. Each group has 36 unique top-level device IDs. Reviewed API-06 and
  Device/DeviceSetup/DeviceAccess/ManagedElementIdentifierPojo documentation
  establishes the read and nested access data, not a detail-to-tree ID alias.

### Association results (candidate and unresolved counts overlap)

| Layer / classification | Count | Interpretation |
| --- | ---: | --- |
| Confirmed collector-derivation-consistent detail/access pairs | 36 | Unique exact projection plus matching provenance; no filename-based pairing |
| Unpaired detail / access artifacts | 0 / 0 | All inputs have a unique derivation-consistent counterpart |
| Ambiguous detail / access pairings | 0 / 0 | No multiple counterparts under that projection/provenance check |
| Confirmed Organization-to-access identity associations | 0 established | Does not mean there is no real overlap |
| Address-only candidate Organization-to-pair associations | 35 | Each tree device has exactly one recorded query-target candidate; explicitly not identity proof or approved enrichment |
| Multiple candidates per tree / pairs shared by candidate tree records | 0 / 0 | No candidate-level fan-out observed; this does not verify identities |
| Tree devices without an address-only candidate | 0 | A candidate is not a confirmed match |
| Detail/access pairs without a tree address candidate | 1 | Not identified as a missing tree device; exclusion cause remains unknown |
| Unresolved Organization-to-access identity associations | 35 | Every tree-device enrichment remains blocked |

All 36 access artifacts have null/masked credential fields: 540 recognized fields
in total. Redaction counts are copied from the full detail result, not an
independently scoped access count; do not sum both artifact groups as separate
redactions. The projection preserves redaction and cannot supply restorable
credentials. Access/schema completeness, credential portability and exact target
version behavior remain unverified.

Exact missing evidence: an authoritative source API statement, or an authorized
same-device response with documented field roles, binding Organization
meIdentifier.managedElementID to the by-IP Device ormID within the relevant
controller/snapshot scope. Alternatively, a documented tree-native identity
binding to that same lookup result is needed. A shared IP/name, equal IDs,
source-label match or another copy of the current responses is insufficient.
No new endpoint is proposed.

Smallest next implementation step, after that evidence is supplied: add a
report-only association check to the existing compatibility preview that requires
the qualified native binding plus unique projection/provenance and reports
conflicts/missing evidence without merging payloads. Until then, retain the
35 candidates as unresolved. No application code/check was added, so no new
tests or redundant unchanged-code regression suite were run for this assessment.

## Legacy cc-objects flat compatibility - offline preview

Evidence: original `app/README.md` and the four named scripts under the owner's
original migration workspace; all four scripts are byte-identical to the
read-only repository copies. Existing original flat files were inspected without
printing configuration values: Physical has empty sites/devices; Organization
has 29 sites and 34 devices. These are a different snapshot, not evidence that
the current 30-site/35-device native tree should lose any records.

| Contract or behavior | Source-observed result / preview boundary |
| --- | --- |
| Original output | Exact top-level `sites`/`devices` arrays. All sampled sites have name/id/parent_site_name/parentOrmID; all sampled devices have name/type/managementIp/id/parentOrmID/deviceAccess. All 34 sampled devices have access objects. Master envelopes instead contain native `tree`; they are not uploader inputs. |
| Identity and nesting | Downloader derives flat id from meIdentifier.managedElementID and source parentOrmID from containing tree node; sites are depth-first, parent before child. Root is not emitted. No inventory/alldevices identity crosswalk is used. Preview retains only opaque references to unchanged source nodes, not replacement IDs. |
| Access enrichment | Original GET device/byip followed by deviceSetup.deviceAccess extraction and deletion of access ormID. Preview performs no reads/enrichment/deletion or association by IP/name/equal IDs; native access availability and credential gaps only are assessed. |
| Order and hierarchy | Physical then Organization; sites before devices in each. Uploader resolves parent names with destination GET site/byname, then POST site or device. Missing parent resolution silently falls back to root in legacy; explicitly not adopted. Duplicate global site names are flagged. |
| Root rename | README claims root renaming; reviewed uploader has no corresponding rename/write operation. It reads destination tree root, does not create/export source root, and uses root fallback. Root rename remains unsupported, not inferred. |
| Creates and IDs | POST `/mgmt/system/config/tree/site` uses destination parent ID/name. POST `/mgmt/system/config/tree/device` uses name/destination parent/type/access, not source device id. No created-ID mapping/read-back/completion verification exists. Server ID assignment is expected, not target-live-qualified here. |
| Updates | PUT `/mgmt/system/config/tree/device` sends flat device id as ormID. README explicitly requires a download from the same controller for update. Source IDs must never be treated as destination update IDs. Physical file precedes updated Organization file. |
| Models/versions | README lists physical/virtual Alteon and DefensePro and claims tests across Vision 4.85 through CC 10.7.0. Reviewed code simply forwards type/access; no qualified model/form-factor conversion or version matrix. This is not exact-target compatibility proof. |
| Credentials | Credential helper replaces CLI/HTTP/HTTPS username/password by old-username lookup, and SNMPv3 username/auth/privacy secrets from supplied mappings. Actual helper reads `snmpsecrets.ini`, unlike README's snmpcredentials.ini wording. It writes cleartext and logs usernames; not reused or executed. Missing/redacted credentials cannot be recovered from backups. |

Implemented `tree-readiness-preview --legacy-compatibility`: always blocked,
offline-only report; no flat sites/devices output, destination objects, import
payloads, credentials or changes. Existing controller import parser rejects this
report. Reuses envelope validation, inferred source dependencies, local strict
JSON/exclusive reports and sensitive-field classification. Unknown fields/classes,
missing flat fields, ambiguous names, access gaps and unqualified transformations
remain explicit; no native fields are silently rewritten.

Actual guarded current-tree assessment: Physical root only (zero flat candidates);
Organization 30 site and 35 device candidates, with 35 missing deviceAccess and
35 credential-gap records. Source tree files hash-unchanged; zero network attempts.
The 36/35 inventory difference does not block this selected tree subset, but
its cause and full device coverage remain unresolved.

Verification: 122 offline preview/reconciliation/controller/backup/launcher
regressions passed, including five focused compatibility tests. Pylance syntax
checks passed for the three changed Python files; changed source diagnostics
were empty. No legacy script, live API, import, deployment or Git operation ran.

Smallest next step: qualify an explicit, independently evidenced tree-device to
saved access-artifact association, plus destination root/site-resolution rules,
before any enrichment preview. Do not copy the legacy IP merge as identity proof.

## Native device identity crosswalk - artifacts supplied, bridge still unverified

The earlier missing-artifact blocker is superseded: all 36 original detail
envelopes were subsequently supplied and inspected offline. They have 36 unique
top-level ormID identities but no ormId, meIdentifier or managedElementID fields
anywhere. externalId and parentOrmID are null in all 36; physicalParentId is empty
in 35 and null in one. Nested setup/access ormID fields have independent roles.
No native dual-namespace bridge was established. No address/name/order/equal-ID
matching was performed; the specific cause of 36 inventory versus 35 tree
devices remains unknown. Required evidence is an authoritative same-device
association between the actual native identity namespaces, not more copies of
these responses. This blocks an inventory crosswalk, not tree-subset assessment.

## Offline inventory reconciliation - VISION-INVENTORY-RECONCILIATION (2026-11-25)

Authorized inputs only: controller-objects/inventory.json,
organization-tree/tree.json and physical-tree/tree.json under the owner's
local backup directory. Inspected allowlisted schema field types before
reconciliation; no native values or unknown field names were displayed.
No other operational input, controller request or live operation was used.

### Observed local results (not a completeness claim)

| Representation | Records / hierarchy candidates | Identity checks | Parent/site observations |
| --- | --- | --- | --- |
| Managed inventory | 36 records | 36 unique native ormId strings; zero missing or duplicate identities | All 36 parentOrmId fields null/absent; no usable inventory parent linkage |
| Organization | 1 root candidate, 30 sites, 35 devices, zero unknown node classes | 35 unique device managedElementID strings; zero missing or duplicate device identities | 35 recognized direct site-containment associations across 20 site candidates; zero unresolved structural dependency issues in the current preview checks |
| Physical | 1 root candidate, zero devices/sites below root | No device identities to compare | No device placement supplied by this tree |

These are actual local observations, not synthetic counts. Structural checks
do not certify vendor schema completeness, source snapshot atomicity, parent
semantics or migration readiness.

### Identity reconciliation boundary

Inventory exposes `ormId`; tree nodes expose
`meIdentifier.managedElementID` (and separately typed dbId metadata). Existing
Vision/legacy evidence establishes these fields independently, not their equality
or a crosswalk. The legacy by-address merge is not a verified identity rule.
No names, addresses, string coincidences, dbId conversions, detail-ID aliases or
identifier suffixes were used to match devices.

- Verified cross-representation matches: **0 established**, not proof of no overlap.
- Inventory-only and tree-only identity sets: **unresolved**, represented as null
  rather than fabricated empty sets or a claimed one-device difference.
- Unresolved cross-representation records: all 36 inventory and 35 Organization
  device candidates. Cross-namespace ambiguity is distinct from within-set
  duplicates (none observed).
- The 36 versus 35 discrepancy is real at the record/class-count level but its
  identity-level cause is **not established** by these files plus current evidence.
  Zero structural parent problems does not resolve inventory/tree identity linkage.

### Implementation and next smallest task

[Standalone reconciler](../src/cc_vision_import/inventory_reconciliation.py)
reuses the existing Vision tree preview and strict local input/report helpers.
Source declarations must agree; tree slots/domains/GETs are checked. Duplicates,
missing identities, site containment and unresolved dependency issues use only
opaque positional references in output. The collector, auth, HTTP, launcher and
master operations remain unchanged. Safe JSON output is optional/exclusive;
status 1 explicitly indicates the identity bridge remains unverified.

Next task: obtain authoritative field-equivalence evidence or approve an
explicit independently reviewed offline identity-association contract; only then
add a one-to-one inventory/tree matcher with duplicate/collision/missing mapping
checks. Do not select an allegedly missing device through name/IP equality.
No live request, import, placement change or destination mapping is proposed.

Verification: 55 guarded offline reconciliation/preview/backup/launcher
regressions passed in 55.067 seconds; final added inventory-parent reporting
passed all four focused reconciliation cases (overlap, not additional tests).
Cases cover equal cross-namespace IDs not matching, duplicates/missing identity,
unresolved parents, invalid/swapped/provenance inputs, nonlocal path rejection,
safe JSON/exclusive output and unchanged inputs. Syntax/Pylance checks passed.
Actual local reconciliation also ran under the existing network guards with
zero attempted network calls; before/after hashes confirmed all three original
backups unchanged. Safe report contains no native operational values.

## VISION-TREE-READINESS-PREVIEW - implemented offline bridge (2026-11-25)

Owner-authorized extension of the proposed source readiness assessment to both
existing Vision Physical/Organization tree envelopes. No actual lab artifact
was supplied for local inspection; implementation is synthetic-offline verified,
not a new live-schema certification.

- [Preview implementation](../src/cc_vision_import/vision_tree_preview.py) accepts
  local schema_version 1, Vision 5.4.9 source provenance, the matching tree domain/
  recorded exact GET, incomplete evidence-only scope, native `tree`, and consistent
  top-level count/redaction metadata. It never expects an `objects` artifact.
  Unknown extra envelope/node/identifier fields are counted without exposing names
  or values; their semantics remain unverified.
- Structural evidence: [legacy traversal](../legacy/app/download_cybercontroller_objects.py)
  lines 110-142 consumes children arrays, meIdentifier.managedElementID and the
  explicit Site/Device managed-element classes. A single object root is a
  position-based root candidate; array entries are not guessed roots.
- `children` membership is an observed JSON containment relationship. Source
  parent/dependency interpretation is marked legacy-based inference, not
  vendor-verified hierarchy. The report deliberately records zero verified
  semantic parent relationships. Only unique known child identities with a
  unique root/site parent can receive an inferred dependency. Unknown/device
  parent roles and missing/duplicate identities remain unresolved.
- Explicit parentOrmID is inspected as a legacy field candidate, without
  treating other aliases as equivalent. Null/unknown/ambiguous references or
  conflicts with containment are blockers and clear the inferred dependency.
  Native identity and unknown configuration fields are not copied into output.
  Source device type/access and tree/detail identity associations remain unverified.
- Meaningful counts distinguish top-level JSON records from inspected root/site/
  device/unknown node candidates. Unknown/non-object nodes and unsupported child
  shapes are not silently normalized into a complete hierarchy. Depth is bounded
  at 64 and candidate count at 10,000.
- Reused: strict local input/JSON handling, ContractReader validation, existing
  dependency_order and exclusive local report writer. Synthetic CC adapters,
  migration artifact product/version gates and production capability catalogue
  are unchanged; no Vision-to-CC relabeling, destination mappings, semantic
  acknowledgements or import actions.
- CLI: `master.py --operation tree-readiness-preview --input <local tree.json>`,
  text by default; optional `--report-format json` and `--output <new report.json>`.
  Reports are safe counts/opaque node references/static issue codes. Inspection
  returns status 1 (readiness blocked), local I/O failures 3 and malformed
  envelopes/preview-limit violations 4. Existing CLI JSON and collectors unchanged.
- Verification: 89 guarded offline tests passed in 36.356 seconds across
  test_vision_tree_preview, test_vision_backup, test_backup_setup and
  test_controller_workflow. Six focused preview tests cover both envelopes,
  parent inference/conflicts, duplicates/missing/unknown fields and nodes,
  array/opaque shapes, malformed envelope/strict JSON/nonlocal paths/depth limit,
  safe text/JSON output, report overwrite rejection and original input preservation.
  Preview/master syntax and Pylance error diagnostics passed. No network attempts,
  live requests, imports, deployment or Git operations.

This implements a source evidence bridge only. Destination inventory/schema/
mapping contracts, credentials and exact-target compatibility remain blockers
to any later comparison or execution. The earlier single-Physical proposal below
is superseded only by this approved two-tree offline scope.

## Vision-to-Cyber Controller migration readiness assessment - 2026-11-25

Scope: six live-validated Vision 5.4.9 backup modules, existing offline code and
legacy import references only. Owner also confirms the interactive summary works.
No operational backup files or destination snapshot were supplied for this
assessment; native field presence in the lab exports is therefore not verified
by source inspection. No live requests, import execution or capability activation.
An exact Cyber Controller destination release/build must still be declared and
qualified; the historical CC PDF provenance conflict remains unresolved.

Classification:

- **Supported** means an evidenced, qualified destination migration path usable
  with these exports. **None of the six currently meets this definition.**
- **Transformation required** means a legacy CC operation candidate exists, but
  source adaptation/mappings are necessary; this is not import approval.
- **Unsupported** means no established CC import implementation in this project,
  not a claim that the vendor cannot support the feature.
- **Unverified** marks unresolved product/version/request/response semantics,
  and can apply alongside a transformation-required candidate.

### Source-to-destination capability matrix

| Vision export | Classification | Verified legacy destination intent | Required transformation/dependencies and current blockers |
| --- | --- | --- | --- |
| Controller objects | Transformation required; CC execution unverified | [CC uploader](../legacy/app/upload_cybercontroller_objects.py) lines 143-202 creates sites with POST /mgmt/system/config/tree/site and devices with POST /mgmt/system/config/tree/device. [Updater](../legacy/app/update_cybercontroller_objects.py) lines 143-184 uses device PUT. | Master inventory/detail envelopes are not the uploader's flat sites/devices input. Need explicit source root/site/device identities, parent graph, destination root/parent/device mappings, supported device type and qualified field selection. Thin ormId and detail ormID are not proven equivalent. Discovery/detail reads do not prove complete site configuration. Create completion/returned IDs and PUT semantics unverified. |
| Device access | Transformation required; CC execution unverified | CC device-create/update payload embeds deviceSetup.deviceAccess; there is no independent legacy access import operation. | Attach access to an explicitly associated device, not by first IP/name match. Preserve nested identity provenance without treating access ormID as a destination device ID. Need secure replacement of required redacted credentials, destination access-field/types/ownership qualification and device dependencies. A redacted export cannot be passed directly to the legacy payload. |
| LDAP permissions | Unsupported CC import; unverified destination API/schema | [LDAP uploader](../legacy/upload_ldap_permissions%20(1).py) lines 10-39 targets Vision and POSTs ldapobjectpermission; not a CC implementation. | CC endpoint/version contract absent. Need directory/group/role/network-policy mappings, qualified attribute semantics and any required secure values. Vision role/group equality is not CC permission equivalence. Forced locking, defaults and all-scope retries in the legacy uploader must not be reused. |
| Physical tree | Transformation required for root/site/device subset; whole-tree import unsupported; CC execution unverified | CC uploader lines 143-202 reads the destination Physical root, then creates flat sites/devices. No native whole-tree POST/import contract. | Extract only evidenced node classes from the native tree while preserving provenance/parent order; unknown classes/fields are blockers, not discarded configuration. Explicit destination root mapping first, then parent sites, then devices. Native root/children/identifier schema of supplied live exports and complete hierarchy coverage remain unqualified. |
| Organization tree | Transformation required for root/site/device subset; whole-tree import unsupported; CC execution unverified | Same uploader selects Organization separately, lines 223-238; reuses site/device creation. | Independently qualify Organization schema/root/parents and destination object placement. No cross-tree merging or assumption that the same managed device should be created twice. Cross-tree identity, shared-device placement and exact write semantics are unresolved. |
| Scheduler | Unsupported CC import; unverified destination API/schema | Original Scheduler uploader in the external reference workspace targets Vision; its task POST is not CC evidence. Repository [copy](../legacy/upload_scheduler.py) records the same configurable-task intent. | Need CC task-type/read/create contracts plus device/site/policy reference mappings, activation/timezone behavior and required secrets. Do not transfer Vision task IDs or blindly remove ormID/taskStatus/jobstatus/previousFeedMd5 as a CC transformation. Task-name skipping is not migration identity. |

### Dependencies, IDs, credentials and missing information

1. **Hierarchy:** destination controller/root mapping -> parent sites in dependency
   order -> child sites/devices -> associated device access. Physical and
   Organization contexts stay separate. Root is mapped, never created as a site.
2. **Identifiers:** retain source controller/tree/kind/native-ID provenance;
   independently qualify destination IDs and mappings. The updater assigns the
   source exported device id to destination ormID: this is unsafe across
   controllers and is not a reusable mapping rule. Uploader fallback to the
   destination root and global site-name matching are likewise not acceptable.
3. **Credentials:** destination session credentials require separately approved
   provisioning for any future live stage. Persistent device usernames,
   passwords/passphrases, SNMP communities/auth/privacy keys and task-specific
   secrets may need secure re-entry where the destination requires them.
   Redaction counts do not identify required destination fields. Null/masked
   values must remain unresolved; session cookies/tokens are not restored.
4. **Missing inputs:** exact target release/build and permissions; qualified
   source tree node/field shapes; independent destination snapshot/root and
   explicit object mappings; device-type/access translation; verified required,
   optional/server-owned fields; completion/read-back behavior. LDAP/Scheduler
   additionally lack established CC APIs and reference/authorization semantics.
5. **No inferred completeness:** an absent destination object is not a CREATE
   candidate without independently established destination enumeration. HTTP
   acceptance is not asynchronous completion. A successful source backup does
   not authorize deletes, replacements or configuration writes.

### Existing offline functionality: reuse and boundaries

- [Strict local JSON input](../src/cc_vision_import/offline_inputs.py) and
  [contract validation](../src/cc_vision_import/_contract_validation.py) can be
  reused for a no-network input/report path. Existing backup envelopes must be
  recognized explicitly, not mistaken for controller migration artifacts.
- [Controller export adapters](../src/cc_vision_import/controller_exports.py)
  require synthetic version 0.0-test. [Controller artifact parsing](../src/cc_vision_import/controller_objects.py)
  requires product cyber-controller and normalized controller-objects records.
  The six real Vision backup envelopes do not satisfy these contracts. Never
  relabel Vision as CC or a live release as 0.0-test to bypass them.
- Existing hierarchy uniqueness/parent/cycle checks and identity ambiguity
  assessment are useful prior art once a narrowly qualified Vision preview
  representation exists. Unknown classes and missing parents must fail explicitly.
- [Mapping resolution](../src/cc_vision_import/controller_mapping.py) requires
  independent inventories, explicit same-kind/tree destination IDs and parent
  dependencies. [Device reconciliation](../src/cc_vision_import/controller_reconciliation.py)
  requires explicit associations; [access acknowledgements](../src/cc_vision_import/controller_access_policy.py)
  are identity/snapshot-bound and grant offline planning only, not credential
  completeness or import approval.
- [Planning validation](../src/cc_vision_import/controller_planning.py) checks
  mapping state, root resolution, collisions, hierarchy/dependencies, declared
  destination completeness and unresolved credentials. [Comparison](../src/cc_vision_import/controller_comparison.py)
  requires explicit semantic qualification and emits BLOCKED/CREATE/SKIP/CONFLICT,
  not an executable UPDATE path. [Offline orchestration](../src/cc_vision_import/controller_workflow.py)
  produces protected/redacted records with execution_authorized false; its
  manifest path is synthetic CC-only. None is a ready-to-use live Vision-to-CC bridge.
- [Production capability catalogue](../src/cc_vision_import/capabilities.py)
  remains empty. Backup-specific live validation does not activate generic CC
  migration reads/writes.

### Proposed next task: VISION-PHYSICAL-READINESS-PREVIEW

**Priority:** high. **Approval:** proposed, not implementation-authorized.
**Objective:** one local, non-executing structural readiness report for the saved
Physical tree root/site hierarchy, the subset directly evidenced by the legacy
CC site/device workflow. This is source assessment, not a destination diff or
import plan; no live destination inventory collection is needed.

**Inputs:** existing physical-tree/tree.json envelope and source product/version/
run provenance. Inspect only structural field names/types from an authorized
local sample; if unavailable, ask for the minimum sanitized root/children/
meIdentifier/site shape before binding the parser. Do not request credentials.

**Bounded implementation proposal:**

1. Validate the real Vision envelope, read its native tree without mutation,
   retain source context and establish only the observed root/site identity and
   nesting subset. Treat unknown/missing/null/inconsistent fields as reported
   blockers; never default IDs/parents or silently exclude other nodes.
2. Check duplicate native IDs, missing/conflicting parent relationships, cycles
   and ambiguous sibling names using existing validation/dependency mechanisms
   where their contracts permit. No source-to-destination matching by name/IP.
3. Report site dependency order plus unresolved destination-root/parent mappings,
   unknown semantics/fields and unsupported node counts. Device nodes are
   identified as deferred dependencies only, not enriched or credential-resolved.
4. Emit a safe machine-readable readiness report and concise counts with opaque
   object references, issue codes, completeness unverified and
   execution_authorized false. No API request, import payload, CREATE/UPDATE/
   DELETE recommendation, source-ID reuse or automatic mapping.

**Acceptance:** supplied valid hierarchy produces accurate site/dependency
counts; duplicate IDs/missing identity/unknown classes and incompatible shapes
produce explicit blockers; original backup files unchanged; no credentials,
addresses or raw configuration in the operator report; existing six collectors
and JSON workflows unchanged; focused existing-framework tests demonstrate zero
network attempts. No synthetic relabeling or capability-gate bypass.

**Later, separately approved work:** qualify a true Vision preview adapter and
independent target snapshot before integrating existing destination comparison/
planning. Qualify device/access transformations afterward. LDAP and Scheduler
remain blocked pending CC-specific contracts. This sequence follows verified
legacy root/site/device functionality rather than inventing whole-tree imports.

Verification for this assessment: source/document inspection only; no code
changed and no tests run (documentation-only task). Proposed preview remains
unimplemented and unverified.

## Operator backup coverage - Vision 5.4.9

Latest owner-reported authorized lab result: all six modules live-tested;
controller objects 36, device access 36, LDAP permission records 13, Physical
and Organization trees collected, Scheduler 23 tasks with 46 fields redacted,
zero reported collection failures. No lab request was made here. This supersedes
historical pending master-live-validation statements below for these exercised
reads only. It does **not** establish full configuration, schema completeness,
restorability, migration readiness or support for another product/version.

| Module | Collected and legacy comparison | Coverage/qualification limits |
| --- | --- | --- |
| Controller Objects | Documented managed-device thin inventory and supported site/device detail GETs. The [object downloader](../legacy/app/download_cybercontroller_objects.py) traverses tree sites/devices and flattens them; master preserves the thin discovery graph and qualified lookup data separately. Lab count: 36 device details. | Partial inventory/detail coverage; discovery is not a complete site configuration export. Thin inventory IDs are not assumed equal to detail IDs. Device query IP/response binding is checked, but full schema, empty-site coverage and complete enumeration are unqualified. |
| Device Access | Redacted deviceSetup.deviceAccess subset of the same device-detail GET. Legacy downloader lines 145-157 extracts this subset, deletes its ormID and joins by IP; master retains qualified native data without that deletion. Lab count: 36 access exports. | Not appliance configuration dumps or portable credential backups. Unknown nonsecret fields retained, exact-version field semantics/nullability and restoration prerequisites unqualified. |
| LDAP Permissions | Same fixed GET as the [LDAP downloader](../legacy/download_ldap_permissions%20(1).py); master exports records with the source-consumed attribute/role subset and unknown nonsecret fields. Lab count: 13 records. | Full LDAP schema, enumeration/pagination, external directory dependencies and cross-product mappings unqualified. No forced device locking, permission scope broadening or fabricated defaults. |
| Physical Tree | Same exact Physical GET as the object downloader; native response under `tree`, unlike legacy flattened sites/devices. Lab: collected. | Root/nesting/order/IDs/parents retained as received, subject to redaction; no node-schema or tree-identity qualification. Top-level JSON records are not hierarchy-node counts or proof of complete enumeration. |
| Organization Tree | Same independently selected Organization GET; separate native artifact rather than merged/flattened hierarchy. Lab: collected. | Same explicit opaque-export limits; shared parsing does not establish identical Physical/Organization schemas or shared-device identity semantics. |
| Scheduler | Same configured GET as the [Scheduler downloader](../legacy/download_scheduler.py), resolved from both supplied Scheduler INIs; array of task objects, retaining IDs, status and unknown fields instead of upload sanitization. Lab: 23 tasks, 46 fields redacted. | Full task types/schema, timezone/reference/dependency semantics, paging and complete enumeration unqualified. Successful task export does not establish recreation/activation behavior. |

### Restoration gaps and sensitive-data policy

- Existing recursive field-name redaction replaces credential-like values with
  null: usernames/security names, passwords/passphrases, SNMP communities,
  authentication/privacy keys, tokens/cookies/session IDs, private/API keys and
  related fields. Credential-valued LDAP attributes are also redacted.
- Where persistent credentials or identity fields are required to recreate a
  configuration, an authorized restoration workflow would need independently
  supplied, verified secure values. They cannot be reconstructed from nulls or
  masked server responses. Some redacted fields are transient session material
  and should be freshly authenticated, not restored.
- The Scheduler count of 46 describes redacted fields, not 46 distinct passwords
  or known restoration prerequisites. No task-by-task restoration field schema
  has been established. Terminal controller/access redaction totals describe
  source detail responses and overlap; do not sum them as distinct secrets.
  Inventory redactions remain in the inventory artifact, not that terminal total.
- Unknown fields may have unqualified sensitivity/semantics; field-name
  redaction is not a full secret-discovery guarantee. Protect every backup
  artifact as operationally sensitive even though known credentials are redacted.
- Native IDs and parents are retained for evidence, not certified portable
  destination mappings. Imports would need approved dependency, identity, TLS/
  trust, validation and verification contracts; none is implemented here.

### Unsupported or outside current coverage

No import/restore/update/delete operations, destination activation or live Cyber
Controller backup is supported. Complete appliance configuration downloads,
restorable credentials, vendor-wide schema/pagination certification and a complete
controller configuration inventory are not provided by these six modules.
Legacy credential transformation/upload scripts are references, not additional
backup coverage. Document-store restoration and Docker/cron/sleep utilities
remain outside the application modules. No endpoint is inferred for a missing domain.

### Operator output and offline verification

Menu-created backups show module status/count meaning/redaction scope and fixed
safe limitations, the exact host run directory and overall status. Unselected
modules say not requested; unavailable redaction counts are not shown as zero.
Raw JSON/body/issue-message data is not printed by the readable renderer.
The full summary artifact and existing profile/JSON/unattended output are unchanged.
Missing/invalid engine JSON is an explicit presentation failure, not a fabricated
successful report. Collection API calls, endpoints and transport are unchanged.

45 targeted guarded offline launcher/backup regressions passed in 40.629 seconds.
New tests cover concise six-module output including 23 tasks/46 redactions,
artifact preservation, partial failures, malformed output without raw echo,
exit-status behavior and unchanged JSON/profile/unattended stdout handling.
Host-launcher syntax checks passed; Pylance reports only its pre-existing
informational platform-dependent unreachable-code hint.

## Scheduler backup - VISION-SCHEDULER-BACKUP (2026-11-25)

Owner reports all five preceding modules live-validated on Vision 5.4.9:
36 controller-object devices, 36 device-access devices, 13 LDAP permission
records and both native trees collected. This supersedes their historical pending
master-validation status below for the exercised subsets, not complete schemas.
No live requests were executed here; Scheduler master behavior is offline-tested only.

- External reference workspace: owner-supplied `CC -Master Config Migration`.
  Root `download_scheduler.py` and `schedulertask/download_scheduler.py` are
  byte-identical. Both `scheduler_config.ini` copies independently declare
  `API.scheduler_endpoint = /mgmt/system/config/itemlist/scheduledtask` and the
  existing `/mgmt/system/user/login` login path. Only safe API-path values were
  extracted; credentials, hosts, ports and other operational settings were not copied.
- Downloader lines 11-14 read `config.ini` from the process working directory,
  not the supplied Scheduler INI filename or the script directory. The root
  workspace's existing `config.ini` is not a valid ConfigParser INI; the
  schedulertask directory has no sibling `config.ini`. Therefore the references
  are not executed as delivered. This naming/configuration mismatch does not
  make the two supplied, matching API path declarations ambiguous.
- Downloader lines 34-37 concatenate the configured path with the HTTPS origin;
  lines 42-71 use existing Vision JSON login, session cookies and Accept/
  Content-Type/X-Requested-With headers. Lines 96-118 issue GET with no body or
  query parameters, check HTTP success and serialize the returned JSON.
  The uploader's read-only `get_existing_tasks` reference, lines 91-108, expects
  an array of task objects with optionally consumed name fields. Its upload,
  field deletion and name-only skipping logic is not adopted or executed.
- Implemented contract: GET `/mgmt/system/config/itemlist/scheduledtask`,
  fixed to the source/INI-observed path in the Vision 5.4.9 backup adapter.
  No arbitrary API-path profile option or additional authentication is added.
  Existing authentication, HTTP, TLS, credentials and local session cleanup
  remain unchanged; no legacy session-ID logging or logout request is copied.
- Component 6 and Full Supported inclusion; Scheduler runs last. Scheduler-only
  skips device/LDAP/tree reads. Exact GET authorization, no query/body, no writes.
  Native array-of-object records are retained under `tasks` in scheduler/tasks.json
  with existing sensitive-field redaction. No mandatory name, ID, task type or
  wrapper is invented; valid empty arrays save zero records, malformed input fails.
- Independent Scheduler status/count/file/issues preserve earlier successful
  modules. Counts are saved array elements. Full schema, pagination/enumeration,
  timezone/reference/activation semantics, restoration and vendor-version-wide
  qualification remain unverified; migration capability catalogues stay closed.
- Verification: 118 guarded offline regressions passed in 85.472 seconds across
  Vision backup, host setup, product clients, mocked integration and controller
  workflow tests. New cases cover native/unknown/status/ID preservation, redaction,
  empty/malformed responses, cookies/headers/TLS, exact GET scope and explicit
  selection, skipped reads after login failure, Scheduler HTTP 401 independence,
  five-module preservation and successful Scheduler after unrelated failures.
  Initial run had one case-sensitive test header assertion error; corrected to
  HTTP case-insensitive comparison without changing production transport.
  Product-client syntax/error checks and backup error diagnostics passed.

This resolves the source/INI read-path blocker for CFG-03 only. Historical
missing-binding records below describe the earlier repository-only evidence;
they do not authorize CFG-04 writes or establish a complete Scheduler schema.

## Physical and Organization tree backup - VISION-TREE-BACKUP (2026-11-25)

Latest owner-reported Vision 5.4.9 baseline: 36 managed devices discovered,
36 controller-object exports, 36 device-access exports, 13 LDAP permission
records and zero failures. No live requests were executed here. This is evidence
for the existing selected backup subset, not full LDAP/schema completeness.
The owner's correction additionally confirms both exact tree GETs below:
HTTP 200 and valid tree JSON on the authorized Vision 5.4.9 lab. This supersedes
the preceding incorrect "untested/unknown" classification. No live requests were
executed here; the new master tree adapter has not yet been live-tested.

| Module | Exact source-observed read | Current Vision 5.4.9 status |
| --- | --- | --- |
| physical-tree | GET `/mgmt/system/config/tree/Physical` | Owner-reported live HTTP 200/valid JSON; opaque export implemented and offline-tested |
| organization-tree | GET `/mgmt/system/config/tree/Organization` | Independently owner-reported live HTTP 200/valid JSON; opaque export implemented and offline-tested |

Evidence and limits:

- [Legacy downloader](../legacy/app/download_cybercontroller_objects.py) lines
  180-185 issues GET and parses JSON; lines 212-216 select the two exact paths.
  The [cc-objects copy](../legacy/cc-objects/app/download_cybercontroller_objects.py)
  agrees. Legacy sources were read only, not imported or executed.
- Lines 110-142 consume a root object and recursive children arrays, node
  meIdentifier.managedElementClass/managedElementID and name; device nodes
  additionally use type/managementIp. These consumer assumptions do not
  establish the complete native fields, parent semantics, unknown node types,
  nullability or enumeration/pagination contract. The legacy flattened
  sites/devices output is not a native tree backup.
- The reviewed Vision PDF does not declare either exact GET (API-02/API-03
  below). Absence is not proof of vendor non-support, but CC-intent source and
  successful shared authentication alone are not Vision tree-read qualification.
- Corrected owner evidence qualifies both exact reads, not their complete
  schema. The master accepts opaque JSON object/array responses, preserves the
  native root/nesting/ordering/unknown fields and applies existing recursive
  credential redaction. It does not enforce the legacy consumer's guessed
  field types, flatten sites/devices or infer identifiers/parents.
- Both are selectable modules and included in Full Supported Backup. Exact
  GET authorization only; existing authentication/HTTP/TLS/session management
  unchanged. Tree-only skips device/LDAP collection. Separate module artifacts
  store native JSON in `tree`; per-module failures preserve successful exports.
- Counts are explicitly top-level JSON records (object root: one; array:
  element count), not hierarchy-node totals. Schema, tree identity binding,
  pagination/enumeration completeness and restoration remain unverified.
  Empty arrays remain native zero-record results; malformed/error responses
  fail, never become fabricated empty backups. Existing size/depth limits apply.
- New artifact evidence distinguishes owner-reported live endpoint verification,
  reviewed-PDF absence and master-live-untested status. The general migration
  capability catalogue and historical CC mock contracts are not activated.
- Verification: 113 guarded offline regressions passed in 47.432 seconds across
  backup, setup, product clients, mocked integration and controller workflows.
  New cases cover opaque object/array preservation, unknown/missing/nullable
  fields, redaction, exact GET scope, cookies/TLS, tree-only selection, empty and
  malformed responses, independent failures, and preservation of device/LDAP
  exports. Pylance source error diagnostics and syntax checks passed; host setup
  retains its existing informational platform-dependent unreachable-code hint.
  No new dependency, test framework, Docker or launcher-architecture changes.

The sections below retain their historical implementation-time verification
limits; the latest owner-reported device/LDAP result above supersedes their
pending lab-validation status only for the exercised backup subset.

## Device identity and source-observed LDAP backup - 2026-11-25

Owner reports the first successful Vision 5.4.9 backup: authenticated, 36
devices discovered, 36 controller-object and 36 device-access exports, 73 valid
module JSON files, zero failures. No new live requests were executed here.
The report covers the prior deployment, not this update.

Device detail queries now bind their response's documented
deviceSetup.deviceAccess.managementIp to the canonical queried IP, require
nonempty lookup ormID/name, and reject a reused ormID across distinct device
queries. Rejected targets produce no controller/access detail file. Diagnostics
use static missing/mismatch/duplicate codes, never addresses/IDs. Canonical
discovery IPs are deduplicated; no undocumented equivalence between thin ormId
and lookup ormID is assumed.

LDAP is enabled only as a **legacy-source-observed read-only list subset**:

- Request: GET /mgmt/system/config/itemlist/ldapobjectpermission, observed in
  [downloader](../legacy/download_ldap_permissions%20%281%29.py) lines 17-29,
  its [copy](../legacy/ldap_permissions/download_ldap_permissions%20%281%29.py),
  and [uploader reference](../legacy/upload_ldap_permissions%20%281%29.py)
  lines 14-32. Legacy sources are not imported or executed.
- Response qualification: array of objects with nonempty string attributeValue;
  present objectClassName/attributeName strings, and present roleGroupPairList
  array of groupName/roleName string objects. This is the subset exercised by
  existing GET/import source, not a fabricated complete vendor DTO.
- Unknown fields/network policies are preserved, known credentials and
  credential-valued attributes redacted. No default locking, permission changes,
  scope broadening or guessed wrappers/page requests. Valid empty arrays save
  zero records; malformed responses fail rather than becoming empty backups.
- Existing session/GET authorization/TLS/credentials/output infrastructure is
  reused. Controller/device collection runs before LDAP; LDAP-only skips device
  discovery. Per-module results retain successful exports when another fails.
- The backup policy/menu now supports LDAP; general VisionClient and migration
  capability catalogues remain mock-only/closed. API-10 is still not found as an
  exact endpoint in the reviewed PDF; output says source-observed, officially
  documented false, master live-tested false, schema/enumeration completeness
  unverified. Complete version contract, pagination, restoration and CC mapping
  remain blockers to broader qualification, not to this declared narrow subset.
- Verification: 108 guarded offline cases passed across backup, host setup,
  product clients, mocked integration and offline controller workflows. Includes
  identity rejection without leaking addresses, IPv6 normalization, LDAP
  redaction/empty/malformed output, GET-only scope, TLS and module independence.
  Actual LDAP master read/response shape still needs authorized lab validation.

## Vision HTTP compatibility correction - 2026-11-24

Owner-authorized functional correction based on the demonstrated comparison
below, not confirmation of the original live response or a new milestone.

- HTTP backend now supports bounded ordinary single-member gzip with CRC/EOF
  checks and independent encoded/decoded limits (16 MiB in the backup).
  Oversized output, truncation, corruption, extra/multiple members and ambiguous
  framing fail before committing response cookies. Bodyless 204/304 skip
  decompression; decoded responses remove stale length/encoding metadata.
- Cache-Control/Vary repetitions are combined, not arbitrary headers.
  Set-Cookie stays multi-valued/session-owned; sensitive or unknown duplicate
  fields and original transport/read-only/TLS restrictions stay strict.
- Selected Vision failures emit safe stderr diagnostics: method/template,
  status, stage, exception/category, normalized Content-Type/Encoding and reason.
  No bodies, credentials, session IDs, raw messages or full headers.
  HTTP 200/status-ok/validated body JSESSIONID remain mandatory; no fallback.
- Offline verification: 161 backend/transport/authentication/backup/launcher
  cases passed, including compressed login followed by automatic inventory and
  device GETs. Backend subset: 72 cases, zero network attempts/1080 guard
  observations, zero actual dispatch/144 observations. Another 54 existing
  offline-workflow/mocked-integration cases passed (215 total, non-overlapping).
- Actual Vision lab authentication/discovery and original failure cause still
  require an owner-authorized run. No API, product-version qualification,
  import/write behavior, TLS/operator interface or accepted containment record
  was changed. No new dependency; zlib is in Python's standard library.

## Pre-fix Vision login compatibility investigation - 2026-11-24

Source comparison only; no authentication or HTTP policy change. The owner
confirmed LDAP, Scheduler and object downloaders as working references.
Failed-master response metadata is not available yet.

References: [Vision LDAP downloader](../legacy/download_ldap_permissions%20%281%29.py),
[Vision Scheduler downloader](../legacy/download_scheduler.py),
[object downloader](../legacy/app/download_cybercontroller_objects.py),
[master authentication](../src/cc_vision_import/authentication.py),
[session ownership](../src/cc_vision_import/sessions.py) and
[HTTP backend](../src/cc_vision_import/http_backend.py). Legacy sources were
read only, never imported or executed. The CC-labeled object downloader has a
different authentication profile; the owner nevertheless confirms it as a
working Vision lab reference. That report is not dismissed based on its label.

| Aspect | Original LDAP/Scheduler scripts | Master |
| --- | --- | --- |
| Login target | LDAP: HTTPS `/mgmt/system/user/login`; Scheduler: configured endpoint in missing API INI | Same documented literal login path |
| Method/payload | POST; JSON username/password | Same method and decoded JSON fields; compact ASCII serialization |
| Application headers | Accept/Content-Type application/json; X-Requested-With XMLHttpRequest | Same on login; GET omits the legacy session-wide Content-Type |
| HTTP client defaults | requests.Session; default User-Agent, compression negotiation, keep-alive and environment proxy handling | Direct http.client HTTPS; implicit Accept-Encoding identity; explicit Connection close; no redirects or ambient proxy credentials |
| Status/JSON | raise_for_status then requests JSON decoding; require status ok | Backend validation precedes UTF-8/strict JSON/status checks; require HTTP 200 and validated body jsessionid |
| Content encoding | requests/urllib3 decode supported compressed content | Reject every non-identity Content-Encoding |
| Header/framing policy | HTTP library supports combining repeated Cache-Control fields | Reject repeated non-Set-Cookie headers; bounded reads, explicit length/framing checks |
| Session ID | Cookie jar persists Set-Cookie; LDAP does not inspect body jsessionid; Scheduler displays it but does not require it | Retain cookie jar and explicitly send the validated body JSESSIONID; an existing explicit Cookie header is not replaced by jar insertion |
| Session persistence | Same Session object across login/GET; pooled TCP connections | Same owned backend/strategy across login/GET; separate TCP connections; cookie state persists |

The object downloader uses the same literal login URL and POST, but adds Basic
Authorization, browser-style headers, Accept `application/json; */*` and explicit
Accept-Encoding `gzip, deflate, br`. It constructs JSON manually; decoded fields
match the master's for ordinary synthetic credentials. It accepts HTTP 200
without checking login JSON/status/jsessionid and relies on session cookies for
GETs. These differences are not adopted blindly or treated as the cause of the
master's reported pre-interpretation malformed classification.

In-memory verification on Python 3.13.14, using installed requests 2.32.5 and
urllib3 2.6.3 (comparison tools only, not new application dependencies):

- Identity JSON: both accepted.
- Gzip JSON: requests accepted; master returned the reported
  `transport_failure` / `malformed_response` pair.
- Repeated Cache-Control: requests accepted; master returned the same pair.
- Cookie-only status-ok JSON: requests accepted and persisted JSESSIONID on
  a prepared GET; master returned `malformed_login_response`, a different code.
- Identical URL/method, decoded login payload and application headers confirmed.
  This header equivalence applies to LDAP/Scheduler, not object login. The
  stdlib request buffer confirmed implicit Accept-Encoding identity.
- Separate AST-only object-source inspection plus guarded request preparation
  confirmed its Basic Authorization and differing headers. A two-request master
  probe retained the response cookie and sent the body session ID on GET; when
  the synthetic IDs differed, its explicit Cookie took precedence over the jar.
- Zero network attempts; no secrets, bodies, full headers or exception messages
  printed. The 115 existing guarded backend/authentication/backup tests passed.

**Actual lab root cause remains unknown.** Legacy compression negotiation does
not establish the encoding returned to the master's identity request. No
duplicate header or cookie defect has been observed on the failed request.
The reported pair is produced before authentication body/session interpretation,
through backend malformed classification (or an invalid transport response
envelope), not proof that Vision's JSON or credentials are invalid. Obtain safe
exception function/line/class and status/encoding/framing metadata from an
owner-authorized observation before implementing a compatibility fix. No retry,
decompression, cookie fallback or globally weakened validation was introduced.

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
defaults true; optional custom CA. Explicit `tls.verify=false` selects the scoped
Vision backup transport and corresponding backend/request permission, with a
concise warning; no extra operator flag is required. Unrelated
operations remain strictly verified. Owner-approved transport limitation:
existing socket timeouts/checked per-request deadlines do not hard-bound DNS or
whole-run execution. Default backend dispatch remains blocked.

Output is explicitly supported-scope, credential-redacted, completeness-unverified
inventory and not a complete configuration backup or migration input. No full tree
enumeration, LDAP/Scheduler API binding, configuration write, import, delete,
async follow-up, retry, authentication renewal or remote logout was added.
Login session state is cleared locally; server expiry is not verified.
AMS-alerts naming variants are explicitly excluded, never backlog modules.
Unsupported module selections fail before access. Initial implementation evidence: 238 targeted offline
guarded tests passed across launcher, backup and directly related existing
client/session/backend/transport/workflow/schema modules; zero guarded network
attempts. Linux permissions, live RBAC/cookie behavior, installed-build
compatibility, and the updated Docker image remain unverified. The current
operator/TLS correction passed 157 focused guarded regression cases and 23
final launcher/backup follow-up cases on Python 3.13.14; these counts overlap.
No guarded network attempts occurred. Actual Python 3.8/Docker/live execution
of the update remains pending owner validation.

### Internal capability scope and exclusions

The operator interface presents only implemented selectable components.
Unsupported/excluded JSON selections are rejected before controller access.
Internal exclusions are not emitted in normal menus, summaries or manifests.
Normal discovery remains the existing documented managed-device GET. Selected
LDAP, native-tree and Scheduler reads reuse the same session. Scheduler uses its
one source/INI-observed GET; no pagination path or write operation was added.

| Capability | Status | Evidence/limits |
| --- | --- | --- |
| Controller Objects | Implemented; partial coverage; not live-verified | Managed-device thin graph plus supported detail GETs, not every site/tree configuration |
| Managed Devices | Implemented within Controller Objects; not a separate selectable module | Native discovery graph preserved; duplicate management IP detail requests deduplicated |
| Device Access | Implemented; redacted and completeness-unverified; not live-verified | Existing device detail response's documented nested access subset; missing access reports module failure |
| Physical Tree / Organization Tree | Implemented opaque native JSON exports; selectable independently | Owner confirms both exact Vision 5.4.9 GETs; new master offline-tested only; schemas/identity/enumeration completeness unqualified |
| Credential Configuration | Unsupported as a restorable credential backup | Sensitive fields are redacted; portability/restore contracts unresolved |
| LDAP Permissions | Implemented source-observed list subset; master live-unverified | Validated/redacted records; full exact-version schema/enumeration and CC mapping unqualified |
| Scheduler | Implemented source/INI-observed array-of-task-object subset; master offline-tested only | Exact GET scheduledtask binding found in both supplied INIs; full schema/enumeration unqualified |
| Cyber Controller live backup | Unsupported | Existing offline synthetic workflows do not qualify live CC versions |
| AMS-alerts restoration | Intentionally out of scope | Document-store restoration/deployment utility, not a controller backup module; never integrated |

AMS-alerts, AMS_alerts, AMS Alerts, AMSAlert, AMSAlerts and equivalent normalized
component identifiers remain internally rejected through standard
`unsupported_backup_domain` validation. The exclusion is component-scoped:
unrelated controller objects with "alert" in their names are not filtered.
No AMS-specific APIs, files or folders are produced. This is an exclusion,
not planned backup functionality.

### Complete legacy-to-master inventory (internal)

Preserved read-only inventory: **25 scripts (17 Python, 8 shell)**. Twenty-four
were reviewed for applicable functionality; the AMS restoration script is
excluded from integration review. Twelve duplicate pairs were hash-confirmed.
Versions are not established by legacy intent alone. Original scripts,
deployment config and archives are not new application dependencies.

| References (identical copies grouped) | Original function / dependencies | Unified mapping |
| --- | --- | --- |
| [CC download](../legacy/app/download_cybercontroller_objects.py), [copy](../legacy/cc-objects/app/download_cybercontroller_objects.py) | CC Basic+JSON login; recursive Physical/Organization and site/device GETs; nested access extraction; missing operation INI; requests/urllib3; no pagination | Shared read/auth intent and offline adapters retained; Vision inventory/device access use separately documented Vision contracts; no CC live backup |
| [CC upload](../legacy/app/upload_cybercontroller_objects.py), [copy](../legacy/cc-objects/app/upload_cybercontroller_objects.py) | Duplicate login/INI; site/device POSTs and supporting GETs; requests/urllib3 | Upload-only, not backup; no unsafe root fallback or name-only placement adopted |
| [CC update](../legacy/app/update_cybercontroller_objects.py), [copy](../legacy/cc-objects/app/update_cybercontroller_objects.py) | Duplicate login/INI; device PUT and supporting GETs; requests/urllib3 | Update-only; explicit offline identity mapping/comparison retained; no destination source-ID reuse |
| [Credential transformer](../legacy/app/update_json_credentials.py), [copy](../legacy/cc-objects/app/update_json_credentials.py) | Local credential JSON transformation, no API/auth; prints secrets | Not a backup module; secret printing/mutation not ported; current access collection redacts credentials |
| [LDAP download](../legacy/download_ldap_permissions%20(1).py), [copy](../legacy/ldap_permissions/download_ldap_permissions%20(1).py) | Vision JSON login; GET `/mgmt/system/config/itemlist/ldapobjectpermission`; missing `vision.ini`; requests/urllib3 | Read-only list subset uses external profile/shared session; full exact-version schema/enumeration and CC contracts remain unqualified |
| [LDAP upload](../legacy/upload_ldap_permissions%20(1).py), [copy](../legacy/ldap_permissions/upload_ldap_permissions%20(1).py) | Vision login/LDAP POST; missing `vision.ini`; requests/urllib3 | Import-only; no forced locking, scope-broadening fallback or write retry reused |
| [Scheduler download](../legacy/download_scheduler.py), [copy](../legacy/schedulertask/download_scheduler.py) | Vision login/session/logout; configured scheduler GET; missing scheduler API `config.ini`; requests/urllib3 | Shared login intent reused; literal task endpoint, enumeration and response binding unresolved |
| [Scheduler upload](../legacy/upload_scheduler.py), [copy](../legacy/schedulertask/upload_scheduler.py) | Configured task GET/create, sanitization and name-based skipping; missing INI | Import-only; no guessed paths, unsafe logging, sanitization or name-only skips adopted |
| [Sleep wrapper](../legacy/app/run.sh), [copy](../legacy/cc-objects/app/run.sh) | Persistent sleep-based runtime | Not reused; selected backup executes and exits |
| [Installer](../legacy/2install.sh), [copy](../legacy/cc-objects/2install.sh) | Docker load/create, optional cron and deployment INI | No legacy installation/cron workflow; use clone/build or save/load |
| [Uninstaller](../legacy/2uninstall.sh), [copy](../legacy/cc-objects/2uninstall.sh) | Docker/container and cron cleanup | Not an application module; explicit operator cleanup only |
| [Container wrapper](../legacy/run-cc-objects.sh), [copy](../legacy/cc-objects/run-cc-objects.sh) | Docker start/exec/stop | Replaced by [on-demand launcher](../run-vision-backup.sh), never invoked |
| [AMS restoration](../legacy/AMS-alerts/restore_cfg.py) | Explicitly excluded, not reviewed for integration | Internal exclusion only; absent from routine operator UI/artifacts |

Missing bindings remain Vision LDAP `vision.ini`, Scheduler `config.ini`
login/logout/scheduler paths, and CC download/upload/update operation INIs
(for example `download.ini`). [Deployment config](../legacy/cc-objects/config.ini)
is not a substitute. No legacy script or authentication function was executed.
Vendor PDFs remain local evidence excluded from Git/image publication.

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
| Physical/Organization export | Owner-confirmed Vision 5.4.9 HTTP 200/valid tree JSON for API-02/API-03; opaque exports enabled in VISION-TREE-BACKUP. Complete schemas/identity/enumeration remain unqualified. | API-02/API-03 source and destination candidates; no real completeness/identity qualification. |
| Site/device create/update | CC API-07/API-08/API-09 destination candidates; Vision-to-CC type/field/identity transformations unestablished. | Same CC destination candidates; native IDs must still be independently mapped and patch-level differences qualified. |
| Device detail/access | Vision source detail/access API missing; CC API-06 alone cannot bridge A. | API-06 source-observed; standalone access endpoint not established. Qualified association and credential portability remain gates. |
| LDAP | Vision API-10 source observed; CC source/reference/create/read-back equivalents missing. API-11 is Vision-destination evidence only. | CC LDAP read/write/reference APIs and schemas not established at all by these scripts. |
| Scheduler | Vision CFG-03 GET /mgmt/system/config/itemlist/scheduledtask resolved from supplied Scheduler INIs; native array/object subset export enabled. Full schema/enumeration unqualified. | CC scheduler APIs/types not established. Vision configurable paths cannot be reused as CC evidence. |
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

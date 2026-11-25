# API Evidence and Compatibility Discovery Matrix

Date: 2026-11-18
Evidence levels: source-observed endpoints; separately scoped offline mock
coverage for authentication and three reads; owner-provided vendor PDF evidence
for selected exact method/path pairs; E-036 synthetic offline subset regressions.
Runtime compatibility is scoped; current owner-reported evidence and remaining
qualification limits are recorded below.

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

`destination-discovery` uses only the two established login/Organization paths.
Basic+JSON login also requires a successful JSON status and validated session
identifier, using the existing session validator; HTTP 200 alone is rejected.
TLS/hostname verification is mandatory, HTTPS port 443 only, no retries/redirects,
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

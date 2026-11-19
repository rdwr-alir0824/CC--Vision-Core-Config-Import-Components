# CCV-010-B - Read-Only Laboratory Qualification Plan

Date: 2026-11-19
Status: **PLANNING AND DOCUMENTATION ONLY. NOT READY FOR LABORATORY ACTIVATION.**
Laboratory execution remains **UNAUTHORIZED**. No readiness gate has passed.
This plan is not owner acceptance, laboratory authorization or an executable
test procedure. All approval fields below are pending.

## 1. Scope, baseline and authority

The accepted baseline is CCV-010-A, owner-reported commit `5f72ddf`; no Git
inspection was performed for this plan. [E-040](PROGRESS.md#e-040---ccv-010-a-owner-offline-acceptance-2026-11-19)
records acceptance of its offline scope. **394 passing application tests** and
41 additional guarded review scenarios are historical evidence, not tests rerun
for CCV-010-B, live interoperability evidence or permission to connect.

Only local static review and documentation are authorized now. This work does
not perform Git operations, network requests, DNS queries, probes, authentication,
API calls, dependency installation, configuration writes or laboratory execution.
Application modules, tests and vendor PDFs must remain unchanged.

Future qualification is limited to separately approved laboratory targets and
one existing, operator-selected site per target/role. It is not inventory export,
migration, destination preflight or production qualification. No configuration
CREATE, UPDATE, DELETE, import, execution, overwrite or corrective operation may
enter the initial allowlist. Authentication and optional logout POSTs are
explicit **session-state exceptions**, not configuration-write permission.
Login may create a remote session, audit entries and authentication counters;
even a GET must be confirmed side-effect-free with respect to configuration.

The production capability catalogue remains empty/default-deny. Never declare a
real backend to be a mock, borrow `0.0-test` permissions, bypass capability gates
or use the legacy scripts as an execution shortcut. Any future lab-only procedure,
auth policy or safety implementation requires separate scope, review and
authorization; this plan adds none.

## 2. Reviewed evidence and architecture boundary

Reviewed: [API matrix](API_MATRIX.md), [architecture](ARCHITECTURE.md),
[decisions](DECISIONS.md), [progress](PROGRESS.md), [roadmap](ROADMAP.md), and
the modules linked below. Existing evidence is retained, not upgraded.
Earlier "B not started/not authorized" statements in dated checkpoints describe
the pre-planning boundary; only B documentation is authorized by the current
request. They do not become laboratory execution permission.

### Exact vendor evidence

The [approved vendor analysis](API_MATRIX.md#ccv-009-b---approved-vendor-reference-analysis)
is the page-level evidence source used here. Local PDF SHA-256 values were
rechecked for this planning task; matching bytes do not establish vendor
authenticity, running version or build applicability.

| Binding | Exact documentation and SHA-256 | Applicability limit |
| --- | --- | --- |
| V / `DOC-V549` | APSolute Vision 5.4.9 REST API, April 2025; `827d4954cf5390f3a242e8bbb0af4dc7dd9ce68f5c17eba19449cf45a8d9d5c4` | Vision 5.4.9 documentation only; installed build unconfirmed. |
| C / `DOC-CC10107` | Cyber Controller 10.10.7 REST API, September 2026; `f6c7e474cb2df25d5d1b7b52da94f13f9b5013649419fc4276f49bd153e2d587` | **10.10.7-labelled content; active metadata says 10.10.6. Unresolved.** |

Page numbers below are PDF / printed pages. Overview/session/async evidence is
V/C 11/1; HTTPS is V/C 12/2. Neither reference provides a reviewed
product-build discovery endpoint for this scope. Require independent operator
evidence; do not guess an endpoint or use API "Version information: 1.0" as the
product release. No adjacent-version or family compatibility is inferred.
C requires corrected vendor provenance or authoritative applicability
clarification covering the exact selected operations and installed build before
its Gate A can pass. Owner preference alone does not resolve vendor evidence.

### Implementation observations, not live qualification

| Component | Current facts and planning consequence |
| --- | --- |
| [Transport](../src/cc_vision_import/transport.py) | Verified HTTPS contexts, encoded path segments, independent finite connection/read timeouts, redirect rejection, sanitized errors. GET retries are configurable; initial lab policy must explicitly set zero. Generic verbs do not enforce this operation allowlist. |
| [HTTPS backend](../src/cc_vision_import/http_backend.py) | Explicit injection, one origin/private cookie jar per instance, eager unbounded body read, no internal retry/redirect, explicit resource close, cleanup failure surfaced. Socket timeouts do not bound DNS or total transfer duration. |
| [Authentication](../src/cc_vision_import/authentication.py) | Vision checks application `status` but does not require session evidence. CC accepts HTTP 200 alone and retains credentials for Basic on subsequent requests. These legacy/mock policies are insufficient for this plan. Basic-plus-JSON is not a documented vendor requirement. |
| [Sessions](../src/cc_vision_import/sessions.py) | Separate owners/backends by source/destination role; 401 expiration, 403 non-expiration, local lifetime and cleanup. Local close does not call remote logout or prove revocation; local expiration is not server TTL. |
| [Product clients](../src/cc_vision_import/product_clients.py) and [capabilities](../src/cc_vision_import/capabilities.py) | Existing clients are mock-only for tree/LDAP reads, not implementations of the proposed site-by-ID operation. No production declarations exist; this plan enables none. |
| [Schema qualification](../src/cc_vision_import/schema_qualification.py) | Offline exact-document binding, login-example and SitePojo subset checks, preservation rules and async trace observation. It neither dispatches nor proves complete wire schemas, remote authentication or inventory completeness. |

## 3. Laboratory information and approval checklist

All entries are **[PENDING - NOT SUPPLIED]** unless documentation evidence is
explicitly identified. Do not put credentials, tokens, customer addresses or
real target values in this document. Future actual values belong only in the
approved restricted authorization record, referenced by opaque identifiers.
Complete independently for every source/destination instance, even at one origin.

| Required item | APSolute Vision | Cyber Controller |
| --- | --- | --- |
| Approved laboratory identifier and target custodian | [PENDING - NOT SUPPLIED] | [PENDING - NOT SUPPLIED] |
| Exact installed product version | [PENDING - NOT SUPPLIED; compare to documented 5.4.9] | [PENDING - NOT SUPPLIED; compare to 10.10.7-labelled content only after clarification] |
| Exact build, patch/hotfix and independent build evidence reference/date | [PENDING - NOT SUPPLIED] | [PENDING - NOT SUPPLIED] |
| Approved management HTTPS endpoint, port, exact hostname and IP allowlist record | [PENDING - NOT SUPPLIED] | [PENDING - NOT SUPPLIED] |
| Expected TLS certificate identity: SAN hostname or IP SAN, issuer, validity and approved identity evidence | [PENDING - NOT SUPPLIED] | [PENDING - NOT SUPPLIED] |
| Certificate trust source: approved local CA bundle/system trust decision, digest and custodian | [PENDING - NOT SUPPLIED] | [PENDING - NOT SUPPLIED] |
| DNS resolver/static mapping policy, approved address set and change handling | [PENDING - NOT SUPPLIED] | [PENDING - NOT SUPPLIED] |
| Approved least-privilege test-account role, authentication mechanism and opaque secret reference | [PENDING - NOT SUPPLIED; no account value or secret here] | [PENDING - NOT SUPPLIED; no account value or secret here] |
| Exact permitted operation IDs, concrete site-ID restricted binding and read permission evidence | [PENDING - NOT SUPPLIED] | [PENDING - NOT SUPPLIED] |
| Explicit login/session-creation authorization and approved wire authentication recipe | [PENDING - NOT SUPPLIED] | [PENDING - NOT SUPPLIED; resolve Basic behavior] |
| Remote-session revocation or bounded-expiry procedure, owner and verification evidence | [PENDING - NOT SUPPLIED] | [PENDING - NOT SUPPLIED] |
| Read-only configuration baseline/change-observation method | [PENDING - NOT SUPPLIED] | [PENDING - NOT SUPPLIED] |
| Exact-version vendor applicability and operation/schema clarification | [PENDING - build applicability] | [PENDING - resolve 10.10.6 metadata discrepancy and build applicability] |
| Approved numeric safety limits, test window, rate and request budget | [PENDING - approval of section 5 policy] | [PENDING - approval of section 5 policy] |
| Evidence storage, access, retention/deletion policy and incident contact | [PENDING - NOT SUPPLIED] | [PENDING - NOT SUPPLIED] |

Independent build evidence should be a sanitized operator-supplied product
About/build display or approved installation/support record, with its source,
time and custodian. Reconcile conflicting evidence before any authentication.
Do not invoke a CLI, web UI or product API to obtain it during this milestone.
A source build does not qualify a destination build.

## 4. Proposed operation allowlist - no operation approved

This is a candidate register, **not an active allowlist**. Every row's approval
status is **PENDING / NOT AUTHORIZED**. Product/version evidence is per row;
C's metadata conflict applies to every C row. Required roles are unknown in the
references: operator/vendor confirmation of the narrow permission is mandatory;
do not assume administrator access or enlarge privileges after a denial.

Common failure conditions for every HTTP candidate: unexpected build, TLS or
origin failure, any redirect, budget/deadline/size violation, malformed response,
unexpected status/schema, auth/RBAC mismatch, suspected exposure or cleanup
uncertainty. Stop without retry. Paths are templates, not real targets.

| ID / product | Exact version evidence | Method / API path | Purpose and expected response | Required privilege | Data exposure / operation-specific failure | Approval |
| --- | --- | --- | --- | --- | --- | --- |
| V-ID / Vision | V 5.4.9; installed build evidence required | Local review / no API path | Confirm exact product/build from independent evidence; no HTTP response | Approved evidence custodian, no API privilege | Build evidence only; missing or conflicting evidence blocks login | PENDING / NOT AUTHORIZED |
| C-ID / Cyber Controller | C 10.10.7-labelled; metadata conflict unresolved; installed build evidence required | Local review / no API path | Confirm product/build and authoritative document applicability | Approved evidence custodian, no API privilege | Build evidence only; conflict or absent clarification blocks login | PENDING / NOT AUTHORIZED |
| V-AUTH / Vision | V 5.4.9, Server Login 156-158/146-148; overview 11/1 | POST `/mgmt/system/user/login` | Establish one session; example 200 JSON `status: ok`, nonempty `jsessionid`, plus usable approved cookie evidence | Approved test role permitted to log in; exact role pending | Credentials in request, session token/body/cookies in memory; session creation requires explicit consent. 200 alone, bodyless result, missing/mismatched session evidence or rejection fails | PENDING / NOT AUTHORIZED |
| C-AUTH / Cyber Controller | C 10.10.7-labelled, same pages; conflict unresolved | POST `/mgmt/system/user/login` | Same bounded session objective; independently qualify JSON and cookie evidence, not existing HTTP-200-only policy | Approved test role permitted to log in; exact role pending | Same sensitive data; unapproved Basic or unresolved body/cookie semantics blocks use | PENDING / NOT AUTHORIZED |
| V-SITE / Vision | V 5.4.9, Get Site by Id 146/136; SitePojo 255/245 | GET `/mgmt/system/config/tree/site/byid/{id}` | Read exactly one operator-selected existing site by its server-native `ormID`; 200 JSON SitePojo object | Read permission for that site; exact role pending | Native ID in path; names, description, parent ID and unknown fields in body. Wrong ID, unexpected envelope, 401/403 or unknown error fails | PENDING / NOT AUTHORIZED |
| C-SITE / Cyber Controller | C 10.10.7-labelled, same operation/model pages; conflict unresolved | GET `/mgmt/system/config/tree/site/byid/{id}` | Same single-site objective, qualified independently for this build/role | Read permission for that site; exact role pending | Same exposure; do not infer equal IDs, schema or privilege from Vision | PENDING / NOT AUTHORIZED |
| V-LOGOUT / Vision, conditional only | V 5.4.9, Server Logout 156/146; supplementary evidence, not a new legacy pair | POST `/mgmt/system/user/logout` | Optional approved remote session termination; 200 example JSON `status: ok`; table also says "No Content" | Session owner with logout permission; semantics pending | Session cookie in request; body/session invalidation ambiguity blocks qualification. A 200 is not revocation proof | PENDING / NOT AUTHORIZED; excluded unless explicitly selected |
| C-LOGOUT / Cyber Controller, conditional only | C 10.10.7-labelled, Server Logout 156/146; conflict unresolved | POST `/mgmt/system/user/logout` | Same optional termination objective, independently evidenced | Session owner with logout permission; semantics pending | Same ambiguity; no invented logout alias or automatic replay | PENDING / NOT AUTHORIZED; excluded unless explicitly selected |
| V-VALIDATE / Vision | V 5.4.9 SitePojo 255/245; offline subset evidence E-036 | Local only / no API path | Bounded strict JSON and subset validation; sanitized outcome, not inventory certification | Authorized evidence processor, no extra API privilege | Body only transiently in memory; sensitive/invalid/unqualified content stops | PENDING / NOT AUTHORIZED |
| C-VALIDATE / Cyber Controller | C 10.10.7-labelled SitePojo 255/245; E-036 retains conflict | Local only / no API path | Same subset check; unresolved C provenance remains unqualified | Authorized evidence processor, no extra API privilege | Same exposure; matching fields do not resolve provenance | PENDING / NOT AUTHORIZED |
| V-CLOSE / Vision | Local CCV-010-A contracts, not vendor endpoint evidence | Local only / no API path | Release response/connection/backend, discard cookies and credential references; report local outcome | Local process owner | Cleanup failure or uncertain retained resources stops; no remote revocation claim | PENDING / NOT AUTHORIZED |
| C-CLOSE / Cyber Controller | Local CCV-010-A contracts, independently owned role/backend | Local only / no API path | Same local objective without affecting another role | Local process owner | Cross-role state loss or cleanup uncertainty stops | PENDING / NOT AUTHORIZED |

Smallest HTTP sequence per approved target/role: **one login POST, one site GET,
then local cleanup**. Add at most one explicit logout POST only when separately
selected in the approved procedure. If logout is not selected, a verified
operator-managed revocation or bounded remote-expiry control must be approved
before login. No cleanup request is implicitly permitted by this plan.

Excluded: by-name site lookup (extraneous required `id` in documentation);
device-by-IP (broader access/credential exposure, optional/opaque models);
Physical/Organization exports, LDAP and scheduler reads (no matching reviewed
vendor contract); all configuration mutation/import/execution; guessed
version endpoints; async tracking/result calls; automatic login renewal,
pagination, enumeration and post-failure diagnostic API calls. Even a documented
device creation endpoint cannot enter this allowlist.

## 5. Mandatory network and backend safety prerequisites

Proposed numeric ceilings below are **local safety policy awaiting approval**,
not observed product limits, existing controls or approved lab values. Gate C
must bind them to each target/role; any change requires procedure review before
testing. No setting may be omitted or treated as unlimited.

| Safeguard | Required future policy and acceptance evidence |
| --- | --- |
| Host/IP and operation allowlisting | Exact approved HTTPS origin/port and address set, restricted to laboratory management interfaces. Enforce egress deny-all except approved destinations and validate the actual peer against the approved set. Bind method/path/site-ID before dispatch; reject arbitrary URL/query/header overrides and cross-origin credentials. Current origin pinning is not an IP or operation firewall. |
| HTTPS, certificates and hostname | HTTPS only; certificate chain, validity and SAN hostname verification mandatory. An approved IP-origin requires a matching IP SAN. Never replace the hostname with an IP in a way that disables identity checks, accept all certificates, downgrade, or override Host to repair a mismatch. Certificate identity changes require fresh approval. |
| CA bundle | Explicit security-owner approval of either the local trust bundle or system trust, its provenance/digest, validity and restrictive permissions. No trust-on-first-use, CA downloads or insecure fallback. File links/mapped storage and any revocation policy must be assessed; the current backend adds no revocation service or pinning policy. |
| DNS | No DNS during planning. Future resolution must use an approved resolver, bounded resolution time and allowlisted results, including IPv4/IPv6/CNAME behavior. Validate every selected address and fail on changes/out-of-set results, not just the first answer. No ambient search-suffix/proxy/discovery fallback. A no-DNS fixed mapping is an alternative only with separately reviewed enforcement preserving TLS identity and peer allowlisting. |
| Connection/read timeouts | Proposed `connect_timeout=5` seconds and `read_timeout=10` seconds, independently enforced. Existing contract permits finite `0 < value <= 300`, but its upper bound is not the proposed lab policy. Prove behavior offline for connect/TLS, request transmission, headers and body. |
| DNS and total deadline | Proposed DNS budget <=5 seconds within an absolute **30-second operation deadline**, starting before resolution and covering connect, TLS, send, all headers/body, validation and local release. Reserve the final 5 seconds for bounded cleanup; stop active work by 25 seconds. Verify enforcement against stalled resolution and slow/trickling transfers. A waiting-thread timeout that leaves work running does not qualify. Remote operator cleanup has a separate preapproved expiry/revocation deadline. |
| Response size | Proposed **65,536 body bytes maximum per response**, including login, logout and error bodies. Enforce incrementally before full buffering/JSON parsing, with or without Content-Length and with chunking/connection-close framing. Reject declared oversize early and actual oversize while reading; do not trust declared size. No decompression is enabled; reject unexpected encoded content rather than adding an unbounded decoding path. |
| Redirects | Deny every unexpected 3xx, including 303. Do not follow Location, forward credentials, change origin or convert methods. 202 also stops the initial synchronous sequence; no implicit polling. |
| Retries and rates | Explicit `read_retries=0`, one attempt for every operation, no auth renewal/status/TLS/timeout retry. One in-flight operation across roles/products, at least 1 second between HTTP dispatches, no concurrency or loops. At most 2 requests per target/role, or 3 if explicit logout is selected; no extra validation request is implicit. Stop on 429/Retry-After; do not sleep-and-retry. |
| Credentials and observability | Approved external secret source/resolver; resolve only at use, memory only, least privilege and separate role references. No command-line secrets, files in the repository, debug/wire logging, TLS key logging, packet/body captures, cookies in reports or raw exception tracebacks. Python object release is not guaranteed secure memory erasure. |
| Cleanup | A reviewed finally-path must attempt both response and connection release, close all independently owned backends and discard local credentials/cookies on every outcome. Preserve primary sanitized failure plus cleanup status. Prove bounded release, no request replay, and fail-closed behavior after release failure. Remote cleanup must have an independently approved method/deadline and custodian before login. |
| Error sanitization | Fixed category/status/attempt count and cleanup flags only; no URLs/site IDs, hostnames, raw headers, error bodies, credentials, exception chains/notes or session values. Recognize indeterminate POST outcomes: an interrupted login may already have created a remote session. |

### Resolution of CCV-010-A's three open controls

**All three are activation blockers in this plan. None is waived.**

1. **DNS-resolution deadline:** the socket connect timeout does not enforce it.
   Implement and offline-verify bounded resolution, or obtain a separately
   approved, technically enforced no-DNS mapping/peer-validation control.
   A pre-test DNS check, trusted lab network or operator stopwatch is insufficient.
2. **Total transfer-duration deadline:** per-socket timeouts permit indefinite
   trickle traffic. Implement and offline-verify an absolute deadline with
   interruption/resource-release guarantees. An external supervisor alternative
   requires separate security review proving actual termination, resource
   ownership/cleanup and safe remote-session handling, not merely a timed wait.
3. **Response-body size:** the current eager `read()` has no cap. Implement and
   offline-verify streaming size enforcement before activation. A small selected
   site, Content-Length promise, process-memory limit or later truncation is
   not an adequate replacement under this plan.

No safety code is implemented here. There is **no approved compensating control
or risk acceptance**. Any proposed exception must separately document exposure,
enforcement, numeric bounds, offline verification, accountable risk owner,
expiry and residual risks before Gate B can be reconsidered. Blanket acceptance
of A's offline scope does not resolve these controls.

## 6. Authentication and session qualification requirements

Before any laboratory login, separately implement/review and offline-verify a
lab-scoped authentication decision policy. Do not simply run the legacy/mock
strategies and label their outcomes qualified.

| Requirement | Future verification and pass boundary |
| --- | --- |
| Vision login | Match approved build-specific contract, HTTP status, strict JSON `status: ok` and nonempty `jsessionid` example evidence, and prove a usable session cookie. Existing Vision status-only success is insufficient. Bodyless/contradictory results stop pending vendor clarification. |
| CC login | Apply independent response and session checks; existing HTTP-200-only acceptance must not authorize the GET. Resolve vendor "No Content" versus JSON examples and approved Basic/session mechanism. No automatic transfer of Vision policy or legacy Basic requirement. |
| JSESSIONID | Establish the documented relationship between JSON `jsessionid`, actual Set-Cookie and outbound `Cookie: JSESSIONID` for the installed build. Backend currently captures Set-Cookie only; it does not convert JSON into a cookie. Missing/conflicting evidence stops; never invent a fallback token source. Confirm secure/path/domain/expiry scope without retaining values. |
| Authenticated read | The selected site GET must show RBAC-authorized session use, not merely 200 or an anonymous page. Basic credentials must not mask a missing/broken cookie session. Resolve the wire recipe before dispatch; no unapproved Basic header or extra probe to test alternate recipes. |
| Role isolation | Separate credentials/references, manager role, backend instance and cookie jar for source/destination, even if origins match. Verify offline cookie provenance and no cross-role forwarding, expiration or cleanup. Later approve exact lab role bindings independently; same-site IDs do not create shared identity. |
| HTTP 401 | Existing offline evidence shows only the affected role expires and its cookies clear even if later body/parsing/cleanup fails. Future lab observation must show no auto-renewal/replay and no effect on the other role. Normal initial sequence stops on 401. |
| HTTP 403 | Existing offline evidence shows denial does not expire the session. Future observation must preserve local role state without privilege escalation, retries or cookie clearing disguised as expiry. Normal initial sequence stops on 403. |
| Failure sanitization | Offline cases must cover rejected/malformed/bodyless login, bad cookie parsing, 401/403, transport/deadline/size failures and cleanup failure; verify no secrets in exceptions, output, notes or logs. Real invalid-credential tests risk lockout and are not initial candidates. |
| Local/remote termination | Verify bounded local close, independent role ownership and explicit cleanup failure reporting. Remote logout/expiry/revocation must be separately authorized and evidenced. Local close, a 200 logout, local expiration or Python process exit alone proves no remote invalidation. An uncertain login requires the same remote-session disposition procedure. |

Deterministic 401/403, cookie mismatch/isolation and malformed-login checks should
first use separately authorized offline doubles; existing historical tests are
not newly executed evidence. Any future deliberate live expiry/denial/isolation
case needs its own procedure revision, account/operation budget and owner approval.
It may use only an explicitly approved read on a selected site, never a
configuration mutation or deliberately bad login by default. Expected-negative
cases must be distinguished from unexpected initial-sequence failures; no
negative testing, second login or reauthentication is implicitly allowed.

If remote logout is selected, settle its body/No-Content ambiguity and obtain
independent revocation evidence without silently adding a post-logout API probe.
Alternatively approve operator-managed revocation or a documented, bounded server
TTL with independent evidence of expiry. Specify the responsible operator,
deadline and audit evidence in the restricted record. Absent that resolution,
do not create a session.

## 7. Single-read response qualification

The following requirements apply separately to V-SITE and C-SITE; each starts
**NOT EXECUTED / UNQUALIFIED**. Evidence is respectively V 5.4.9 and C
10.10.7-labelled Get Site by Id 146/136 and SitePojo 255/245, as recorded in
the [matrix contracts](API_MATRIX.md#documented-request-response-and-identity-contracts).
C remains provenance-unqualified until its conflict is resolved.

| Dimension | Required check and reporting |
| --- | --- |
| HTTP and envelope | Expected 200, approved JSON media type and one SitePojo object, not list/wrapper/HTML/empty body. Strict bounded UTF-8 JSON, no duplicate members or nonfinite numbers. Unexpected 202, redirect or error body stops without secondary requests. |
| Required fields | `ormID`, `name`, `type` must be present and non-null strings under the documented offline subset policy; no aliases, coercion or fabricated values. Required-field nullability is not settled by vendor evidence: preserve the distinction and classify null as unqualified, not product-invalid by assertion. |
| Optional fields | `description` and `parentOrmID` are optional strings in the model. Missing remains missing; present-null remains null/unqualified pending clarification. Do not populate defaults or equate absent/null/empty string. |
| Native identifiers | Compare returned `ormID` with the exact operator-bound native lookup ID using a documented policy; mismatch stops. Preserve exact strings, case and types in transient processing. Bind identity to product/build/controller/role; do not equate parent/access aliases or copy source IDs to a destination. |
| Unknown fields | Preserve permitted unknown members, nesting, JSON types and member/array order in the transient qualification representation. They are outside the documented subset, not silently schema-qualified. Unexpected fields/schema drift stop for review; do not strip them to obtain a pass. Preservation is not permission to retain raw bodies on disk. |
| Sensitive content | Treat names/IDs/descriptions and unknown fields as potentially sensitive. Inspect only in approved memory-bound processing; known credentials/session material trigger stop and no payload retention. Do not weaken existing credential classifiers, invent wire `secret_ref` values or save rejected artifacts. |
| Evidence and outcome | Record operation/build/reference, subset checked and sanitized issue codes. `documented-subset` is not full endpoint-schema validation; unknown semantics/null/provenance yield `unqualified`, malformed/type/ID mismatch yields failure. Passing a selected subset cannot upgrade artifact metadata, certify a complete export or enable a capability. |

The existing offline qualifier consumes a caller-supplied version-1
`api-schema-evidence` artifact envelope, not a raw wire response. Any future
adapter must be separately reviewed, explicitly supply truthful provenance and
not fabricate export completeness or a successful validation status. The new
plan supplies no adapter, fixture or production client. Unknown-field
preservation applies before sanitization; retained evidence is a separate
minimal projection, not a supposedly lossless redacted export.

## 8. Proposed sequence for a later exact procedure

These are planning steps, not instructions authorized to execute now.

1. Obtain independent product/build evidence and complete the restricted
   checklist separately for each target/role. Resolve C provenance; bind approved
   method/path/site-ID, wire auth recipe, data handling and remote cleanup.
2. Resolve and offline-verify all Gate B controls and authentication limitations.
   Record implementation identity and verification evidence; preserve the
   production default-deny boundary. Do not use manual raw requests as a bypass.
3. Obtain Gate A/B/C decisions and then a distinct Gate D authorization for the
   exact immutable procedure revision, execution identity, window, request count,
   rate, deadlines and selected cleanup route. Revalidate on any change.
4. Only under that future authorization, initialize separate local role/backend
   owners and verify approved target/trust/limit bindings without fallback.
   Fail closed before login if any prerequisite differs.
5. Dispatch the single approved login POST for one role. Validate full approved
   authentication/session evidence, not HTTP 200 alone. Any uncertainty stops
   subsequent reads and invokes the preapproved incident/cleanup disposition.
6. Dispatch exactly one approved site-by-ID GET. Apply section 7 checks in
   bounded memory and produce only the approved sanitized evidence projection.
   A response is not a complete inventory or cross-product compatibility proof.
7. Perform at most the expressly selected logout POST on the normal-success
   route, or use the preapproved operator revocation/expiry disposition. Attempt
   local cleanup on every route, independently per role; report both remote
   session disposition and local cleanup, including uncertainty.
8. Review sanitized evidence and configuration-change observations; stop pending
   review before any other target/role or procedure repetition. A second product
   or destination requires its own bound gates; do not infer shared qualification.

On a stop condition, do not automatically send even a cleanup API request.
Perform local-only release and operator escalation; any remote action must
follow a separately authorized incident disposition. Do not continue to "finish"
the sequence, retry an uncertain POST or attempt corrective configuration writes.

## 9. Asynchronous operations - future scope only

V/C Overview 11/1 documents 202 plus status Location, tracking 200 while in
progress, 303 plus result Location and final result retrieval. It does not
establish tracking/result HTTP methods, polling limits, complete error states,
expiry/cancellation or final-body schemas. Example status/result path shapes
are evidence, **not initial allowlist operations**.

Future async qualification must independently establish:

- Exact product/build and operation-specific async support, request method,
  tracking/result methods and privileges, approved origins/paths and opaque
  request-ID correlation. Never infer GET or send credentials to an unvalidated
  Location, even on an apparently similar host.
- Single unambiguous HTTPS Location, origin/port/path allowlist, no cross-origin
  or general redirect following; retain current 303 denial until a separately
  reviewed explicit workflow exists.
- Bounded poll count, interval/rate, absolute overall deadline, response size,
  authentication lifetime and handling of missing/malformed/mismatched IDs,
  401/403, expired tracking, connection failure and server-reported failure.
- Separate classifications for accepted, in-progress, result-available and
  final result. 202, tracking 200 and 303 are nonterminal; final retrieval must
  validate HTTP/body semantics. "Reported success" is not independently verified
  operation success or configuration correctness.
- No automatic authentication renewal, cancellation, write replay or
  "retry to discover outcome". Timeout/lost tracking leaves the outcome
  uncertain; escalate without corrective writes.

No polling, result fetch, asynchronous implementation or execution is part of
CCV-010-B. An unexpected 202 or 303 in the initial sequence stops it.

## 10. Evidence retention and access prerequisites

Before testing, the data/security owner must approve **[PENDING - NOT SUPPLIED]**:
storage system and location, classification, encryption at rest/in transit,
named roles/ACLs, custodian, access auditing, integrity protection, retention
duration, backup handling, secure deletion/verification and incident process.
No default repository location, local plaintext export, shared temp directory,
cloud sync or third-party upload is authorized. Existing C3 plaintext records
are not automatically an approved laboratory evidence store.

Retain only a reviewed minimal record:

| Evidence item | Permitted form after approval |
| --- | --- |
| Time and identity | UTC timestamp with timezone, run/procedure revision, opaque target/role identifier, product/version/exact build and restricted authorization reference |
| Operation and result | Approved operation ID, numeric status where observed, attempt count, measured duration/byte count, result classification: blocked/not-executed, passed-bounded-subset, failed, unqualified, stopped or indeterminate |
| Schema | Exact evidence binding/document digest/pages, selected subset and sanitized validation issue codes; no raw field values or unsafe diagnostic paths |
| Failure | Fixed sanitized transport/auth/schema category, primary and secondary cleanup category; no raw exception text, URLs, Location, headers or error bodies |
| Response digest, when appropriate | For a non-sensitive, approved redacted read-response projection only: SHA-256 plus projection policy/version and digest-input definition. Not proof of a raw/lossless response. Omit raw-body digests for login/logout/session-bearing or other sensitive bodies; hashing is not redaction and low-entropy identifiers are not anonymized by a digest |
| Cleanup | Independent local response/connection/backend outcome per role and remote revocation/expiry verified, pending, failed or unknown; responsible operator and safe evidence reference |
| State observation | Approved operator attestation/audit reference for no unexpected configuration change, distinct from expected session/audit effects; no configuration dump |

Never retain raw credentials, usernames, Authorization/Basic material, cookies,
JSESSIONID/JSON session values, unrestricted configuration dumps, packet captures,
raw request/response bodies or customer addresses. Remote cleanup uncertainty
must be reported, not converted to success. Sanitization must precede persistence
and apply to errors as well as success. Unknown/sensitive fields preserved in
memory do not receive retention permission. No real laboratory evidence was
collected during this planning milestone.

## 11. Immediate stop conditions and disposition

| Trigger | Required disposition |
| --- | --- |
| Unexpected product/version/build, contradictory build evidence or unresolved required applicability | No login/next request; return to Gate A/C. |
| TLS certificate/hostname/trust failure or unexpected certificate identity | Stop; no TLS downgrade, trust import, alternate host or retry. |
| DNS/peer outside approved set or unexpected redirect/Location | Stop; no following, alternate-address attempt or credential forwarding. |
| Authentication/session evidence failure, unexpected 401/403 or RBAC mismatch | Stop; no renewal, Basic fallback, broader role or authentication retry. |
| Unapproved method/path/site/role/header or operation-budget excess | Deny before dispatch where possible; stop and report scope breach. |
| Unbounded, excessive, encoded or deadline-exceeding response | Abort bounded processing, attempt local release, retain category/counts only; no truncation-as-success. |
| Unexpected schema, null ambiguity, native-ID mismatch, unknown fields or malformed JSON | Stop; preserve distinctions transiently, no raw retention, field stripping or guessed coercion. |
| Credential/session exposure in body, output, log or evidence | Stop, contain evidence access, notify security owner via approved channel; no automated product-side credential rotation. |
| Session/cookie/credential isolation failure | Stop all affected role activity and local cleanup; treat as security incident, no compensating login. |
| Uncertain backend/resource cleanup or remote-session disposition | Stop; quarantine process/run from further sends and escalate to the named custodian. |
| Unexpected product-side configuration/state change beyond preapproved session/audit effects | Stop immediately; retain only safe incident evidence, notify product owner; do not undo or repair configuration. |

Every stop prohibits automatic retries, corrective configuration writes,
unapproved logout calls or diagnostic API expansion. Preserve the sanitized
primary failure, attempt bounded local-only cleanup, notify the accountable
owner/security contact and require a new explicit decision before resuming.

## 12. Readiness gates and approval register

Gates are per exact product/build/target/role/operation/procedure revision.
A pass on one does not pass another. Plan existence, historical tests, matching
release strings or owner acceptance of A's offline implementation passes none.

| Gate | Required evidence and accountable approval | Current status |
| --- | --- | --- |
| A - Documentation readiness | Integration/evidence owner confirms exact operations/paths, product/build applicability, login/cookie and SitePojo contract policy, least-privilege evidence and selected remote cleanup semantics. Resolve C provenance authoritatively; no adjacent-version inference. | **NOT PASSED** - build evidence, auth/cleanup clarification and C provenance unresolved. |
| B - Backend safety readiness | Backend/security owners approve reviewed DNS, absolute-duration and streaming-size controls or specifically allowed defensible alternatives, numeric bounds, egress/allowlist enforcement, zero retries, TLS, isolation, strengthened auth decisions and bounded cleanup. Record separately authorized offline verification against blocked DNS, trickle/oversize responses and all failure paths. | **NOT PASSED / BLOCKED** - three resource controls and lab integration/auth safeguards not resolved or implemented by this plan. |
| C - Laboratory authorization | Lab/product/data/security owners approve restricted checklist, targets/accounts/roles, exact operations/session side effects, concrete limits, remote-session disposition, storage/ACL/retention, test window, incident contacts and change-observation method. | **NOT PASSED** - information and approvals not supplied. |
| D - Execution authorization | After A/B/C evidence review, project owner explicitly authorizes the exact immutable read-only procedure, implementation revision, operator, target/role bindings, budgets/window and cleanup route. Any material change invalidates authorization. | **NOT PASSED / UNAUTHORIZED** - no execution authorization requested or recorded here. |

Explicit decisions still required: actual lab/build declarations; authoritative
C applicability; site selection/native-ID binding and least privilege; login
session creation and authentication headers/mechanism; optional logout versus
operator revocation/bounded expiry; safety implementation scope and verification;
any separately reviewed risk control; numeric ceilings/rate/budget; data storage,
access and disposal; expected session/audit side effects and state observation;
incident handling; gate decisions; final exact-procedure execution approval.
These are pending requirements, not recorded owner acceptance.

**Overall readiness: PLAN PREPARED; LAB NOT READY; EXECUTION UNAUTHORIZED.**
Stop after this documentation milestone. Production capabilities remain
default-deny; no real product connectivity or laboratory qualification has
occurred.

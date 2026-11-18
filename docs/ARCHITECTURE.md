# Master Application Architecture

Date: 2026-11-18
Status: **Architectural direction approved on 2026-11-17**. CCV-002-A/B/C offline
foundation and contracts implemented; CCV-003-A/B transport and authentication
mock-tested; CCV-003-C adds synthetic-version read clients and a mocked
read-to-plan workflow. CCV-003's implemented mock-only scope is owner-accepted.
CCV-004-A adds offline controller-object normalization, hierarchy validation,
and explicit mapping against a separate supplied destination inventory; that
offline-only scope is owner-accepted. CCV-004-B adds a separate controller
planning validator, acknowledged offline exact comparison, nested CREATE
dependencies, and deterministic redacted candidate plans/summaries.
That offline-only B scope is owner-accepted. Separately authorized CCV-004-C1
adds offline adapters for supplied recursive trees and context-qualified legacy
flat exports, reusing those contracts and their order-preserving serialization.
Its offline-only scope is owner-accepted. Separately authorized CCV-004-C2
adds explicitly associated offline device-detail/access reconciliation, with
per-device evidence acknowledgement and preserved provenance.
Its acceptance-review corrections reject Cyber Controller controller artifacts
at generic planning boundaries and confine acknowledgement comparison exclusions
to policy-validated devices. Unknown root/site configuration remains comparable.
No concrete HTTP backend, production secret resolver,
online execution, or real product/version compatibility is established.

The owner approved ADR-001 through ADR-009 and the documented architectural
amendments. Concrete implementation/storage details remain open where noted;
directional approval does not authorize later milestones or live operations.
The [progress tracker](PROGRESS.md) records approval and verification evidence.
Decision records are in [DECISIONS.md](DECISIONS.md); their proposal-time labels
are superseded by the approval record in the progress tracker.

## Component model

```text
Master CLI/controller
  -> Profile/configuration validation + secret resolution
  -> Orchestrator
       -> Migration modules
            -> Product-specific capability/API clients
                 -> Authentication/session manager
                 -> Shared HTTP transport
       -> Versioned artifact and mapping contracts
       -> Offline validation + candidate planning (no network)
       -> Online destination preflight + reconciliation (authorized reads)
       -> Plan identity + integrity validation
       -> Explicit import approval gate
       -> Post-import read-back verification
       -> Structured result journals + redacted reports/logs
```

Application code lives separately under [src/cc_vision_import](../src/cc_vision_import/).
CCV-001 created documentation only; CCV-002-A/B/C implement the offline subset
described below. CCV-003-A adds backend-independent transport mechanics;
CCV-003-B adds mock-only authentication strategies and local session ownership.
CCV-003-C connects those components to three source-observed reads and the
existing artifact/mapping/offline-plan contracts, using injected fake backends.
CCV-004-A reuses those offline artifact/mapping contracts without changing
authentication, clients, capabilities, transport, or the CLI/mock workflow.
CCV-004-B adds standalone offline comparison/planning APIs; the strict resolver,
generic planner, client workflow, and CLI remain unchanged.
Legacy sources remain read-only and are never imported or executed.

## Responsibilities and interfaces

| Component | Proposed responsibility | Must not do |
| --- | --- | --- |
| Master CLI/controller | Select operation, products, profiles, modules, artifact, and plan; return meaningful exit status. | Hide partial failures or combine export and import implicitly. |
| Configuration/profile layer | Validate separate source/destination product, version, base URL, CA trust, timeouts, and secret references. | Store passwords in committed profiles or infer missing product/version. |
| Shared HTTP transport | Bounded requests, TLS verification, request encoding, redacted error context, and conservative retry policy. | Implement domain logic or assume a write is safe to repeat. |
| Session/authentication layer | Own a session through its full lifetime; delegate login/logout semantics by product capability; clean up explicitly. | Print cookies/tokens or invent an unsupported logout endpoint. |
| Vision API client | Expose only evidence-backed Vision operations for a declared version. | Inherit Cyber Controller support merely because paths look similar. |
| Cyber Controller API client | Expose only evidence-backed controller operations for a declared version. | Treat legacy script naming as compatibility certification. |
| Capability registry | Track product/version, operation, evidence, and verification state. | Enable unsupported operations using a silent generic fallback. |
| Migration module | Export, normalize, validate, compare/plan, apply approved operations, and verify its own domain. | Construct arbitrary HTTP calls outside its client. |
| Orchestrator | Resolve selected-module dependencies, separate offline planning from online preflight, enforce plan integrity/approval, and journal outcomes. | Continue a dependent write after its prerequisite failed or replay an uncertain write without reconciliation. |
| Reporting/logging | Summarize sanitized counts, statuses, unresolved mappings, evidence, and failures. | Include operational payloads, usernames, addresses, secrets, or raw responses by default. |

The implemented foundation uses Python 3.13.14 on Windows, typed dataclasses,
`argparse`, `json`, and `unittest` from the standard library. No dependencies are
installed. HTTP library, broader runtime support, packaging/distribution, and
secret backend remain undecided.

## Product and authentication boundaries

1. Require declared source and destination product/version independently.
2. Resolve a capability before invoking an operation. Unknown compatibility
   blocks that operation, not necessarily unrelated approved modules.
3. Use separate sessions and credentials for source and destination.
4. Preserve source evidence: object scripts configure HTTP Basic authentication
   as well as a JSON login request; LDAP/scheduler use JSON login in a session.
   The required combination must be confirmed, not copied blindly.
5. Keep sessions open during operations and close them deterministically.
   Logout is used only when its path and semantics are established.
6. Default to certificate verification with approved CA configuration. Do not
   silently downgrade TLS. Any exceptional policy needs separate approval.
7. Distinguish invalid credentials, expired session, authorization denial,
   transport failure, malformed responses, and unsupported capability.
8. Never automatically replay writes after authentication renewal or a timeout:
   first reconcile destination state or report an indeterminate outcome.

## Implemented shared HTTP transport - CCV-003-A

[Transport contracts and mechanics](../src/cc_vision_import/transport.py) use only
the standard library. At A's checkpoint authentication/session work was outside
scope; the separately authorized B implementation is described below. There is
no default or concrete HTTP backend, production HTTP dependency, or online CLI
operation. C's separate synthetic capability catalogue does not enable migration.

### Interfaces and injection

- `HttpTransport(TransportConfig(...), backend)` requires an injected `HttpBackend`.
  The backend protocol exposes `send(BackendRequest) -> HttpResponse`.
- `request(HttpMethod, segments, query=(), headers=None, body=None,
  expect_json=False)` supports GET, POST, PUT, PATCH, and DELETE as generic HTTP
  verbs, not evidence that either product supports any corresponding operation.
- Bodies are explicit bytes; GET bodies are rejected. Responses carry status,
  opaque bytes, and headers. Optional JSON expectation checks strict UTF-8 JSON,
  rejecting duplicate members and nonfinite constants using the existing loader.
  No product schema is inferred. Empty 204 responses are valid unless JSON was
  explicitly required. A 202 response is HTTP acceptance, not operation completion.
- The caller owns backend/session cleanup. A future adapter must eagerly consume
  and release each response, enforce certificate/hostname checks and both
  timeouts, and map library IO exceptions to `BackendFailure`. It must perform
  exactly one attempt without redirects, internal retries, authentication
  renewal, ambient proxy/auth behavior, or secret logging.

The injected adapter is a trusted dependency. These obligations are a contract,
not proof that an arbitrary adapter obeys them. No backend has been selected,
implemented, or live-qualified in this milestone.

### Security and configuration

`TransportConfig` validates on construction and at transport initialization:

- A supplied HTTPS origin, reusing existing offline origin validation. No DNS
  resolution or default product address. Invalid-origin parser exception chains
  are discarded so an invalid port or authority cannot disclose input.
- TLS verification defaults to true; false and nonboolean substitutes are
  rejected. Each dispatch uses a standard-library client `SSLContext` with
  certificate verification and hostname checking, never an insecure fallback.
- Optional `trusted_ca` must identify a local existing file accepted by the SSL
  trust loader. Missing, unreadable, invalid-certificate, URL, and UNC paths fail
  explicitly, including mixed-separator UNC forms before file access. Supplied
  CA bundles select trust explicitly; they are not downloaded.
- Required separate connection/read timeouts, finite and greater than zero,
  each at most 300 seconds. Booleans are not numeric configuration.
- GET retry count defaults to zero and accepts only integers from zero to three.
- URL construction accepts tuples of separate path segments and query pairs,
  not relative/absolute URL strings. Components are encoded independently;
  dot traversal, separators, pre-encoded path segments, controls, and invalid
  structures are rejected. Caller data cannot replace the configured origin.
- Header syntax/control characters, case-insensitive duplicates, and overrides
  of Host, Content-Length, Transfer-Encoding, or Connection are rejected before
  dispatch. `redact_headers` masks **all** header values, including custom names,
  cookies, authorization, proxy authorization, API keys, and session identifiers.

URLs, bodies, headers, and CA paths are excluded from normal dataclass
representations. Transport errors contain only fixed categories/messages,
numeric status/attempt count, and a fixed underlying reason category. No raw
backend exception, credential, header, URL, or response body is attached or logged;
unexpected adapter exceptions are surfaced as sanitized `backend_failure`.
Configuration errors retain the existing structured `ContractValidationError`
shape. Raw requests/responses are necessarily available to the backend/caller;
they are sensitive data, not safe logging objects. The transport emits no logs.
Header names are retained by the redaction helper and must not themselves
contain secrets.

### Error and retry semantics

| Category | Classification |
| --- | --- |
| `connection_failure` | Backend-reported connection IO failure on GET. |
| `timeout` | Backend-reported timeout on GET; no implied wall-clock test. |
| `tls_certificate_failure` | Backend-reported certificate/TLS failure on GET; never retried. |
| `authentication_rejection` | HTTP 401; no login/renewal or replay. |
| `authorization_failure` | HTTP 403; no scope broadening or replay. |
| `http_error` | Other non-2xx final statuses, including redirects; no automatic redirect/retry. |
| `malformed_response` | Invalid backend response/status/body type or explicitly expected invalid JSON. |
| `indeterminate_write_outcome` | Any dispatched non-GET with IO/TLS/backend failure, malformed response/required JSON, HTTP 408, or HTTP 5xx. |
| `backend_failure` | Unexpected backend exception, sanitized rather than leaked. |

Indeterminate errors preserve the underlying fixed `reason` and available status.
Even a connection/TLS failure is conservatively uncertain for writes because
this interface has no independently verified "not sent" evidence. Other HTTP
rejections retain their HTTP category but never authorize a replay or certify
unchanged destination state.

Only GET connection/timeout failures can retry when explicitly configured:
at most four total attempts (one plus up to three retries), each with bounded
timeouts. No backoff, Retry-After processing, HTTP-status retry, TLS retry,
malformed-response retry, write retry, or automatic authentication renewal.
Future clients must use GET only for genuinely safe reads. Reconciliation and
separate authorization are required before considering another uncertain write;
the transport cannot reconcile or grant permission.

### Mock verification and limits

[Fake-session tests](../tests/test_transport.py) cover successful verbs, timeout/
connection/TLS failures, rejected configuration, HTTP classification, redaction,
bounded retry, malformed responses, uncertain writes, and URL/header injection.
They inherit the same fail-fast network guards as all 39 unchanged regression
tests; no product address or actual endpoint is exercised. See
[E-007](PROGRESS.md#e-007---ccv-003-a-offline-verification-2026-11-17) for actual
commands/results.

Mocks verify policy, forwarding, and classification, not a TLS handshake,
elapsed network timeout, real CA deployment, or adapter compliance. Successful
custom-CA forwarding uses a mocked trust loader; invalid CA data is rejected by
the real standard-library loader. Python guards are not OS-level isolation:
use trusted local CA files (including their filesystem links) and trusted
adapters. Live qualification, resource limits for real response bodies,
production authentication integration, and product/version capability evidence
remain future work.

## Implemented mock authentication and sessions - CCV-003-B

[Authentication contracts/strategies](../src/cc_vision_import/authentication.py)
and [session ownership](../src/cc_vision_import/sessions.py) build on the unchanged
CCV-003-A transport. This subtask has mock evidence only, not product/version
qualification. B itself adds no real backend, secret-store integration, CLI
operation, configuration migration, or remote logout. C's separately authorized
mock client integration is described below.

### Typed contracts and evidence boundaries

- `CredentialReference` uses the existing opaque secret-reference grammar and
  hides its value from representations. `SecretResolver.resolve(reference)`
  returns validated in-memory `ResolvedCredentials`; no default resolver exists.
- `AuthenticationRequest` requires a source/destination `SessionRole`, declared
  product/version, credential reference, and optional `SessionExpiration` policy.
  Version syntax is checked; accepting it does not assert supported versions.
- `AuthenticationOutcome` records local authentication acceptance with a
  `LoginEvidence` marker or structured `AuthenticationFailure`. Its
  `compatibility_verified` attribute is always false in this implementation.
- `SessionSnapshot` exposes state, expiration reason, product/version/role, and
  `last_authentication`, a **historical** login outcome. Current eligibility is
  determined by `state`/`is_authenticated`, not a previous successful outcome.
- Authentication/session errors have fixed categories for HTTP rejection,
  authorization, application rejection, malformed login response, transport,
  secret resolution, invalid credentials/state, expiration, initialization,
  ownership conflict, cleanup, and clock failures. Where available they retain
  only numeric HTTP status and fixed transport category/reason.

The only login path used is source-observed API-01,
`POST /mgmt/system/user/login`. Scheduler login/logout paths remain unknown and
unused. No cookie name, body token field, renewal endpoint, or remote logout
path is inferred.

| Strategy | Source evidence and implemented mock behavior | Not established |
| --- | --- | --- |
| Vision | [LDAP downloader](../legacy/download_ldap_permissions%20%281%29.py), lines 16-23: JSON username/password, JSON/Accept/XMLHttpRequest headers, HTTP success and body `status == "ok"`. Strict JSON parsing rejects invalid UTF-8, duplicate members, nonfinite constants, nonobjects, and missing/nonstring status; another status string is an application rejection. | Other Vision authentication profiles, version compatibility, token/cookie schema, server TTL. |
| Cyber Controller | [Object downloader](../legacy/app/download_cybercontroller_objects.py), lines 54-85: Basic credentials plus JSON-text login, HTTP 200 acceptance, session auth on subsequent calls. The mock strategy creates JSON safely, includes Basic on login/subsequent managed requests, and exposes `legacy_http_200_only` evidence. | Whether Basic plus JSON is required, application-level success schema, version compatibility, or proof that HTTP 200 means genuine authentication. |

Cyber Controller deliberately does **not** borrow Vision's `status` schema.
Its source-observed HTTP-only rule even accepts an HTTP 200 with a non-JSON or
negative-looking body; this weakness is visible in the outcome marker and tested,
not presented as verified security behavior. Stronger product-specific
validation requires approved evidence. Generic response/status/body validation
still applies through the transport; Cyber Controller's unexpected 2xx statuses
are rejected rather than broadening its observed HTTP-200 rule.

Basic encoding currently supports Latin-1 credentials and rejects colon-bearing
usernames or unencodable values before dispatch. Broader encoding behavior needs
evidence. Vision credentials are encoded safely as JSON without constructing
JSON through string concatenation.

### Ownership and lifecycle

`SessionManager(backend_factory, resolver, clock=...)` is a synchronous,
single-owner context manager. Its factory must produce a fresh, exclusively
owned `SessionBackend` implementing the existing `send` interface plus local
`close`. Within one manager, source/destination cannot share the same active
backend instance or overwrite an unclosed role. Cross-manager sharing and
concurrent use are unsupported; injected factories/backends are trusted.

1. `initialize(request, transport_config)` creates the role's backend and
   transport, validates configuration, and records `initialized`. A failed
   transport initialization cleans up the newly owned valid backend.
2. `authenticate(role)` resolves credentials only at login and sends one POST.
   Success records `authenticated` with the strategy's limited evidence marker.
   Failure records `failed` with a sanitized outcome and blocks further use.
3. `request(...)` forwards generic HTTP mechanics only after authentication;
   this is not a product client or migration implementation. Source/destination
   use separate backends, cookie jars, references, and retained credentials.
   Caller Authorization/Cookie/Proxy-Authorization overrides are rejected.
4. An optional positive finite local lifetime starts at login success, using an
   injectable monotonic clock. Omitted lifetime means **unknown server expiry**,
   not an infinite server session. No TTL is inferred from response fields.
   At the exact local deadline, subsequent status checks/requests mark the
   session `expired` and block dispatch. Clock failures fail closed.
5. HTTP 401 on a managed request marks the session `expired`, records an HTTP
   rejection reason, and raises a structured authentication error. HTTP 403
   remains authorization failure without guessing expiration. Application-level
   expiry in otherwise successful later responses is not modeled without schema
   evidence.
6. `close(role)`/`close_all()` and context exit perform **local cleanup only**,
   release manager-held credentials, and ask the backend to close/discard cookies
   and authentication state. Successful cleanup is idempotent and records
   `closed`; requests remain blocked. Cleanup failure records `cleanup_failed`,
   blocks requests, surfaces a fixed error, and allows explicit cleanup retry.
   Closing all roles still attempts the other role if one close fails.

Failed/expired sessions are not renewed in place: an owner must explicitly close
and reinitialize before another login. Expiration drops retained credentials but
backend resources/cookies remain owned until explicit/context cleanup. Local
close is not remote logout or token revocation. A cleanup error during context
exit takes precedence and suppresses formatting of a potentially sensitive
exception from the context body.

No automatic login renewal or operation replay exists. Login is a POST and never
retries, even with GET retries enabled. Managed writes retain A's single-attempt
behavior and indeterminate outcome categories. Other errors propagate without
replay. A prior uncertain operation still requires reconciliation and approval;
manually creating a new session does not make that write safe to repeat.

### Secret and backend responsibilities

Resolved credentials have protected representations and never enter snapshots,
artifacts, plans, or logs through this implementation. Vision credentials are
not retained by the manager after successful login; the Cyber Controller
source-observed Basic model retains them in memory until failure, expiration,
or cleanup. No plaintext credentials, cookies, or body tokens are serialized or
logged by application code. Existing reference-only artifact contracts are
unchanged. Mock credentials and cookie markers are synthetic only.

Resolver, factory, clock, and local close exceptions are sanitized at their
boundaries. Errors do not attach raw callback exceptions, response bodies,
usernames, passwords, cookies, or tokens. Raw request/body/header data necessarily
passes to trusted backends. Protected representations are not encryption or a
guarantee of memory zeroization: Python objects, debugger/frame locals, resolver
caches, and backend-held copies require separate operational policies. Do not
serialize resolved credentials or capture raw locals/payloads in logging.

A future backend must actually isolate cookie jars, enforce TLS/timeouts, avoid
internal retry/redirect/auth-renewal behavior, close local resources, and discard
session secrets on `close`. Neither those real IO behaviors nor genuine server
authentication are proven by the protocol. This milestone implements no backend
or production resolver. The API matrix separately records source evidence and
mock coverage; neither establishes real product/version compatibility.

### Verification

[Authentication/session tests](../tests/test_authentication.py) use synthetic
responses, a fake owned session backend, injected resolver/clock, and the existing
transport/network guards. All 60 existing regressions are retained unchanged.
Actual commands, results, static checks, restrictions, and limits are recorded in
[E-008](PROGRESS.md#e-008---ccv-003-b-offline-verification-2026-11-17).

## Implemented mock product clients and integration - CCV-003-C

### Capability and product boundaries

[Mock declarations](../src/cc_vision_import/mock_capabilities.py) define a closed
tuple of three development/test operations, separate from the empty production
`VERIFIED_CAPABILITIES` catalogue in
[capabilities.py](../src/cc_vision_import/capabilities.py).
Each records product, exact version, operation,
fixed URL segments, API-matrix evidence record, source-observed evidence, a
`synthetic-mock-only` qualification, and a `synthetic-unverified` response schema.
Official-documentation, live-testing, and compatibility flags remain false.

The owner explicitly approved **`0.0-test` only** for these mock capabilities
because the legacy evidence establishes no supported product versions. This is
an application-owned synthetic marker, not a Radware release or compatibility
range. Unknown products, every other version, cross-product operations,
arbitrary trees, and unresolved scheduler operations fail closed. There is no
wildcard version match, registration fallback, version discovery, or claim that
missing evidence proves vendor non-support. Profile syntax validation and B's
generic authentication contracts remain independent of C's client capability
gates.

Default catalogue lookup never falls back to mock entries and rejects
`0.0-test` even if it is mistakenly added to the production catalogue.
`mock_only=True` explicitly selects synthetic metadata; operational access also
requires an injected backend implementing the nominal `MockSessionBackend`
contract. Client construction and every read check that backend declaration,
including after role reinitialization. An arbitrary backend with an `is_mock`
attribute is not sufficient.

The workflow's `SessionManager(..., mock_only=True)` rejects unmarked backends
before the affected role's credential resolution/authentication and cleans up
newly rejected closeable instances through the existing sanitized path.
Ordinary session-manager defaults remain unchanged for the existing generic
authentication contracts. Neither a mock-policy flag alone nor a future real
HTTP adapter implementing only the ordinary protocol gains synthetic API access.
The nominal mock contract is a trusted development assertion, not OS-level
isolation; network adapters must never implement/register as that contract.

[Product clients](../src/cc_vision_import/product_clients.py) expose separate
typed read interfaces:

| Client | Public operation | Source evidence |
| --- | --- | --- |
| `CyberControllerClient` | `export_physical_tree()` | API-02, GET `/mgmt/system/config/tree/Physical` |
| `CyberControllerClient` | `export_organization_tree()` | API-03, GET `/mgmt/system/config/tree/Organization` |
| `VisionClient` | `list_ldap_permissions()` | API-10, GET `/mgmt/system/config/itemlist/ldapobjectpermission` |

Each client borrows a caller-owned manager/role, checks the product/version
binding at construction and before every read, and forwards GET through the
existing session/transport stack. It neither owns cleanup nor authenticates,
renews, invents logout, exposes writes, or discovers extra endpoints. HTTP 401
expires only the affected role; other authentication/transport errors retain
their existing structured categories. Unsupported capability, session mismatch,
and malformed API shape have fixed `ProductClientError` categories without raw
payloads, credentials, or supplied version strings. No logging is introduced.

### Synthetic response assumptions and artifact boundary

These shapes are deliberately unverified, not vendor API schemas:

- Physical/Organization: a JSON object with `meIdentifier.managedElementID`
  containing nonblank text and `children` containing child objects with the
  same minimum shape. The mock parser checks descendants and limits tree depth
  to 64. No managed-element class, device access, pagination, or completeness
  semantics are inferred.
- LDAP: a JSON array containing objects, including an empty array. No permission
  field interpretation, scope broadening, device-lock changes, or pagination
  behavior is implemented.
- Strict JSON syntax/UTF-8 failures retain the transport's malformed-response
  category. Valid JSON with the wrong minimum shape raises a client error;
  malformed data never becomes an empty success.

`ReadResult` hides its opaque objects from representations.
`to_artifact(exported_at=...)` uses the existing schema-1 parser, reference-only
secret policy, deep copying, and offline-validation contract. A tree is retained
as **one opaque root object**, not flattened into portable sites/devices. LDAP
entries remain separate objects. The domain is the synthetic capability name.
Caller-supplied export time is required; the exporter identifies a synthetic
mock client. Full JSON-value/secret checks occur at the artifact boundary,
including rejection of numeric overflow decoded as infinity. Validation status
`valid` means offline contract validity only.

### Minimal read-to-plan workflow

[build_mock_plan](../src/cc_vision_import/mock_workflow.py) requires synthetic
source/destination declarations, a selected read capability, an explicit planning
request and export timestamp, mandatory connection/read timeouts, an injected
backend factory, and an injected secret resolver. No backend or resolver is
constructed by default.

1. Load and validate separate profiles; require both secret references; reject
   unsupported source operation or either product/version before backend creation.
2. Own distinct role backends in a context-managed `SessionManager` and authenticate
   with the existing distinct product strategies. Shared backend identity is
   rejected by B's ownership rules.
3. Read source data through the selected product client. Destination is
   authenticated independently, but **no destination inventory/preflight is
   performed**.
4. Construct and explicitly validate a schema-1 artifact, serialize exact bytes,
   and call the existing `create_plan` with caller-declared mappings/actions.
   The plan destination must match the authenticated destination profile's
   product/version/origin. Controller identity remains a supplied assertion.
   Profile/planning contract errors are re-raised outside their handlers with
   only the structured validation result, removing raw URL-parser exception
   chains (including supplied invalid-port text).
5. Return the artifact and offline candidate plan only after context cleanup.
   Unresolved/ambiguous mappings remain blocked; missing mapping records fail.
   No identity extraction, comparison, or real cross-product conversion is
   inferred. Synthetic known-semantics/comparison declarations are not API proof.
6. `MockWorkflowResult.summary()` returns counts, plan status, fixed offline
   stage, mock-only/compatibility flags, and zero executed writes. Result
   representations hide artifact/plan contents. Summary serialization contains
   no identifiers, origins, references, credentials, cookies, or response bodies.

Raw artifact/plan access is explicit and is **not** a redacted report. Do not
serialize whole result dataclasses or arbitrary opaque API payloads as logs.
The existing generic artifact policy cannot detect secrets disguised as arbitrary
free text; producers remain responsible for classification. Protected reprs do
not erase credentials from Python memory.

The workflow adds no CLI mode, automatic authentication renewal, configuration
write, simulated apply/verification, approval mechanism, or remote logout.
Read retries remain disabled in its configurations; client callers may separately
use A's explicitly bounded GET policy. Authentication POSTs are never replayed.
All initialized roles receive local cleanup on success/failure; cleanup failures
remain sanitized errors, not successful results. Failed local close cannot
guarantee resource release and follows B's existing failure semantics.

### Verification and limitations

[Client tests](../tests/test_product_clients.py) and
[mocked integration tests](../tests/test_mocked_integration.py) exercise all
three reads and each read-to-plan path using in-memory fakes and the shared
15-entry fail-fast network guard. They test authentication/application rejection,
local/HTTP expiration, independent roles/cookies, unsupported capabilities,
malformed responses, absent/unresolved/ambiguous mappings, shared-backend
rejection, sanitized cleanup failure, invalid-port parser chaining, and
raw/encoded-secret redaction.
Actual full-suite evidence is recorded in [E-010](PROGRESS.md#e-010---ccv-003-c-mocked-client-and-integration-verification-2026-11-17).

No live compatibility is established. Cyber Controller authentication still has
only source-observed HTTP-200 acceptance, not application-status validation.
Real TLS/timeouts/cookie isolation/response disposal remain future trusted-adapter
obligations. An injected backend is executable trusted code, not sandboxed by
these interfaces; this repository provides no concrete network backend. Python
test guards establish zero guarded attempts, not OS-level isolation.
The workflow sanitizes existing parser chains at its own boundary; direct calls
to older profile/plan parsers have not been changed by this milestone.
The separately authorized CCV-004-A/B and C1 offline contracts are described
below. C1/C2 add no client operation; all live/backend development and C3 remain
unauthorized.

## Implemented offline controller objects and identity mapping - CCV-004-A

[Controller objects](../src/cc_vision_import/controller_objects.py) and
[explicit mapping](../src/cc_vision_import/controller_mapping.py) are reusable
Python APIs, not export/import commands or production schema certification.
They do not construct sessions, request API data, fetch device-access details,
resolve secrets, perform semantic comparison, or execute writes.

### Legacy observations and intentional safety differences

Static inspection of the three object scripts establishes:

- The downloader traverses `children`, recognizing exact managed-element
  `Site` and `Device` classes; native IDs come from
  `meIdentifier.managedElementID`. Sites contain other sites/devices.
- Its flat `sites`/`devices` output stores names, IDs, `parentOrmID`, site
  `parent_site_name`, device `type`, and `managementIp`. Tree identity is
  external to that flat payload. Unknown native fields/classes are dropped.
- Device access is fetched separately, joined by management IP, and moved from
  `deviceSetup.deviceAccess` to top-level `deviceAccess`; nested access `ormID`
  is deleted. This is not a verified portable credential/reference schema.
- Upload resolves destination parents by name and can fall back to root;
  update supplies the exported device ID as destination `ormID`. Neither
  behavior is carried into the new contracts.

The credential transformer's field names were additionally inspected as text
only: CLI/HTTP/HTTPS and SNMPv3 usernames/passwords are sensitive. No legacy
module, credential configuration, or operational export was loaded/executed.

### Normalized records and field preservation

- Typed root, site, device, device-access, inventory, and
  `SourceObjectReference` records. A reference contains controller identity,
  explicit `Physical`/`Organization` tree, object kind, and native ID.
- Schema-1 artifacts reuse domain `controller-objects`, declared Cyber
  Controller product/version, existing export metadata and JSON/secret
  validation. Roots are explicit objects and count toward inventory/mapping
  totals. Previously invalid artifacts cannot be silently promoted to valid.
- `normalize_tree` consumes an explicitly supplied synthetic nested tree.
  The root frame is supplied by the caller; no undocumented root class is
  invented. Known site/device classes cannot masquerade as roots. Only the
  two observed child classes are modeled. Devices have absent/empty child
  arrays; root/site child arrays are mandatory. Unknown classes, malformed
  child shapes, and excessive nesting fail rather than disappear.
- Known fields move to typed fields; unknown JSON remains in configuration.
  Native `meIdentifier` extras, consistent `ormID`/`parentOrmID` provenance,
  device-setup extras, and **device-access `ormID`** are preserved. Contradictory
  aliases or duplicate native/normalized representations require reconciliation.
  There is no native wire-payload serializer or implicit reference rewriting.
- Device-access location distinguishes absent, top-level, and nested values,
  including explicit null. Conflicting locations are rejected, not merged.
  Missing access is not enriched or replaced by an empty object. Non-sensitive
  access settings and opaque secret references are retained without resolution.
- Inventories are deep-copied at parsing boundaries and revalidated when
  converted to artifacts, including after nested configuration mutation.
  Direct dataclass construction alone is not validation.

Generic artifact secret-key checks are supplemented by username/user/login,
security-name, passphrase, authentication-key, and privacy-key recognition.
Sensitive values require null or an opaque `secret_ref`; raw values fail with
fixed messages and positional paths. Names, IDs, addresses, configuration, and
credential references are excluded from new object/result representations.
New boundaries strip underlying parser exception chains. No logging is added.
Artifacts contain intended configuration and references, not redacted reports.
Arbitrary secrets disguised in unrecognized free-text fields cannot be
generically detected; synthetic-only evidence does not certify real exports.

### Hierarchy and explicit destination resolution

- One declared controller per inventory; exactly one root per represented tree.
  Physical/Organization references remain distinct even for equal native IDs.
  IDs are unique within a tree, across object kinds.
- Reject missing/incorrect/cross-context parents, device parents, root parents,
  duplicate/conflicting identities, cycles/self-reference, and malformed nodes.
  Reuse the existing dependency-order validator.
- The owner's Option 1 clarification supersedes initial duplicate-name rejection:
  preserve every object with a distinct stable ID, including duplicate names,
  and preserve its configuration in exported artifacts. Equal names under
  different parents, trees, or object types are not name ambiguities.
- `assess_controller_identity` separately reports `ambiguous_name` for **every
  affected same-type sibling**, using positional paths without names or IDs.
  An invalid identity assessment is not an invalid artifact: export/round-trip
  remains available without discarding duplicates. A valid assessment means
  only that no same-type sibling-name collision was found, not that names can
  establish identity or that mapping/import is authorized. Names remain exact,
  case-sensitive, and never silently normalized.
- Existing `ObjectIdentity` uses a canonical JSON array `[controller_id, tree]`
  as its namespace, object kind as type, and native ID as ID; delimiters cannot
  collapse distinct context components.
- `resolve_controller_mappings` requires distinct declared source/destination
  controller contexts and independently supplied, revalidated inventories.
  Every source record, including each root, needs an explicit existing
  `IdentityMapping` with exact index, identity, domain, and product contexts.
  No mapping is inferred from names, addresses, ordering, or source IDs.
- Destination identities must exist in the supplied destination inventory;
  tree/type changes, collisions, unresolved/missing/ambiguous states, relocation,
  inconsistent parent mappings/dependencies, and dependency cycles fail.
  Source parent must map to the actual destination parent; no root fallback.
  Equal raw ID strings are allowed only through explicit destination-qualified
  mappings to a separately present destination record.
- Explicit qualified mappings may resolve otherwise name-ambiguous objects.
  Source/destination ordering and repeated names never select a target.
  Unresolved/ambiguous mappings remain rejected by the existing resolver.
  There is no automatic name matcher or import path; ambiguity grants no
  automatic mapping/import permission and does not erase the source artifact.
- Resolution returns existing mapping contracts and a counts/status validation
  result; it does not rewrite configuration, attest inventory provenance,
  establish semantic equivalence, or authorize create/update operations.

### Verification and remaining gates

[Tests](../tests/test_controller_objects.py) use synthetic
[Physical](../tests/fixtures/controller-physical.json) and
[Organization](../tests/fixtures/controller-organization.json) fixtures plus
derived simple/invalid/ambiguous cases under the existing 15-entry network guard.
A regression feeds resolved mappings and the exact normalized artifact bytes to
the existing planner/integrity verifier: unknown semantics/comparison yield
blocked actions with no changes. The accepted C workflow remains unchanged.
See [E-013](PROGRESS.md#e-013---ccv-004-a-offline-object-and-mapping-verification-2026-11-17)
for the initial implementation and
[E-014](PROGRESS.md#e-014---ccv-004-a-option-1-duplicate-name-clarification-2026-11-17)
for the superseding duplicate-name policy and current focused/full-suite results.

Both trees' detailed node layouts, string-only device type/address assumptions,
root classes, identifier aliases, duplicate rules, device-access portability,
cross-tree device behavior, pagination/completeness, and destination provenance
remain unverified against products. A itself added no adapter for the
context-deficient legacy flat export; the separately authorized C1 adapter below
requires explicit source-root context. There is no automatic parent-name or by-IP lookup.
Offline product/version declarations grant no capability: production remains
default-deny and `0.0-test` remains restricted to mocked API development.
CCV-004-B's separately authorized offline comparison/planning extension follows.
Credential transformation, real export/import, and live qualification remain
separately gated.

## Implemented offline semantic comparison and CREATE planning - CCV-004-B

The owner authorized B on 2026-11-18, following A's acceptance and Category B
architecture assessment. B adds no network adapter, API operation, import,
overwrite/delete behavior, or credentials/secret resolution.

### Separate controller planning validator

[controller_planning.py](../src/cc_vision_import/controller_planning.py) provides
`validate_controller_planning(source, destination, mappings, complete_trees=(),
device_access_acknowledgements=())`.
It revalidates/copies normalized inventories and reuses the existing explicit
mapping parser, identity types, and dependency-order validator.
`resolve_controller_mappings` remains unchanged and still rejects missing
targets for operations requiring existing destination identities.

- Require distinct declared source/destination contexts and exact source
  index/qualified identity/domain/product-version bindings for supplied mappings.
  Malformed records, duplicate mapping IDs/indices, and cycles fail structurally.
- The shared validator enforces the universal C2 access policy for every device
  carrying access, whether normalized directly by A/B, exported through C1's
  recursive/flat adapters, or reconciled by C2. Source and mapped destination
  acknowledgements must bind qualified identity, relevant source/access data,
  policy version, and protected opaque evidence. Missing/stale acknowledgements
  make affected entries invalid; comparison consumes those entries to emit
  BLOCKED. Direct validator calls cannot bypass the gate by omitting comparison.
  Malformed/duplicate/unknown acknowledgement declarations are rejected.
- Access policy independently rejects empty/null access and uncertain device
  credentials, regardless of acknowledgement hashes. The validator also retains
  credential-uncertainty checks for all controller objects and mapped targets.
  No acknowledgement overrides configuration/hierarchy/identity errors or
  enables an unsupported transformation. Original artifacts remain unchanged.
- Every represented source root must explicitly resolve to an existing
  destination root in the matching tree. A missing/unresolved root cannot become
  CREATE; affected dependents are blocked, without blocking the other tree.
- Absent mapping records are reported as `mapping_absent`; unresolved/ambiguous
  states stay blocked. An existing-target mapping whose target is absent is
  `destination_absent`, not an inferred MISSING state.
- Per owner policy clarification, CREATE needs **both an explicit MISSING
  mapping and a declared-complete destination tree**. `complete_trees` defaults
  empty, takes explicit tree enums, and may reference only trees with destination
  roots present. These are bound offline assertions, not live completeness proof.
  Existing explicitly mapped objects may still be compared in a partial tree.
- Missing non-root objects may depend on a mapped existing parent or another
  MISSING parent eligible for CREATE. Parent mappings/dependencies must agree
  with the source hierarchy. Existing children cannot silently relocate beneath
  a planned parent. Cross-tree targets/dependencies and target collisions block.
- A mandatory parent edge is retained even when a supplied parent mapping is
  absent/invalid, so blocking propagates; this never repairs that mapping or
  grants permission. Extra valid dependencies are honored. Diagnostics are
  positional fixed codes/messages; no names, IDs, or payloads are reported.

### Explicit comparison semantics and conservative classification

[controller_comparison.py](../src/cc_vision_import/controller_comparison.py)
provides `compare_controller_inventories` with the same inventory/mapping/
coverage inputs, `semantics_known_for=()`, and `comparison_rules=()`. The owner selected **per-object
explicit offline policy acknowledgement**, rather than assuming unknown fields
have portable product semantics. Acknowledgements identify qualified source
references, are checked against the source inventory, and are bound into the
plan. Default acknowledgement is empty: even identical data remains BLOCKED.

For acknowledged objects, policy `acknowledged-normalized-exact-v2` compares
all retained normalized settings exactly. The owner's 2026-11-18 clarification
supersedes B's initial implicit exclusions, dictionary sorting, and opaque
credential-reference equality:

- Compare names as settings only after explicit identity mapping; never match
  objects by name/address/order. Compare device type/address, access location/
  value, unknown configuration, and native identifier extras.
- No configuration fields are excluded by default. In particular, different
  native identity aliases produce CONFLICT unless an explicit rule is selected;
  conflicting prerequisites then block their dependents.
- The only supported opt-in rule is
  `ControllerComparisonRule.NATIVE_IDENTITY_PROVENANCE`
  (`validated-native-identity-provenance-v1`). It excludes exactly top-level
  configuration `ormID`/`parentOrmID` and
  `configuration.meIdentifier.managedElementID` from a copied projection.
  Evidence is **local offline contract validation**:
  `controller_objects._native_bindings` checks each alias against its qualified
  object/parent reference, and `validate_controller_planning` independently
  checks destination identities and parent mappings. This is not official
  evidence that arbitrary product fields are server-managed or ignorable.
  No arbitrary exclusion paths or other server-managed-field rules are accepted.
  Empty identifier containers, native classes/extras, and device-access `ormID`
  remain significant. No source/artifact data is removed or rewritten.
- Preserve unknown configuration dictionary-member order, nested dictionary
  order, array order, JSON types, field absence versus null, and exact strings.
  No sorting, case folding, address normalization, default substitution, or
  inferred equivalence is applied to those settings. Known typed-record and
  plan-envelope members are named contract fields, not unknown configuration;
  canonical envelope encoding remains separate from ordered settings encoding.
- Any unresolved secret reference, credential field containing null, explicit
  null device-access value, or recognized mask marker blocks the affected
  object's comparison and CREATE decision with `unresolved_credentials`.
  Both source and resolved destination are checked before any exclusion rule.
  Equal reference labels or equal masks never establish credential equivalence.
  Existing structural validation still rejects raw credentials, including raw
  masked values in sensitive fields. The shared controller credential-field
  classifier is reused by structural checks and comparison.
- Per-object acknowledgement authorizes offline representation comparison only,
  not vendor compatibility, live equivalence, secret migration, or changes.

| Classification | Conditions |
| --- | --- |
| CREATE | Explicit MISSING non-root mapping; destination tree declared complete; semantics acknowledged; no credential uncertainty; parent/dependencies eligible. |
| SKIP | Existing explicitly resolved target; acknowledged full settings compare exactly equal under the recorded rules; no credential uncertainty; dependencies unblocked. |
| CONFLICT | Existing explicitly resolved target; acknowledged settings differ. No update/overwrite is proposed. |
| BLOCKED | Unknown semantics, unresolved/masked credentials, absent/unresolved/ambiguous mapping, incomplete missing-target evidence, invalid root/target/hierarchy/dependency/collision, or blocked/conflicting prerequisite. |

Parents precede children. Conflicting/blocked prerequisites block dependents;
unrelated branches/trees remain independently classifiable. All source objects,
including duplicate names, remain represented. Destination-only objects are
left untouched; no DELETE or overwrite action exists.

### Redacted deterministic plans, summaries, and verification

`ControllerMigrationPlan` is a controller-specific **redacted schema-2** envelope,
stage `offline-controller-candidate`, not a replacement for the existing generic
`MigrationPlan` contract (which intentionally carries raw qualified mappings).
Shared action/comparison enums and graph validation are reused; specialized
classification incorporates the additional controller safety gates.

- One immutable action per source object: generated action label, source index,
  optional destination snapshot index, tree/kind, semantics-acknowledgement flag, classification, comparison,
  logical parent/dependency action labels, and fixed issue codes.
- CREATE has no destination index or fabricated destination ID. A parent planned
  for creation is referenced by its logical action label, never a placeholder
  native ID. This is planning only; destination ID assignment/binding after
  actual creation is not implemented.
- Plans, summaries, and default representations contain no object names, native
  IDs, raw mapping IDs, controller labels, addresses, configuration, usernames,
  credentials, or secret references. Snapshot digests and positional references
  let retained input artifacts carry the complete configuration separately.
- Explicit `comparison_policy` metadata records policy ID, fixed policy/evidence
  identifiers, selected rules, local rule-evidence identifiers, exact excluded
  paths, order/credential policies, and offline-only authorization scope.
  Summaries also expose policy/rule/evidence identifiers without payload data.
- Order-preserving source/destination snapshot hashes bind all preserved fields,
  including provenance excluded by an explicitly selected rule. A declaration digest binds
  explicit mappings, tree completeness, acknowledgement indices, and policy.
  Deterministic plan ID/integrity cover those digests and ordered actions.
  Mapping record order does not change the result; snapshot indices/order are
  intentionally bound, not automatically reidentified.
- The standard `ConfigurationArtifact.to_json()` preserves dictionary-member
  order recursively for domain `controller-objects`. This applies equally to
  inventories converted with `to_artifact()` and controller artifacts reparsed
  through the generic artifact parser. There is one supported controller JSON
  serialization contract, without a mode switch or parallel format.
  Other domains retain their existing recursively sorted-key serialization.
  `to_dict()`, controller normalization/parsing, planning snapshot copies, and
  standard Python JSON decoding preserve configuration ordering; plan-envelope
  canonicalization does not contain or reorder raw configuration.
- Serialize controller snapshots with that standard method, or retain the
  order-preserving artifact dictionaries without reordering them. External
  key sorting/canonicalization is not a supported controller serialization
  path. Verification rejects reordered snapshots or candidates generated from
  them when compared against independently retained original snapshots.
  It cannot establish historical fidelity if both inputs were already lossy.
- `to_json`/`to_dict` check internal integrity. `summary()` emits fixed per-tree
  counts and per-action statuses/reason codes, explicitly denying execution.
  `verify_controller_plan` recomputes from independently retained input snapshots
  and declarations and compares canonical JSON, including JSON type distinctions.
  Hashes are not signatures or authorization; no approval/import path is added.
  Initial schema-1 controller candidates must be regenerated and reverified
  under policy v2; they are not silently accepted as schema-2 plans.

The new Python APIs are not wired into the CLI, API clients, generic plan/result
parser, or accepted C mock workflow. Use their own recomputation verifier; a
redacted controller candidate is not an executable import or generic plan file.
No new production capability or product/version compatibility is enabled.

### Verification and limitations

[Comparison tests](../tests/test_controller_comparison.py) reuse A's synthetic
tree fixtures and the existing 15-entry network guard. They cover all four
classifications, per-object semantics, incomplete/per-tree coverage, root gates,
absent/unknown/ambiguous mappings, duplicate preservation, nested CREATEs,
parent conflict propagation, no relocation, collision/cross-tree/dependency
errors, deterministic/redacted output, input preservation, and integrity.
Additional policy regressions exercise default/no implicit exclusions, the
finite evidence-backed opt-in rule, significant dictionary order and snapshot
binding, unresolved/masked credentials, unchanged original fixtures, explicit
policy metadata, and recomputation rejection after policy/order changes.
The standard-serializer regressions additionally exercise inventories through
controller artifacts, repeated serialization/generic parsing, comparison,
schema-2 candidate JSON, and recomputation verification. Dictionary ordering at
the configuration level and within nested objects/array members stays
significant; identical data stays SKIP with unchanged snapshot/plan identity.
Array/type/null distinctions, secret handling, unsupported domain rejection,
lossy external reserialization rejection against retained originals, and
noncontroller sorted-key compatibility are covered.
See [E-018](PROGRESS.md#e-018---ccv-004-b-serialization-fidelity-correction-2026-11-18)
for the final **220 passing tests** and zero guarded attempts. E-016/E-017
retain the earlier implementation/policy evidence; E-018 corrects the
acceptance-blocking standard-serialization defect discovered after E-017.

Artifact schema 1 and controller-plan schema 2 are unchanged. Controller
artifact JSON bytes may differ from earlier sorted output, so independently
retained byte hashes must not be transferred to reserialized artifacts.
Generic plans still bind their exact original input bytes; controller plans
still bind their order-preserving normalized snapshots. Regenerate/reverify
affected candidates rather than substituting newly encoded bytes.

All semantics/completeness assertions and inventories remain trusted offline
inputs. No live preflight, real schema qualification, production readiness,
credential portability, native write-payload generation, actual ID binding,
approval/apply/verification execution, or durable journal is established.
Mask recognition is conservative, not a general detector of secrets concealed
in arbitrary free text; recognizable literal markers may also block. Per-object
acknowledgement cannot override credential uncertainty. No general field-order
normalization or real-product server-managed-field exclusion rule is supplied.
Historical sorted controller artifacts cannot recover their original member
order from JSON alone. Do not acknowledge exact-order semantics for legacy or
externally reformatted inputs of uncertain fidelity: keep them UNKNOWN/BLOCKED
until trusted, order-preserving source snapshots can be supplied. The engine
does not authenticate input provenance or detect transformations made before
its input boundary without independently retained originals.
The subsequently authorized C1 adapters are described below; C2 and
live/backend work still require separate authorization.

## Implemented offline legacy export adapters - CCV-004-C1

The owner authorized C1 only on 2026-11-18.
[controller_exports.py](../src/cc_vision_import/controller_exports.py) transforms
supplied data, not live controllers. It adds no competing object model, HTTP
backend, endpoint, API permission, automatic matcher, CLI command, or execution
path. Raw adapters explicitly accept only synthetic version `0.0-test`.
Real versions remain unsupported and the production capability catalogue stays
empty. The existing mock-client backend/session gates are unchanged.

### Source evidence and representation contracts

Read-only inspection of the legacy downloader, uploader, and updater confirms:

- Physical and Organization reads are separate recursive `children` trees.
  Nodes use `meIdentifier.managedElementID`, exact Site/Device class names,
  site/device `name`, and device `type`/`managementIp`.
  Containment supplies the parent; optional native parent aliases must agree.
- The downloader's flat file contains `sites` and `devices`. It records native
  IDs as `id`, parents as `parentOrmID`, and extra site `parent_site_name`.
  It omits the original root and discards fields outside its selected subset.
- Device access is obtained separately from a by-IP detail response at
  `deviceSetup.deviceAccess`, then attached to flat devices as `deviceAccess`.
  The legacy script deletes access `ormID` and joins by address. C1 does neither:
  no detail lookup or automatic enrichment is implemented.
- The uploader's name lookup/root fallback and updater's source-ID reuse are
  not copied. Parent names are preserved only as opaque provenance.

These are source observations, not documented/live schemas. Root class,
response completeness, required access keys, devices across both trees,
address uniqueness, and server-side reference/credential semantics are unknown.
Synthetic fixtures exercise local handling; they do not upgrade this evidence.

### Adapters and explicit context

- `adapt_tree_response(payload, controller_id, tree, version, exported_at)`
  validates/copies JSON and reuses `normalize_tree`. Every source object is
  retained or the entire operation fails explicitly. Unknown classes, malformed
  JSON-compatible structures, missing fields, duplicate stable IDs, invalid
  native aliases/parents, and credential values are never silently skipped.
- `adapt_flat_export(payload, root_response, controller_id, tree, version,
  exported_at)` requires an independently supplied **source** root response
  with explicit native root identity and an empty `children` array. The flat
  file alone cannot establish that root or tree and is not sufficient input.
  A nonempty root response is rejected rather than silently dropping children.
  This source root is not an implicit destination root mapping.
- Flat parent references resolve against the complete supplied native-ID table,
  including the explicit root. Site row ordering and parent-name strings never
  choose parents. Missing/device/self/cyclic parents and duplicate IDs fail
  through the existing hierarchy/dependency rules. No default/root fallback.
- Flat site/device array order is retained as normalized object order (root,
  sites, devices); the flat format has no original cross-array sibling order
  to recover. Each record's native `id` and `parentOrmID`, parent-name provenance,
  and unknown configuration fields are preserved. No managed-element class or
  source/destination ID is invented. Known fields move into the existing typed
  name/device/access contracts. Unknown envelope fields are rejected: C1 has no
  safe model for relocating them into an arbitrary root's configuration.
- `adapt_controller_read(ReadResult, controller_id, exported_at)` consumes one
  existing Cyber Controller mock tree result and selects its explicit tree.
  It checks the unaltered synthetic capability declaration against the existing
  mock catalogue; Vision, non-tree operations, malformed envelopes, forged
  declaration flags, and unsupported versions are rejected.
  The data adapter is not proof of a backend's origin and grants no network
  permission. Only the existing clients perform mock-backend/session checks.

### Artifact fidelity, identity, and incomplete access

`ControllerExportResult` contains an existing `ConfigurationArtifact` (hidden
from default representation), a fixed-message positional validation result,
the existing separate identity assessment, and evidence/completeness labels.
It is a result wrapper, not another controller object schema.

- Configuration dictionaries retain insertion order recursively, including
  dictionaries inside arrays and device-access settings. JSON types, unknown
  configuration, array order, and unknown-field absence/null remain distinct.
  Controller artifact schema 1 and standard order-preserving `to_json()` are
  reused. C1 never canonicalizes raw configuration or changes plan schema 2.
- Generic artifact validation first validates/copies the entire supplied
  response. Controller validation adds recognized usernames/login/SNMP fields.
  Raw credentials and raw masked sensitive values fail with redacted errors;
  no silent redaction, field deletion, secret lookup, or credential conversion.
  Callers must supply contract-valid opaque secret references or null
  placeholders. Their labels are retained, not resolved or certified as
  production-authorized. The existing comparison engine blocks unresolved
  references/null credentials/masks even when both sides use identical values.
- Missing, explicit null, or empty device-access data produces
  `incomplete_device_access`. All objects/settings remain in the returned
  artifact, which is marked **invalid** and remains invalid after serialization.
  `to_inventory()` and ordinary controller artifact parsing then fail closed.
  The conservative scope is the whole incomplete artifact, not a silently
  partial planning inventory. No empty access record is substituted.
- A nonempty access dictionary establishes only structural availability.
  `completeness="unverified"` is always reported, even with no local issues:
  there is no authoritative required-field list or live completeness evidence.
  Structural `validation.status="valid"` does not assert a complete export,
  product compatibility, resolved credentials, or permission to compare.
- Duplicate same-type sibling names are preserved in valid artifacts and
  reported as `ambiguous_name` by `identity_assessment`, consistent with the
  accepted A policy. Explicit qualified destination mappings may resolve them;
  absent/unresolved/ambiguous mappings remain BLOCKED. Duplicate stable native
  IDs are invalid; names never replace them.
- `to_inventory()` reparses the protected artifact using the existing controller
  contract. From there, strict identity mapping, per-object semantics
  acknowledgement, resolved existing destination roots, confirmed MISSING and
  declared-complete trees, and parent dependencies retain all B safety gates.

### Verification and remaining scope

[Adapter tests](../tests/test_controller_exports.py) and the
[synthetic response collection](../tests/fixtures/controller-export-responses.json)
exercise Physical/Organization, nested sites, multiple devices, unknown/order-
sensitive fields, malformed nodes, missing parents, duplicate siblings, and
incomplete access. Tests demonstrate:

1. Synthetic response -> adapter -> normalized inventory -> artifact -> standard
   JSON encode/decode -> comparison -> candidate plan -> schema-2 recomputation.
2. Both representations and trees, explicit synthetic destination mappings,
   unchanged SKIP for identical configuration, CONFLICT for dictionary/access/
   array/type/null differences, and nested CREATE candidates without assigned
   destination IDs.
3. Injected in-memory source/destination mock sessions -> existing read client ->
   adapter -> plan, with independent credentials and backend cleanup. A separate
   malformed-node case confirms exception-safe cleanup after adapter failure.
4. Invalid/incomplete artifacts remain rejected after roundtrip; credential
   errors/report representations do not expose tested secret values/references.

Full offline suite: **244 tests passed**, retaining all **220** existing tests
plus **24** adapter regressions, with **zero guarded network attempts**.
Actual commands/results are in
[E-020](PROGRESS.md#e-020---ccv-004-c1-offline-export-adapters-2026-11-18).
C1's implemented offline-only scope is owner-accepted on 2026-11-18; see
[E-021](PROGRESS.md#e-021---ccv-004-c1-owner-acceptance-2026-11-18).
No legacy script was executed/modified and no API was contacted.

Limitations: flat files cannot restore root/configuration/access fields already
discarded by legacy code; earlier lost ordering cannot be reconstructed.
Source-root context, offline inventories, reference approval, and completeness
assertions are trusted inputs, not authenticated evidence. Unknown secrets
disguised in arbitrary unrecognized text cannot be generically detected.
C1 itself adds no by-IP enrichment or detail client. The separately authorized
C2 component below reconciles supplied data only. Live export, real-version
qualification, configuration writes, credential migration, and production
connectivity remain unimplemented.

## Implemented offline device-detail reconciliation - CCV-004-C2

[controller_reconciliation.py](../src/cc_vision_import/controller_reconciliation.py)
reuses `ControllerDevice`, `SourceObjectReference`, `ControllerExportResult`,
schema-1 controller artifacts, and the unchanged schema-2 comparison/plan APIs.
It introduces no competing device model, endpoint/client, HTTP backend, IO,
secret resolution, CLI operation, or execution path. Only `0.0-test` is enabled.

### Input, identity, and conflict contracts

`reconcile_controller_devices(artifact, details, accesses, associations)` accepts
a controller artifact, two arrays of local record envelopes
`{"record_id": "opaque-reference", "payload": {...}}`, and a tuple of
`DeviceReconciliationAssociation` records:

- `source`: explicit controller/tree/device-kind/native-ID reference.
- `detail_record`: exactly one supplied detail record per device.
- `access_record`: optional separately supplied access record.
- `acknowledgement`: optional `DeviceAccessAcknowledgement` binding the qualified
  device, normalized source snapshot hash, ordered access/input hash, policy
  version, and a protected opaque evidence reference. Missing or stale
  acknowledgement blocks planning, not structural inventory parsing.

Record envelopes and associations are **local synthetic contracts**, not vendor
response schemas or capability declarations. Detail payloads may contain the
source-observed `deviceSetup.deviceAccess` representation or the already
supported top-level `deviceAccess`; separate access payloads are bare dictionaries.
Native identifiers/type/address fields in detail responses are not established
by the legacy downloader. If supplied, locally recognized `ormID`, `id`,
`meIdentifier`, `parentOrmID`, `name`, `type`, and `managementIp` must agree
with the qualified tree object; they never choose it.

Every supplied record must be associated exactly once. Duplicate record IDs,
reused detail/access records, duplicate device associations, missing referenced
records, unknown controller/tree/device targets, and unmatched records fail.
Unmatched address references with multiple possible devices receive
`ambiguous_ip_reference`; this is diagnostic only, never a by-IP association.
Duplicate IPs/names are allowed with distinct qualified associations. Devices
are never automatically merged between Physical and Organization.

Overlapping configuration must match exactly, including nested member/array
order, JSON types, and null. There is no recursive union, conflict preference,
parent rewrite, or overwrite. Detail child objects and simultaneous top-level/
nested access are rejected. Tree, detail, and separately supplied access must
agree when multiple locations supply values. Explicit null is not absence:
only absent tree access may be filled; null is never silently replaced.
Existing non-absent tree access retains its original location/value.

### Preservation and artifact eligibility

The original tree configuration is retained. Additional detail attributes are
not projected into guessed product fields. Each associated device's existing
`configuration` gains one reserved provenance member,
`offlineDeviceReconciliation`, with local `schema_version=2`, record references,
the complete detail and separate-access payloads, original `tree_access`
location/value, source snapshot hash, versioned acknowledgement,
`scope="offline-planning-only"`, and
`completeness="unverified"`. Unknown fields and native access IDs are retained
without deletion. Input record/dictionary order is retained inside payloads;
devices keep their original inventory order regardless of record order.

The namespace is not an alternate artifact format. Existing schema-1
order-preserving controller serialization handles it; exact comparison and
schema-2 hashes include it. Consequently provenance/record changes can
conservatively cause CONFLICT or invalidate acknowledgement and a retained plan.
The explicit opt-in `validated-offline-access-acknowledgement-v1` comparison rule
excludes only the local acknowledgement and source snapshot hash from semantic
equality for devices after shared planning policy gating. It does not interpret
same-named root/site fields as device provenance: those unknown configuration
fields remain order-sensitive comparison inputs. Malformed or unacknowledged
device provenance remains BLOCKED, never eligible for this exclusion.
Its two field paths and local contract evidence
appear in the comparison policy. It never excludes access, detail, unknown
configuration, or original tree-access data. Full snapshots still bind all
metadata, and no exclusions are automatic. Without that rule, independently
bound controller-local metadata may conservatively cause CONFLICT.
Already reconciled/reserved-name input is explicitly rejected; re-reconciliation
needs separate review rather than silently replacing provenance.

C2 may inspect a C1 artifact marked invalid **only** for
`incomplete_device_access`. It first reparses the entire normalized structure,
then recomputes every device's reconciliation requirements. Other invalid
statuses cannot be cleared. Missing device associations, absent/null/empty
access, or uncertain credentials produce
an explicit invalid result with positional issues; all objects and safely
associated supplied data remain available in the protected artifact.
Standard serialization retains invalid status; `to_inventory()` and ordinary
controller parsing reject it, preventing controller planning.
Acknowledgement-only failures instead preserve a structurally valid artifact/
inventory, while the result reports policy issues. Controller comparison emits
BLOCKED for affected devices (and dependent actions), including after roundtrip.
Conflicting,
malformed, or ambiguously associated input instead raises a fixed-message
contract error without returning a partial success; caller inputs are unmodified.

Recognized raw credentials are rejected, not redacted or exported. Contract-valid
secret references and null credential placeholders are preserved but **block**
eligibility, as do recognized masks. The existing comparison uncertainty test
is shared from the controller contracts, without changing its behavior.
Ordinary noncredential null values do not automatically block. No access
completeness/credential portability claim follows from nonempty settings or an
evidence reference. Evidence labels are checked for shape, not fetched,
authenticated, or certified against vendor requirements.

The valid result still requires B's explicit independent destination mappings,
per-object semantic acknowledgements, resolved roots, confirmed MISSING and
destination completeness declarations for CREATE, and parent dependencies.
No destination ID is invented or assigned.

### Bound access acknowledgement policy

[controller_access_policy.py](../src/cc_vision_import/controller_access_policy.py)
implements `qualified-offline-device-access-v1`. The owner approved Option 1
and explicitly selected its application to **all controller devices carrying
device-access configuration**, not only C2-enriched devices. Existing direct
C1/A/B planning callers must now supply explicit acknowledgements.

Acknowledgement is a separate operator action:

1. Reconcile without acknowledgement to inspect a protected preview.
2. Explicitly call `acknowledge_device_access(source_artifact, preview_artifact,
   qualified_device, evidence_reference=...)` for each reviewed device.
3. Supply the returned acknowledgement in its association and reconcile again.
   The reconciliation code never creates acknowledgements automatically.

For direct normalized inventories without C2 metadata, pass the same artifact
as source and preview; supply the resulting tuple through the shared validator,
controller comparison, or verification `device_access_acknowledgements` parameter.
Comparison delegates acknowledgement validation and credential gating to the
shared validator rather than maintaining a comparison-only gate. The verifier
requires the retained declarations; their complete contents are digest-bound,
but evidence references and raw identities are not included in redacted plans.
Duplicate/unknown acknowledgement identities are rejected.

The source hash covers the structurally normalized source snapshot (including
controller/tree identities, all objects, metadata, and ordered configuration),
not arbitrary input whitespace or cached validation status. The access hash
covers effective access location/value plus C2's complete detail payload,
separate access, record references, and original tree-access data when present.
Changes to values, types, field/array order, missing/null distinctions, or bound
inputs invalidate prior acknowledgement. Planning rechecks these hashes,
qualified identity, and policy version; it reconstructs the original C2 source
snapshot from retained provenance to detect post-reconciliation mutation.

Evidence references must be local opaque catalogue identifiers of the exact form
`evidence-` plus 32 lowercase hexadecimal characters. Use a newly assigned local
identifier whose protected catalogue entry points to evidence; never encode or
reuse credentials, session tokens, device addresses, URLs, or configuration as
the identifier. Format checks reject freeform values and raw address/URL/token
strings; they cannot authenticate catalogue ownership or detect a secret
deliberately disguised as a permitted identifier. Callers remain responsible
for protected catalogue storage and classification. References are hidden from
default representations and operator summaries; explicit artifact access remains
protected, not a redacted report.

The policy distinguishes structural validity, offline acknowledgement, official
schema verification, and live compatibility. No acknowledgement can repair bad
identity/parents, missing required fields, incomplete access, raw/masked
credentials, or unresolved sensitive references. Nonempty access and operator
acknowledgement do not establish completeness or portability, and never
authorize import execution.

Generic schema-1 planning lacks the destination inventory, tree-completeness
declarations, and shared controller validation needed to enforce controller
safety. Checking access acknowledgement alone cannot make that path safe.
Its shared assembly boundary therefore explicitly rejects every
`controller-objects` artifact or plan whose declared source product is
`cyber-controller`, regardless of access acknowledgement or cached validation
status, with `controller_planning_required`. The same check covers creation,
parsing, verification, validation, and generic plan serialization. Validation
returns the standard invalid result; other boundaries raise a secret-safe
contract error. Even a self-consistent historical schema-1 envelope with a
correct digest cannot re-enter through parsing or verification.

Use controller-specific comparison and `verify_controller_plan` with retained
source/destination inventories and declarations instead. Those APIs provide
affected-device BLOCKED classifications and preserve incomplete diagnostic data.
Other generic domains, including synthetic Cyber Controller domains, and
Vision-labeled generic synthetic contracts remain unchanged; no Vision schema
compatibility is inferred. Product/domain declarations remain offline inputs,
not authenticated evidence about the origin of arbitrary supplied data.

Compatibility: artifact schema 1 and controller plan schema 2 remain in use.
C2 provenance schema 1 and bare evidence strings no longer establish planning
eligibility; rebuild a preview from retained original inputs and explicitly
acknowledge it. Old plans lacking the updated policy metadata/declarations are
rejected by recomputation; they must be regenerated, not treated as approvals.
The subsequent shared-boundary enforcement adds no schema, policy-version, hash,
or serialization-format change. Existing comparison callers retain their
acknowledgement parameter and behavior; direct validator callers must now pass
current declarations for devices carrying access instead of receiving valid
entries without them. The strict existing-target identity resolver is unchanged.
The acceptance-review corrections also add no schema, policy-version, hash, or
serialization-format change. Previously generated generic Cyber Controller
controller plans are now explicitly unsupported; regenerate through the
controller-specific APIs rather than treating a generic envelope as approval.
Retained controller plans that hid root/site configuration differences under the
acknowledgement rule fail recomputation and must likewise be regenerated.
These corrections establish neither live compatibility nor import authorization.

### Verification and limitations

[42 guarded reconciliation tests](../tests/test_controller_reconciliation.py)
derive synthetic details/access from the existing synthetic tree fixtures.
They demonstrate C1 export -> normalized artifact -> explicit reconciliation ->
standard serialization/parsing -> comparison -> candidate plan -> verification,
for both trees, SKIP/CONFLICT/CREATE, evidence/configuration tampering, and
external sorting against retained inputs. Missing/ambiguous/duplicate/conflicting
records, secret rejection, incomplete access, exact types/order/nulls, qualified
identities, redacted results, and non-mutation are covered.

Initial C2 verification passed 271 tests; the clarified universal policy passed
282 tests. Shared-boundary enforcement passed **286 tests** (all 282 prior cases
plus four new boundary regressions), with zero
guarded network attempts. Existing comparison/export test fixtures now
explicitly acknowledge reviewed synthetic access rather than bypassing the
gate. The new negative cases exercise direct shared validation, controller
comparison/verification, and generic planning for A/B-normalized, C1 recursive/
flat, and C2 inputs in both trees; they preserve input bytes and prove that
same-name/native-ID devices in different trees cannot share acknowledgement.
Source/destination staleness and unsafe/invalid data remain blocked/rejected.
See [E-024](PROGRESS.md#e-024---ccv-004-c2-shared-planning-boundary-enforcement-2026-11-18)
and the prior [E-023](PROGRESS.md#e-023---ccv-004-c2-bound-access-acknowledgement-policy-2026-11-18).
Python guards are test evidence, not OS-level isolation. Real detail IDs/classes,
required access fields, per-version schemas, pagination/completeness, cross-tree
device equivalence, and portable credentials remain unverified. Unknown secrets
disguised as unrecognized arbitrary text cannot be generically detected.
C2 is implemented/offline-verified, not owner-accepted; C3 and live work remain
unauthorized.

## Proposed migration modules

| Module | Operations | Dependencies and unresolved questions |
| --- | --- | --- |
| Controller objects | Export/plan/create sites and devices; explicit device update | Tree-qualified hierarchy; destination identity; both-tree device behavior. |
| Device access and credentials | Validate access settings and apply offline credential mappings | Device inventory and approved secret policy; whether exported secrets are reusable. |
| LDAP permissions | Export, validate references, compare, plan, create | Destination roles, groups, network policies, and device-lock semantics. |
| Scheduler | Export, validate task types/references, compare, plan, create | Configuration-supplied paths; task schema, activation, timezone, and dependency mappings. |

Device access can be a closely coupled submodule of controller objects rather than
a separate deployment unit. Do not build a dynamic plugin framework initially;
use an explicit registry of approved modules.

The document restore and Docker/cron utilities are excluded pending a scope
decision. They do not establish controller API capabilities.

## Artifact, identity, and secret handling

Propose a versioned JSON artifact envelope containing schema version, domain,
declared source product/version, export metadata, normalized objects, and mapping
requirements. Keep source-native fields only where needed for reviewed fidelity;
do not silently discard unsupported fields.

- Treat exported configuration as sensitive, even after removing known secrets.
- Prefer secret references resolved at import; exact storage/provider is pending.
  Do not persist new plaintext secret exports by default.
- Validate any legacy import through an explicit adapter; do not claim new
  artifacts are already compatible with legacy JSON.
- Retain source IDs only as provenance. Resolve destination IDs using validated
  mappings before writes; never substitute source IDs.
- Represent site identity with tree and hierarchy context. Duplicate names,
  collisions, missing parents, and uncertain device matches block affected writes.
- Do not silently relocate objects to root or replace unknown values.
- Protect artifact/report paths from accidental overwrite; define retention and
  access-control policy before handling real exports.

## Implemented offline contracts - CCV-002-B

These are application-owned input contracts, not Radware API schemas or product
compatibility certifications. B implemented no connection, authentication, secret
resolution, planning, or migration execution. C adds only the offline planning
contracts described below, not product matching or execution.

### Source and destination profiles

[SourceProfile and DestinationProfile](../src/cc_vision_import/profiles.py) are
separate typed contracts sharing validation. Construct validated instances through
their `from_dict(payload)` class methods.

| Field | Requirement |
| --- | --- |
| `role` | Required; `source` or `destination`, matching the selected profile contract. |
| `name` | Required; lowercase hyphen-separated identifier, beginning with a letter. |
| `product` | Required; exactly `vision` or `cyber-controller`. |
| `version` | Required string; at least two dotted numeric components, optionally followed by `-` or `+` and an alphanumeric build suffix with dot/underscore/hyphen separators. |
| `base_url` | Required supplied HTTPS origin; valid host and optional port, no user information, path other than `/`, query, fragment, whitespace, or port zero. No DNS lookup. |
| `secret_ref` | Optional, unresolved opaque reference; starts alphanumeric and contains only letters, digits, dot, underscore, slash, or hyphen. Omit if unavailable; explicit null is invalid. No provider lookup. |

Unknown profile fields are rejected, including inline credentials/tokens. No
profile hostname, credential, or secret-reference default is hardcoded in
application code. Base URLs and secret references are excluded from normal
profile representations and CLI validation reports.

Product/version syntax identifies a declaration only. For example, accepting a
synthetic version does not claim that version exists or supports any operation.
The grammar is an application convention, not a vendor-supported version range;
future legacy/version adapters must explicitly handle other formats.

See synthetic [source](../tests/fixtures/source-profile.json) and
[destination](../tests/fixtures/destination-profile.json) fixtures. Profiles are
not embedded in migration artifacts: only the source product/version declaration
belongs in the artifact envelope.

### Versioned artifact and metadata

[ConfigurationArtifact](../src/cc_vision_import/artifacts.py) is constructed through
`parse_artifact(payload)`. All six envelope fields are required:

| Field | Contract |
| --- | --- |
| `schema_version` | Integer `1`, excluding booleans. This is the application artifact schema version, not a product version. |
| `domain` | Lowercase hyphen-separated identifier, beginning with a letter; no assertion that a matching migration module exists. |
| `source` | Object with required `product` and `version`, using profile declaration syntax; no endpoint, destination profile, or credentials. |
| `metadata` | Object with required `exported_at` and `exporter`. Timestamp uses ISO-8601 date/time with `T`, seconds, optional 1-6 fractional digits, and `Z` or numeric timezone; calendar/time values are checked. Exporter is a lowercase hyphen-separated identifier. |
| `objects` | Array of JSON objects, possibly empty. Unknown configuration fields and JSON values are deep-copied and retained, subject to secret-reference rules. No domain-specific IDs or field schema are inferred. |
| `validation` | Object with required `scope`, `status`, and `issue_codes`. Scope is `offline-contract`; status is `not_validated`, `valid`, or `invalid`. Issue codes are lowercase identifiers with optional digits/underscores. Only `invalid` must carry nonempty issue codes. |

Unknown fields in the envelope, source declaration, metadata, or validation record
are explicit errors, not silently discarded extensions. Configuration-object
fields remain opaque and preserve their original names and values. Non-JSON
types, non-string dictionary keys, nonfinite numbers, and nesting beyond 64
levels are rejected. An eventual legacy adapter must construct this envelope and
report nonportable fields explicitly; no legacy format is loaded automatically.

`to_dict()` and `to_json()` revalidate before returning a copied payload or JSON,
including after nested dictionaries have been modified. The serializer neither
writes files nor exports data from a controller. The
[artifact fixture](../tests/fixtures/artifact-v1.json) demonstrates the full shape.
Use the validated factories and serializers; raw dataclass construction alone
does not perform runtime validation.

Validation metadata is an untrusted historical declaration. It does not override
current checks or prove configuration correctness, migration approval, or live
compatibility. An artifact recording earlier invalid validation can itself have
a structurally valid envelope; callers must retain that historical information.

### Secret and diagnostic boundaries

- Profiles accept references only, never raw credential fields. Artifacts never
  contain the connection profile.
- Recognizable credential-bearing configuration keys, at any nesting level, must
  contain null or exactly `{"secret_ref": "opaque-reference"}`. Null is retained;
  no import/erase/default behavior is inferred. Mixed reference/value wrappers
  and raw credential values fail explicitly rather than being redacted/dropped.
- Reserved key detection normalizes case/punctuation and checks password,
  passwd, secret, token, credential, community, cookie, authorization, privatekey,
  apikey, sessionid, and exact pwd markers. This conservative policy can block
  nonsecret fields containing those terms; resolution requires explicit review,
  not silent bypass.
- Unknown/free-text values cannot be certified secret-free by generic structural
  validation. Data producers must classify secrets and use references; future
  domain-specific schemas/review remain necessary before real exports.
- Configuration objects are excluded from artifact representations. CLI reports
  contain structural results only, not raw input, arbitrary field names, base
  URLs, references, or underlying exception text. Arbitrary object fields use
  positional diagnostic paths to avoid disclosing sensitive key names.

The existing [ValidationIssue and ValidationResult](../src/cc_vision_import/contracts.py)
shape is preserved. New parsers raise `ContractValidationError` with a structured
result on the first failure; registry validators return that result to the CLI.
Errors include stable codes, paths, and actionable fixed messages, with no silent
success-shaped fallback.

### CLI compatibility and offline verification

Existing help, inventory, and `validate --module synthetic` behavior is preserved;
inventory now additionally lists `source-profile`, `destination-profile`, and
`artifact`, each offering validation only. Exit codes remain `0` success, `1`
contract validation failure, `2` usage/unknown operation/module, `3` input/JSON error.

```powershell
$env:PYTHONPATH = Join-Path (Get-Location).Path 'src'
python -B -m cc_vision_import validate --module source-profile --input .\tests\fixtures\source-profile.json
python -B -m cc_vision_import validate --module destination-profile --input .\tests\fixtures\destination-profile.json
python -B -m cc_vision_import validate --module artifact --input .\tests\fixtures\artifact-v1.json
python -B -m unittest discover -s tests -v
```

Fixtures are synthetic; their products, versions, timestamps, and reserved
`.invalid` URLs are not operational data or evidence of product compatibility.
Tests install fail-fast socket/DNS/HTTP guards before application import and
assert zero attempted calls on every test, including invalid/error paths.
These guards verify Python entry points, not OS-level filesystem/network
isolation. Use trusted local files. Actual results are recorded in
[PROGRESS.md](PROGRESS.md).

## Implemented offline planning contracts - CCV-002-C

The [mapping contracts](../src/cc_vision_import/mappings.py),
[plan/action contracts](../src/cc_vision_import/plans.py), and
[operation result contracts](../src/cc_vision_import/operations.py) extend B.
Construct validated values through their parsing/factory functions, not raw
dataclass construction. All stages remain offline and use standard-library code.

### Qualified identity mappings

`ObjectIdentity` consists of `namespace`, `object_type`, and `object_id`.
The namespace carries explicit tree/hierarchy or other disambiguating scope;
names are not identity keys and are never assumed globally unique.

Each `IdentityMapping` requires:

- `mapping_id`, migration `domain`, and `source_index` into the exact artifact.
- Source identity and explicit source/destination product/version contexts.
- Resolution `state`: `resolved`, `missing`, `unresolved`, or `ambiguous`.
- A destination identity for `resolved` only. `missing` and `unresolved` have no
  destination; `ambiguous` requires at least two distinct qualified candidates.
- A nullable `parent_mapping` and explicit mapping-ID `depends_on` references.

Every artifact object requires exactly one mapping, including unresolved objects.
Missing records, duplicate source indices/qualified identities, mismatched
contexts, missing references, and cycles fail explicitly. Identical object IDs
in different namespaces are distinct. Multiple source objects targeting the same
qualified destination block all affected actions as `destination_collision`.
No source ID is used to fill a destination ID, and no product fields are inspected
to discover identities. The caller supplies declarations; C does not certify
their correspondence with product-native fields.

### Explicit proposals and conservative classification

`create_plan(artifact_bytes, request)` takes exact UTF-8 artifact bytes and an
explicit request. Its three required fields are `destination`, `mappings`, and
`actions`; see the synthetic [request fixture](../tests/fixtures/planning-request.json).
The destination requires a supplied `controller_id`, product, version, and HTTPS
base URL; no connection profile or credentials are copied into the plan.

Each action proposal requires `action_id`, `mapping_id`, comparison declaration
(`missing`, `identical`, `different`, `unknown`), boolean `semantics_known`, and
action-ID `depends_on` references. C does not calculate product-specific equality
or infer semantics. A `true` flag is an explicit producer assertion for a proposed
candidate, not a compatibility or live-validation result.

| Mapping/comparison declarations | Derived action |
| --- | --- |
| Destination missing, comparison missing, semantics explicitly known | `create`; change is `create-from-source`, referring to the mapped source index. |
| Resolved identity, comparison identical, semantics explicitly known | `skip`; no changes. |
| Resolved identity, comparison different, semantics explicitly known | `conflict`; report `configuration_differs`, no replacement. |
| Unknown semantics/comparison, unresolved/ambiguous identity, target collision, inconsistent declarations, or prior invalid artifact validation | `blocked`; structured reasons, no changes. |

Parent/dependency mapping actions must be explicitly present in an action's
dependencies. Actions are ordered topologically with deterministic tie-breaking.
Conflicting or blocked prerequisites block dependents. Each mapping has exactly
one proposal; duplicate or missing actions fail. There is no delete, update,
replacement, implicit root placement, or automatic field-level transformation.

The builder returns a serializable candidate even when classification finds
conflicts/blocks: its `validation.status` is `invalid`, with structural issue
paths and codes. Structurally malformed requests fail with `ContractValidationError`.

### Versioned plan and integrity boundaries

Plan schema version `1` includes:

- `stage`, fixed to `offline-candidate`, and deterministic `plan_id`.
- `source_artifact`: content-addressed `artifact_id`, exact-byte SHA-256,
  artifact schema version, product/version, object count, and declared historical
  validation status.
- Destination declaration, selected domain, qualified mappings, derived actions,
  explicit dependency graph, and recomputed structured validation results.
- `integrity_sha256`.

Canonical encoding is ASCII-escaped UTF-8 JSON with sorted keys, compact
separators, and no nonfinite numbers. Mappings/candidates/references are sorted;
actions use a deterministic dependency order. The plan ID is `plan-` plus SHA-256
of the canonical body excluding ID/integrity fields. The integrity digest covers
that body plus the plan ID. No current timestamp/randomness enters the plan.
Changing source whitespace or line endings changes the exact-byte artifact hash,
even when decoded configuration is semantically identical.

`parse_plan(payload)` recomputes classifications, dependency ordering, validation,
ID, and digest; it rejects altered/unsupported actions and mismatched contents.
`to_dict()`/`to_json()` recheck integrity, including mutable nested dependency data.
`verify_plan(payload, artifact_bytes, destination, expected_integrity)` additionally
checks the actual source bytes, supplied destination declaration, and an
independently retained expected digest. Changed inputs require a new candidate;
they cannot retain the previous integrity binding.

Checksums do not prove authorship or authorization. A party can generate a
different internally consistent plan with new hashes; the independently retained
digest is necessary to distinguish it from the previously selected plan.
Protect that digest and artifact/plan storage. Destination identity and comparison
declarations are not live-confirmed. No candidate can claim preflight, approval,
write eligibility, or migration verification.

The additive `validate --module plan --input <local-file>` CLI operation checks
internal integrity and reports blocking validation failures with exit `1`.
It does not load external source bytes or verify the independently retained
digest; consumers must call `verify_plan` for those bindings. Existing A/B
commands, JSON result shapes, and exit statuses are retained.

### Structured operation results

`parse_operation_result(payload, plan)` binds each result to an existing action,
plan ID, and plan integrity digest. Required fields are `operation_id`, `plan_id`,
`plan_integrity_sha256`, `action_id`, `state`, `issue_codes`, `verified`, and
`evidence`. Result serialization revalidates against the supplied plan.

| State | Meaning; not an execution claim by this implementation |
| --- | --- |
| `planned` | Proposed operation recorded, not performed. |
| `skipped` | Skip action recorded; no configuration change. |
| `blocked` | Prerequisite/validation prevents progress; reason required. |
| `failed` | Known processing/operation failure recorded; reason required. |
| `completed` | Completion recorded; **not automatically verified**. |
| `verification_pending` | Verification remains outstanding; no verified claim. |
| `indeterminate` | Outcome uncertain; reason required, reconciliation before retry. |

Only proposed creates may carry execution outcomes; skips require a skip action,
and blocked/conflicting actions cannot be reported completed. A separate boolean
`verified` can be true only for `completed` with nonempty matching evidence.
Each evidence record requires an opaque `reference`, SHA-256, and boolean
`matched`; false/missing matching evidence prevents verified status. There is no
standalone `verified` state that bypasses these checks.

These are hypothetical/result-record contracts only: C produces no operation
completion, contacts no destination, reads no referenced evidence, and
authenticates no evidence provenance. Shape/presence checks are not independent
proof that an asserted result occurred. Durable journaling, approval binding,
state-transition orchestration, live read-back, and recovery remain future work.

## Plan identity and integrity - future online gates

Status: **Architectural direction approved** (ADR-003 and ADR-004);
offline candidate identity/integrity implemented in C; online/preflight/approval
binding not implemented.

Each plan must have a unique plan ID, a schema version, and a SHA-256 integrity
digest over a deterministic serialization of its approval-relevant contents:

- Source artifact SHA-256 checksum over the exact input bytes, artifact schema
  version, and declared source product/version.
- Destination identity: canonical base URL, declared product/version, and a
  stable controller identifier where an evidenced capability provides one.
  A profile name alone is insufficient. If the destination cannot be identified
  unambiguously, preflight blocks apply rather than inventing a discovery API.
- Selected modules and object identities, source-to-destination mappings,
  dependency order, and unresolved mapping requirements.
- Planned actions, field-level intended changes, conflict dispositions, and
  destination-state preconditions with preflight evidence/time.
- Transformation rules, conflict policy, and secret reference/version identifiers
  where available, without embedding resolved secret values in the plan.

Offline candidate plans must identify unknown/stale destination assumptions.
Online preflight produces the destination-checked plan eligible for approval;
changes create a new plan revision/digest. Approval records must bind the plan
ID and digest, source checksum, destination identity, and explicitly permitted
actions. Modification of any bound input, mapping, change, policy, or destination
invalidates approval and requires preflight and approval again.

Before apply or resume, verify the artifact checksum, plan digest, approval
binding, and relevant destination preconditions. Changed or unverifiable inputs
block affected execution. A checksum detects content changes but does not prove
authorship: protect plans, approval records, and journals against unauthorized
modification. Approval-record storage/access control remains to be selected.
Secret references must be revalidated before use; an unversioned secret cannot
be claimed to have checksum-proven value integrity.

## Operation lifecycle

1. **Export:** authorized reads produce a validated artifact. Authentication is a
   session action, not approval for configuration writes.
2. **Offline validate/transform:** parse artifacts, check schema, apply explicit
   mappings, and report missing values without a network connection.
3. **Offline candidate planning:** derive intended actions, dependencies, and
   mapping requirements from local inputs or an explicitly identified destination
   snapshot. Make no network requests. Snapshot comparisons are provisional,
   not proof of current destination state.
4. **Online destination preflight:** under separate read authorization, confirm
   destination identity/capabilities, resolve mappings, compare current state,
   and classify conflicts. Send no configuration-changing requests. Finalize
   destination preconditions and the plan digest; unresolved ambiguity blocks
   affected actions. A dry-run that includes preflight is online and must be
   explicitly selected, never silently added to offline planning.
5. **Approve:** obtain explicit approval bound to the destination-checked plan
   and its integrity fields. Difference reports alone do not authorize updates.
6. **Apply:** validate approval/integrity and recheck relevant destination
   assumptions using authorized reads; drift requires replanning and approval.
   Journal each attempt and execute only approved operations. Stop affected
   dependency chains on failure.
7. **Verify:** read back supported destination state and compare intended
   semantics, not raw server-generated IDs or masked secrets.
8. **Report/recover:** preserve structured results and reconcile partial or
   uncertain outcomes before proposing any retry.

Site creation is parent-first within each tree. Devices follow resolved parents.
LDAP and scheduler references require explicit destination mapping or a confirmed
pre-existing dependency; do not assume all modules have a universal ordering.

## Default import conflict policy

Status: **Architectural direction approved** (ADR-009); import not implemented.

| Destination finding | Default disposition |
| --- | --- |
| Object missing, identity/dependencies resolved | Plan a create; execute only after import approval and fresh preconditions. |
| Exactly one semantically identical object | Skip as identical; record the comparison evidence. |
| Exactly one object with differences | Report field-level differences; do not modify it by default. |
| Ambiguous identity, conflicting mapping, or unverifiable equivalence | Block affected actions and dependents; require explicit resolution. |
| Destination-only object | Report if relevant; retain it unchanged. |

Never delete or overwrite existing configuration without separate, explicit
approval for the exact object/action/changes in a revised plan. The default import
approval does not grant this permission. An approved update also requires an
evidence-backed capability; this policy establishes no delete API support.
Masked or unreadable secrets cannot establish semantic identity.

## Validation and comparison

- Validate artifact shape, product/version capability, mandatory fields, object
  identities, duplicate names, hierarchy cycles, parent references, and mappings.
- Preserve LDAP authorization scope and device-lock intent. Missing destination
  role/group/policy mappings are blockers; no automatic all-scope retry.
- Validate supported scheduler fields and task types before stripping any
  server-managed fields. Review schedule activation and timezone explicitly.
- Compare normalized semantics with documented exclusions for generated fields.
  Masked secrets are not proof that credentials match.
- Enforce bounded asynchronous completion checks only through an evidenced API.
  If no completion mechanism is known, report accepted/unverified; invent no
  polling endpoint and claim no verified success.

## Failure handling and reporting

Propose per-object structured results with a correlation ID, domain, opaque object
reference, plan ID/digest, action ID, attempt ID, destination identity reference,
planned action, outcome, verification outcome, and sanitized reason.
Human-readable summaries and machine-readable JSON should derive from the same
results. Exit status must distinguish success from partial failure, blocking
validation, and execution failure; numeric codes remain to be designed.

Bounded retries may be considered for safe reads. Configuration writes are not
retried automatically. A lost response can mean a successful server write.
No transactional rollback is promised.

### Partial-import recovery

Status: **Architectural direction approved** (ADR-009); recovery not implemented.

- Persist an append-only structured result journal with durable write intent
  before each mutation and an outcome record afterward. Include timestamps,
  dependencies, sanitized response status, resolved destination ID/mapping
  references, and verification/reconciliation evidence. Protect sensitive
  identifiers; never store resolved secrets, cookies, or raw payloads.
- If intent cannot be persisted, do not send the write. If journaling fails after
  dispatch, stop further writes and surface the failure. An intent without a
  durable terminal outcome is uncertain, not proof of failure.
- Distinguish not attempted, skipped-identical, accepted/unverified, verified,
  failed, blocked, and indeterminate outcomes. Restarting must not replay all
  source objects or treat accepted operations as completed.
- Resume only from a valid plan/approval/journal binding and separately authorized
  destination reconciliation reads. Recheck previously successful objects needed
  by remaining actions; never rely solely on an old journal entry.
- For uncertain writes, inspect the evidenced destination identity, object state,
  and asynchronous status where available. If the intended result is confirmed,
  record it and do not replay. If safe non-completion is established, propose a
  retry subject to valid approval and fresh preconditions. A temporarily absent
  object alone is not proof that an asynchronous write failed.
- If state differs or remains ambiguous, block retry and request operator
  resolution. Changed mappings/actions/preconditions require a revised plan and
  renewed approval. Recovery never grants deletion, overwrite, or automatic
  compensating-write authority.

## Verification strategy and approval gates

- Foundation tests must be offline and deny accidental network access.
- Use synthetic fixtures for schemas, mapping conflicts, malformed responses,
  TLS/timeout configuration, session cleanup, error redaction, and partial failure.
- Mock tests establish local behavior, not API compatibility.
- Require approved official references and/or separately authorized lab evidence
  per product/version before enabling live writes.
- Require post-import evidence before marking a migration verified complete.
- Live integration and production acceptance require separate authorization.

CCV-001 was static only. CCV-002-A/B/C and CCV-003-A/B/C verification cover offline
local behavior, not APIs or product compatibility. CCV-003's implemented mock-only
scope and CCV-004-A/B's offline-only scopes are owner-accepted. Separately
authorized CCV-004-C1 export adapters are implemented and offline-verified;
their next gate is technical review and owner acceptance. Do not begin C2,
real HTTP backend development, or live operations without separate authorization.

# Master Application Architecture

Date: 2026-11-17  
Status: **Architectural direction approved on 2026-11-17**. CCV-002-A/B/C offline
foundation and contracts implemented; CCV-003-A/B transport and authentication
mock-tested; CCV-003-C adds synthetic-version read clients and a mocked
read-to-plan workflow. No concrete HTTP backend, production secret resolver,
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
CCV-004 and all live/backend development require separate authorization.

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
local behavior, not APIs or product compatibility. The next gate is owner review
of CCV-003-C's narrow mock-only read-to-plan scope, followed by separate
authorization and evidence for a bounded follow-on task. Do not begin CCV-004,
real HTTP backend development, or live operations.

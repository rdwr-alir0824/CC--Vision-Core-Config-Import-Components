# CCV-010-C - Architecture A: Static IP Bindings and Nonblocking TLS

Date: 2026-11-20  
Status: **REVISED DEADLINE-CONTAINMENT POLICY APPROVED — DESIGN NOT IMPLEMENTED — NOT APPROVED FOR EXECUTION**  
Evidence: [E-047](PROGRESS.md#e-047---ccv-010-c-revised-deadline-containment-policy-2026-11-20);
[E-046 revised design](PROGRESS.md#e-046---ccv-010-c-design-revision-and-supervised-containment-2026-11-20);
[historical E-045](PROGRESS.md#e-045---ccv-010-c-architecture-a-offline-design-2026-11-19)  
Recommendation: **CONTINUE FAIL-CLOSED; IMPLEMENTATION NOT AUTHORIZED.**
The owner approved qualified, deadline-accounted, fail-closed containment policy
direction on 2026-11-20. Unconditional whole-operation hard interruption/release
by deadline is no longer C's acceptance requirement and is not claimed.

## 1. Authority, baseline and evidence

This is a revised proposal requiring independent review, not an implementation, runtime
qualification, approval of laboratory values, compensating-control acceptance,
or owner acceptance. No real hostname, IP address, account or credential is
supplied. The feature branch name `feature/ccv-010c-http-safety` is user-supplied.
The revision corrects the review's MEDIUM deadline-ownership and LOW successful-
cleanup findings and evaluates complete-operation process containment.
The [owner's dated policy decision](DECISIONS.md#owner-policy-decision---ccv-010-c-deadline-containment-2026-11-20)
now controls acceptance-policy direction. It replaces only the unconditional
hard-interruption requirement, not the design/integration/qualification
prerequisites. E-043 through E-046 and their former requirement assessments remain
historical. The independent E-046 review in the project conversation recommended
ACCEPT REVISED DESIGN WITH EXPLICIT LIMITATIONS; that review was not implementation
or laboratory authorization, and this policy decision does not supply either.

The approved policy requires one immutable monotonic operation deadline; deadline
and authorization-generation checks at authorization, dispatch, validation and
commitment; no success for expired/stale operations; no new dispatch after observed
expiry or authorization revocation; no late-result commitment of authentication,
cookies, configuration or successful results; termination escalation on worker
deadline excess; explicit exit/reaping/resource-disposition evidence; quarantine
on unconfirmed termination/disposition and no replacement while restrictions
remain unresolved; no automatic authentication/configuration-write replay;
measured startup/termination/cleanup/reporting overruns on approved builds; and
explicit remaining timing/scheduling/resource uncertainty.

No unconditional hard-real-time termination, report delivery or complete resource
release by deadline is promised. Policy direction is approved, not implementation,
runtime compatibility, laboratory execution or full milestone acceptance.
Production capabilities remain default-deny; concrete laboratory dispatch remains
disabled. No product authentication, laboratory connections or configuration
import/update/deletion are authorized. Gates A-D remain NOT PASSED; full CCV-010-C
milestone acceptance remains withheld.

[E-043](PROGRESS.md#e-043---ccv-010-c-offline-http-safety-hardening-2026-11-19)
and [E-044](PROGRESS.md#e-044---ccv-010-c-review-and-authorized-corrections-2026-11-19)
remain the implementation evidence: **425 passing offline tests**, including
the chunk-data CRLF and initial-deadline timeout corrections. That count is
historical, not a test run for this design. No confirmed unresolved defect in
the corrected offline safeguards is asserted here. DNS guarantees, hard
whole-operation interruption, blocking I/O/TLS/parsing/cleanup qualification and
real authentication remain unresolved. Built-in HTTPS dispatch stays denied
before DNS. The trusted offline-double seam is not a live escape hatch.

The [architecture overlay](ARCHITECTURE.md#ccv-010-c-safety-overlay---2026-11-19)
controls over earlier backend descriptions. The [laboratory plan](LAB_QUALIFICATION_PLAN.md)
is an accepted historical planning artifact, not execution authority. Its
Gates A-D remain **NOT PASSED**. Its proposed numeric limits are unapproved and
are not installed as defaults by this design. The [decisions](DECISIONS.md)
and [roadmap](ROADMAP.md) retain separate authorization, implementation,
verification, compatibility and acceptance boundaries under ADR-002/004/006/007.

### 1.1 Inspected contracts and consequences

| Source inspected | Verified source fact / design consequence |
| --- | --- |
| [http_backend.py](../src/cc_vision_import/http_backend.py) | Exact `DestinationAuthorization`; private strict cookie jar; positive body budget; mandatory deadline; no built-in dispatch; one origin per instance; `Connection: close`; confirmed status retained through failure; explicit pending cleanup. Preserve these policies, not the blocking connection/file implementation. |
| [transport.py](../src/cc_vision_import/transport.py) | `BackendRequest`, `HttpResponse`, `BackendFailure`, error precedence and one `OperationDeadline` across eligible GET retries; context setup and JSON validation are synchronous. Keep public shapes and conservative write uncertainty. |
| [sessions.py](../src/cc_vision_import/sessions.py) | Independent role owners, nominal mock restriction, 401 expiry/403 non-expiry, retained cleanup failures, no remote logout. A transport is never a `MockSessionBackend`. |
| [authentication.py](../src/cc_vision_import/authentication.py) | Vision JSON application-status strategy; CC Basic-plus-JSON and HTTP-200-only evidence; `compatibility_verified=False`; no automatic renewal. Preserve mock contracts without treating them as laboratory authentication qualification. |
| [contracts.py](../src/cc_vision_import/contracts.py), [_contract_validation.py](../src/cc_vision_import/_contract_validation.py) | HTTPS-only profile/origin validation, typed products, sanitized contract errors. Existing hostname validation is not static-address authorization; A adds a narrower binding validator without changing generic profiles. |
| [capabilities.py](../src/cc_vision_import/capabilities.py), [mock_capabilities.py](../src/cc_vision_import/mock_capabilities.py) | Empty production catalogue; exact synthetic-only declarations. Address permission, operation permission and product capability evidence are independent requirements. |
| [test_http_backend.py](../tests/test_http_backend.py), [test_transport.py](../tests/test_transport.py), [test_authentication.py](../tests/test_authentication.py), [offline_support.py](../tests/offline_support.py) | Existing wire-in-memory parsing, status priority, cookie atomicity/isolation, expiry, retry and sanitation regressions must remain. Extend their guards/doubles only if later authorized. |

No application module, test, vendor PDF, configuration or other milestone is
changed by this task. No network, DNS, installation or live authentication
operation was performed. E-046 preserves the prior design revision's read-only
Git status/branch procedural deviation. No Git operation was performed for this
policy update; the historical record is not rewritten or treated as runtime evidence.

## 2. Architecture and invariants

Proposed path:

`role session -> HttpTransport -> static-bound backend -> raw nonblocking TCP
socket -> SSLObject + MemoryBIO pump -> incremental HTTP/1 parser`

Choose `SSLContext.wrap_bio` / `SSLObject`, not an `HTTPSConnection` subclass or
buffered socket file. Explicit encrypted-byte pumping makes all network reads
and writes visible to the readiness/deadline mechanism. Memory BIO TLS operations
do not themselves wait for network readiness, but synchronous SSL computation
and allocation remain outside any hard in-process interruption guarantee.

One backend belongs to one role/session generation, one immutable binding and
one approved origin. Each attempt gets a fresh socket, TLS object and pair of
BIOs; HTTP connections are never pooled. The private cookie jar persists only
within that owner/binding. No concurrent calls, cross-role TLS state, proxy,
ambient authentication, discovery, DNS, redirect, automatic reconnect or
credential-refresh behavior is allowed.

Core invariants, checked before each externally visible transition:

1. Explicit address authorization AND existing exact method/target
   authorization AND the applicable product/role policy must all hold.
2. The HTTPS hostname never becomes the numeric TCP destination in URL, SNI,
   certificate identity, cookie origin or HTTP Host.
3. Only a validated family-specific numeric sockaddr reaches `connect_ex`.
4. A verified connected peer must equal the **selected** authorized address and
   port, not merely some other member of the approved set.
5. Every attempt/phase uses the same absolute expiry and clock domain.
6. No HTTP plaintext enters TLS before successful verified handshake and peer
   check; no credentials go to another address after uncertain dispatch.
7. A response is not successful until framing, size, cookies, release and
   caller-side required validation pass before expiry.
8. Uncertain ownership/cleanup disables further dispatch; errors expose only
   safe categories, confirmed status, attempt counts and disposition flags.

An approved egress firewall is still a separate laboratory prerequisite.
`getpeername` proves the socket's reported remote endpoint, not the identity of
equipment behind NAT, a load balancer or routing infrastructure. TLS identity
and independent target evidence address different threats.

## 3. Static destination binding

### 3.1 Proposed immutable representation

Add a future frozen binding contract alongside, not in place of,
`DestinationAuthorization`. Names below are design names, not existing symbols.

| Field | Required meaning |
| --- | --- |
| `binding_version` | Exact supported schema version; unknown versions rejected. |
| `approval_ref`, `revision` | Opaque protected authorization reference and immutable revision; neither a self-issued permission nor proof of authenticity. |
| `role`, `session_generation` | Explicit owner; generation prevents stale authenticated state being attached to a replacement binding. |
| `hostname` | Independently approved canonical ASCII DNS identity, without scheme, port, brackets, slash or trailing dot. |
| `port` | Explicit integer, excluding bool, in 1..65535; HTTPS origin's effective port must equal it. No coercion from strings, service names or floats. |
| `addresses` | Nonempty, duplicate-free, finite ordered tuple of explicit IPv4/IPv6 entries. Each entry contains family and canonical numeric address/packed bytes; port comes only from the binding. |
| `address_policy` | Fixed approved order, finite maximum address count, and per-address connect cap. No ambient address sorting or automatic racing. |
| `scope_ref` | Reference to the exact existing origin/method/target authorization and separate product/build/role/procedure scope. |
| `trust_ref`, `policy_revision` | Approved TLS trust/identity policy and complete numeric-resource/deadline policy revision. |
| `validity` | Explicit approval validity/revocation authority; wall-clock approval validity is separate from monotonic elapsed-operation accounting. |

Restricted approval records contain actual values; this repository document does
not. Future loading must authenticate provenance/access and check freshness,
not trust an arbitrary caller-created dataclass or digest. A digest detects
changes, not authorization. No file loader, CLI option or approval service is
implemented here.

### 3.2 Validation and canonicalization

- Reuse `_origin`, `_target` and `DestinationAuthorization.permits` for existing
  HTTPS and exact operation rules. A's extra validator requires a DNS-name
  origin; generic existing IP-origin/mock behavior remains unchanged.
- Require ASCII labels with letters/digits/hyphens, 1..63 characters per label,
  no leading/trailing hyphen, total presentation length <=253. Reject Unicode,
  whitespace, controls, empty labels, trailing dot, percent escapes, wildcard,
  userinfo and URL delimiters. Lowercase hostname case is the sole identity
  normalization. IDNA A-label identities require independent approval; there
  is no runtime Unicode-to-IDNA discovery or correction. Reject IP literals and
  numeric-only/legacy numeric host spellings as hostname identities.
- Require already canonical IPv4 dotted decimal or canonical compressed IPv6;
  use `ipaddress` parsing/packed comparison, never a resolver to validate.
  Reject octal/hex/shortened IPv4, IPv4 leading zeros, bracketed address-field
  values, URLs, ports embedded in addresses, CIDRs, ranges and wildcards.
- Family must match parsed version. IPv6 entry maps to
  `(numeric_address, port, 0, 0)`; IPv4 to `(numeric_address, port)`.
  Initial A excludes scoped/link-local IPv6 and `%zone` syntax rather than
  invoking interface-name lookup. Reject IPv4-mapped IPv6, unspecified,
  multicast and broadcast destinations; loopback is excluded from the initial
  laboratory destination policy. Private/global unicast is never implicitly
  authorized by address class.
- Duplicate detection uses family/packed-address identity, not textual equality.
  Count and serialized-length caps precede expensive parsing. Reject conflicting
  origin/hostname/port/role/revision combinations before socket creation.
- The canonical HTTP authority is lowercase hostname, with `:port` only for
  nondefault 443; explicit/implicit 443 remains same-origin equivalent.
  SNI and certificate name receive hostname only, never `hostname:port`.

### 3.3 Multiple addresses, changes and peer checks

Use approved order, sequential TCP candidates, one open candidate socket at a
time. No Happy Eyeballs threads or concurrent background connections. Each
candidate gets at most the approved per-address cap AND the remaining shared
connect/operation budget. All addresses may be exhausted without ever sending
HTTP. An address cap is not a renewed operation timeout. The initial lab policy
may deliberately permit only one candidate; a multi-address procedure needs
explicit approval of order, caps and attempts.

Only pre-TLS ordinary TCP refusal/unreachability or candidate connect-cap expiry
may move to the next approved address after verified local disposition. An
operation expiry ends all candidates. Peer mismatch, TLS failure, policy
failure, malformed HTTP or cleanup uncertainty stops the whole operation.
Once TLS begins, the backend does not select another address internally.
Whole-attempt GET retries belong exclusively to `HttpTransport`; section 8
preserves that generic contract and requires zero retries for the lab slice.

After successful `SO_ERROR` verification, call `getpeername`, validate tuple
shape, family, numeric packed address, port and IPv6 scope. Reject unexpected
family/mapped form, selected-address mismatch, changed port, failed query or
unqualified scope. Recheck before HTTP transmission; no TLS/socket substitution
is permitted between checks. If peer verification cannot complete, no credentials
are sent. Map a valid-but-unauthorized peer to `safety_policy_rejection`; a
socket-query failure to connection failure, with no address fallback.

Changing hostname, port, any address, address order, role, trust policy,
operation scope or bound procedure revision invalidates prior authorization.
It requires a new protected approval and fresh session/backend; no cookies or
TLS state carry across. Revocation invalidates the active generation, stops new
work and triggers local disposition without implicit logout. Approval changes
cannot mutate an in-flight snapshot; a revocation check before dispatch must
still fail it. Emergency revocation cannot preempt a stuck synchronous call.

### 3.4 No-DNS and no-bypass boundary

Do not call `getaddrinfo`, `gethostby*`, `create_connection`, HTTP connection
helpers, proxy discovery, service-name lookup, reverse DNS, hosts-file lookup or
resolver workers. Numeric sockaddr recognition in CPython's socket wrapper must
be audited for the exact runtime; a numeric string alone is not evidence that
all internal name-resolution paths are absent. Only prevalidated canonical
family-specific values enter it. If that path cannot be proven resolution-free
on the target build, keep dispatch disabled; do not add fallback resolution.

`server_hostname` in `wrap_bio` is a TLS identity input, not a TCP locator.
No CA/AIA/OCSP download, online revocation provider or externally connecting
trust callback is allowed. Trust is local and preapproved; local revocation
policy and stale trust remain separate unresolved security decisions.

All 3xx responses are terminal transport rejections under existing status
handling, including same-origin Location and 303. Never follow or rewrite
method/Host or forward credentials. A 202 remains a transport 2xx, not operation
completion; the lab workflow must stop without async polling. Neither product
versions, capabilities, mock markers nor a previously successful connection
can authorize an address or bypass method/target checks.

## 4. Interfaces, limits and integration seams

Preserve `send(BackendRequest) -> HttpResponse` and `close()` with sanitized
`BackendFailure` reporting. A future backend requires explicit binding,
`DestinationAuthorization`, body budget, complete bounded resource policy and
`OperationDeadline`; missing inputs fail before creating sockets. It remains
explicitly injected and non-mock. The existing blocked backend is not silently
replaced or enabled.

Use small injectable socket, readiness, TLS/BIO and clock adapters for synthetic
tests. Production adapters, if later authorized, are fixed trusted code, not
runtime plugins or user-supplied factories. A readiness abstraction may expose
read/write/error interests; it must preserve Windows connect error readiness.
Ownership state and parser state are operation-local.

Mandatory finite policy inputs, no unlimited/omitted defaults:

- Request plaintext body bytes, total serialized request bytes, header bytes,
  per-line bytes and count, including automatically added cookies/Host/framing.
- Response status/header block bytes, line bytes and count; body bytes remain
  the existing explicit `max_response_bytes`.
- Chunk-size line bytes, chunk count and cumulative framing/trailer bytes.
- Encrypted receive/send step bytes, BIO occupancy, TLS step/plaintext write
  bytes, plaintext parser buffer and cumulative encrypted operation bytes.
- Cookie-jar retained count and name/value/attribute bytes across responses,
  candidate-copy budget and session lifetime/request count.
- Address count, connection phase/candidate caps, I/O phase caps, operation
  timeout and cleanup reserve.

Validate policy sizes against a reviewed finite implementation maximum; do not
accept arbitrarily huge Python integers as practical resource bounds. Limits
must compose: allocation peaks include input/output BIOs, parser buffers,
payload accumulator plus final bytes copy, request serialization and old plus
candidate cookie jars. Cap buffered plaintext, not just the returned entity.
A TLS call can allocate internally before a post-call occupancy check; these
caps are application-observed limits, not hard bounds on OpenSSL/process memory.
Cumulative wire/TLS caps are additional proposed restrictions, not a claim that
E-044's entity cap already limits packet traffic.

These additional limits and narrower protocol choices are A-only proposed
lab restrictions requiring review; they must not silently alter existing
generic/mock APIs or accepted tests. Reuse the strict cookie policy and existing
validators; extract only a necessary shared policy helper during later approved
implementation rather than copying divergent logic.

## 5. Nonblocking TCP state machine

Every state entry, retry and return checks `deadline.remaining()`. Work states
also check the active-work cutoff defined in section 8. No socket timeout mode
is used to emulate nonblocking I/O: set `setblocking(False)` before connect,
then keep it for the entire lifetime.

| State | Action / transition |
| --- | --- |
| VALIDATE | Validate envelope, binding, approval, scope, TLS policy and all limits. Expired initial deadline preserves TIMEOUT, never BACKEND. On rejection -> DISPOSE (possibly no resources). |
| CREATE | Create exactly `socket(family, SOCK_STREAM, IPPROTO_TCP)`; record sole ownership immediately; set nonblocking. No default family, connect helper or proxy. -> CONNECT_START. |
| CONNECT_START | `connect_ex(numeric_sockaddr)`. Zero -> CONNECT_CHECK. Reviewed pending result -> CONNECT_WAIT. Other result -> candidate connection failure and DISPOSE. |
| CONNECT_WAIT | Wait for write OR exceptional readiness with finite remaining phase/candidate/operation budget. Readiness is a hint, not success. Empty/spurious results -> recompute budget and wait; expiry -> DISPOSE. |
| CONNECT_CHECK | Query `getsockopt(SOL_SOCKET, SO_ERROR)`; zero plus valid `getpeername` -> PEER_VERIFIED. Nonzero terminal error -> DISPOSE. A qualified still-pending result -> CONNECT_WAIT, never assumed connected. |
| PEER_VERIFIED | Exact selected binding match required. Freeze selected endpoint into attempt state. -> TLS_CREATE. |
| DISPOSE | Unregister readiness, close candidate, retain uncertain failures. Only confirmed release plus eligible pre-TLS failure and remaining budget permits next CREATE; otherwise return failure/quarantine. |

On Windows propose `select.select(read_sockets, write_sockets,
exception_sockets, timeout)` behind the readiness interface. Pending connects
must be observed in writable **and exceptional** sets, then verified with
`SO_ERROR`; writable-only logic is insufficient. It operates on sockets, not
files/process pipes. A selectors-based implementation is acceptable only after
auditing its Windows error-event mapping and giving the same tests; epoll/kqueue
or Unix descriptor assumptions are not portable substitutes.

Create a reviewed named-result table for CPython 3.13.14/WinSock:
`WSAEWOULDBLOCK`, `WSAEINPROGRESS`, `WSAEALREADY` and POSIX equivalents where
actually returned are pending; zero is immediate completion. Do not transplant
Linux integer errno literals. Treat `EISCONN`/`WSAEISCONN`, if encountered, as
requiring completion/peer verification, not blind success. Audit `connect_ex`
return codes versus raised exceptions on this exact build.

`InterruptedError`/interruption with no terminal cancellation means recompute
all absolute budgets and resume the same state, not reconnect. CPython may
internally retry interrupted system calls; its actual timeout recalculation
needs inspection/qualification. Explicit cancellation/KeyboardInterrupt is not
swallowed: dispose and propagate according to caller policy, never retry.
Repeated ready/pending cycles check the deadline and use bounded state steps;
no busy loop can renew it.

Refusal/reset/unreachable/resource-related OS errors -> CONNECTION; readiness
or phase/operation expiry -> TIMEOUT; unexpected adapter/clock/type failures ->
BACKEND; unauthorized binding/peer -> SAFETY_POLICY. Disposition uncertainty
adds `cleanup_failed` and disables retry. No raw address or OS exception text
is included in reports.

## 6. Nonblocking TLS state machine and byte pump

### 6.1 Identity and context requirements

Use a role/session-owned, audited `SSLContext` with `CERT_REQUIRED`,
`check_hostname=True` and `keylog_filename is None`. Preserve the verified
client context policy, approved local trust and modern protocol floor; no
`CERT_NONE`, check disabling, hostname substitution, insecure cipher/version
retry, TOFU or certificate-error fallback. Reject `SSLKEYLOGFILE` before invoking
a context factory that could open a key-log file; checking the context only
after creation is too late to prevent that side effect. Do not mutate global
environment to conceal it. No wire/debug/key logs.

Use the original approved hostname as `wrap_bio(..., server_side=False,
server_hostname=hostname)`; do not supply a `session`. OpenSSL verifies the
certificate chain and hostname during handshake. TCP's numeric address is
independent of that identity: no IP SAN is substituted for the approved DNS
hostname. Set the A-only policy to SAN-based name verification
(`hostname_checks_common_name=False`), subject to exact OpenSSL qualification;
failure to support the policy blocks A rather than enabling CN fallback.
Do not invent additional wildcard/certificate pin semantics: expected identity,
SAN/wildcard policy and certificate-change approval must be explicitly reviewed.

Limit ALPN to approved HTTP/1.1 behavior. Reject any negotiated alternative.
No HTTP/2 parser, TLS early data, cross-origin/role resumption or imported
`SSLSession`. Use a fresh TLS object per connection; audit context ticket/cache
behavior on the target SSL build and disable applicable resumption mechanisms
where supported. If implicit reuse cannot be excluded, create fresh contexts
per attempt within the operation budget or keep A disabled. Context construction
is still synchronous; preconstruction cannot prove bounded initialization.

### 6.2 TLS transitions

| State | Action / next state |
| --- | --- |
| TLS_CREATE | Create incoming/outgoing `MemoryBIO` and `SSLObject` with audited context/hostname. Account for creation time; verify raw peer remains bound. -> HANDSHAKE_STEP. |
| HANDSHAKE_STEP | Call `do_handshake()` once. Success -> FLUSH_HANDSHAKE then TLS_READY. `SSLWantReadError`/`SSLWantWriteError` -> PUMP with handshake continuation. Verification/protocol failure -> DISPOSE, TLS failure. |
| PUMP | Drain generated ciphertext to a bounded pending-send buffer; perform partial raw nonblocking sends. Feed bounded raw receives to incoming BIO only as needed. Wait for the actual unsatisfied raw read/write interests with remaining budget. -> saved TLS continuation. |
| TLS_READY | Recheck verify/key-log/ALPN/peer policy. Do not send HTTP until handshake succeeds and pending handshake output is flushed. -> REQUEST_WRITE. |
| TLS_WRITE / TLS_READ | One bounded SSL plaintext operation; handle partial results and either WANT condition through PUMP. Never assume a read only needs readability or a write only needs writability. |
| TLS_EOF / TLS_ERROR | Distinguish authenticated close_notify from abrupt TCP EOF and protocol errors. Feed `write_eof()` once on raw EOF; do not spin or treat truncation as success. -> HTTP completion check or DISPOSE. |

Pump rules:

1. Attempt bounded in-memory TLS work before waiting for raw readability:
   SSL may already have buffered plaintext. `SSLObject.pending()` can inform
   this, but zero does not prove that no protocol processing remains.
2. Drain outgoing BIO after **every** TLS step, including exceptions.
   `SSLWantReadError` may have generated outbound handshake traffic. Flush it
   before waiting for inbound data to prevent deadlock.
3. With pending ciphertext, request raw write readiness; retain the exact
   unsent bytes/offset after partial send or `BlockingIOError`. No loss,
   duplication or unbounded draining into a growing queue.
4. When more encrypted input is necessary, request read readiness. If both
   output and input are required, wait on both and service each in bounded
   steps, checking expiry between them. Do not translate BIO WANT_WRITE
   mechanically into an unconditional network-write wait: inspect/drain output.
   WANT_WRITE with no actionable pump progress is an explicit bounded
   failure/qualification case, not a forever loop.
5. Each receive/feed step and BIO/plaintext occupancy is capped. No read of
   unbounded size, no accumulating unlimited TLS records while HTTP stalls.
   Repeated protocol-only records are bounded by cumulative encrypted-byte
   limits and the deadline.
6. A successful TLS write consumes only its returned plaintext byte count.
   On WANT conditions retain the original pending plaintext segment until
   the API reports consumption; serialize calls so it cannot be replaced by
   unrelated data. Flush generated ciphertext before reporting request sent.
7. Deadline checks surround each SSL/BIO call. They reject late results but
   cannot interrupt a native call that fails to return.

`SSLCertVerificationError` and other `SSLError` failures use the existing TLS
category (whose historical name is `tls_certificate_failure`, even for other
TLS errors); WANT exceptions are control flow, not reported TLS failures.
Raw network errors use CONNECTION; timeouts use TIMEOUT. TLS failure stops
address fallback and retries. No partial TLS object survives for reuse.

Forbidden network helpers: `HTTPSConnection.connect/request/getresponse`,
`socket.create_connection`, `makefile`, buffered `read/readline`, `sendall`,
`SSLSocket` auto-handshake, and `unwrap` in cleanup. `wrap_socket` with default
handshake can block; setting nonblocking later does not repair it. Even
`wrap_socket(..., do_handshake_on_connect=False)` has synchronous setup and
ownership behavior needing audit, so it is not the selected mechanism.
`create_default_context`, certificate-store/CA loading, `wrap_bio`,
`do_handshake`, SSL read/write, BIO operations and object destruction still
perform synchronous filesystem/native/CPU work; nonblocking network semantics
do not supply a hard duration bound for those calls.

## 7. HTTP request, parser and response safeguards

Implement a small incremental HTTP/1 parser over bounded plaintext, not
`HTTPResponse` private helpers or `email`'s forgiving wire parser. Keep the
existing `_headers`, framing policy and strict cookies as policy prior art.
The parser must reject malformed data even if the payload is small.

### 7.1 Request transmission

Build exact origin-form target using existing canonical URL/operation rules.
No arbitrary full URL, Host override, Content-Length override, transfer coding,
proxy headers, CONNECT, upgrade or caller-owned Connection header. Serialize
one HTTP/1.1 request with transport-owned Host and `Connection: close`.
Use explicit exact body length, no chunked request, no automatic Expect/100
handshake. GET bodies remain disallowed. Validate all resulting headers,
including cookie-generated headers, before transmission; count the complete
serialized plaintext request and reject overflow before the first send.

Use bounded memoryview segments/offsets with SSL write and raw send partial
counts; both layers must finish without duplicating bytes. A raw zero-byte send
for nonempty output is a connection failure, not progress. EWOULDBLOCK/WANT
uses readiness; no `sendall`. Do not expose secrets in buffers' repr/logs.
Track whether any request bytes may have reached the peer for diagnostics,
but retain existing conservative indeterminate-write categorization even for
some pre-dispatch failures. No automatic POST/login/logout/write replay.

### 7.2 Header parsing

States: STATUS_LINE -> HEADER_LINE* -> HEADER_END -> FRAMING -> BODY ->
COMPLETE. Retain only bounded partial lines; require exact CRLF, not bare LF.
Count status line, every field line and terminal CRLF in total-header bytes.
Enforce per-line, total bytes and field count as bytes arrive, before appending
beyond the allowance. No unlimited scan awaiting a terminator.

Require supported HTTP/1.0 or HTTP/1.1 status-line syntax and a three-digit
final code 200..599; no informational/101 upgrade path in initial A. Treat
unrequested 1xx as explicit A-policy rejection, not an endless interim loop.
No invented final status when status-line parsing is incomplete.

Require token field names, colon immediately after name, printable ASCII field
values with existing conservative control rejection. Permit only documented
optional SP surrounding the value; reject tabs/obs-fold, leading continuation,
colonless lines, whitespace before colon, NUL, non-ASCII and malformed pairs.
Detect duplicates case-insensitively and reject all except separate
`Set-Cookie` lines. Do not coalesce duplicates, even equal Content-Length.
Keep individual cookies private; never flatten or expose them in public headers.

Record a syntactically valid supported final status as soon as it is confirmed;
later malformed headers/body, timeout or cleanup does not erase a known
non-success status. 401 immediately invalidates only that role's cookie jar.
It cannot later commit cookies from the same response. Confirming status does
not imply that the rest of the response is valid.

### 7.3 Framing decision

| Case | Required disposition |
| --- | --- |
| Content-Length present | One field of nonempty decimal digits only; reject sign, commas, duplicates, whitespace inside, unreasonable digit count and overflow. Compare bounded decimal value to body cap before reading body. |
| Transfer-Encoding present | HTTP/1.1 only: exactly one `chunked` coding, case-insensitive; reject other codings/lists/duplicates and any TE on HTTP/1.0. Any Content-Length plus TE is malformed. |
| Content-Encoding present | Exactly `identity`, case-insensitive, or absent. Reject gzip/br/deflate/lists; no decompression or success after truncation. |
| Neither length nor TE | Close-delimited body, subject to byte/deadline limits and authenticated TLS EOF policy below. |
| 204 or 304 | No entity body. Apply status-specific header constraints; reject TE and forbidden 204 length. A 304 length, if supplied, is representation metadata, not bytes to read. Never reinterpret tail bytes as a body. 304 remains non-success to transport. |
| 205 | No content permitted. Initial A accepts explicit Content-Length: 0 only, rejects TE, nonzero length and buffered payload; other legal zero-content framing is an explicit unsupported lab-policy case, not a permissive EOF fallback. |
| Protocol upgrade/tunnel | Reject; no alternate parser or connection handoff. |

Header and length validity is checked even for error responses. Preserve known
status priority while reporting the secondary malformed/safety reason.

### 7.4 Fixed, chunked and close-delimited bodies

- Fixed length: read exactly the declared entity length incrementally. EOF
  before it is malformed. Never return over-limit data or silently accept a
  truncated body. Unexpected plaintext already buffered beyond the entity is
  rejected under A's single-message policy. Unobserved trailing wire bytes
  are discarded on close, never reused; detecting every falsely short length
  would require waiting for EOF and is not claimed.
- Incremental cap: request at most the lesser of the reviewed step ceiling
  (preserve the existing 65,536-byte maximum plaintext body step) and remaining
  entity allowance plus one detection byte. Fixed framing never reads beyond
  its remaining entity. Accumulate/count entity bytes independently of
  misleading metadata; exact-limit binary payload is unchanged. At limit in
  chunked/EOF modes, parse framing or use the single detection byte, never a
  zero-size read mistaken for completion.
- Chunked states: SIZE_LINE -> DATA(n) -> DATA_CRLF -> SIZE_LINE, then
  ZERO_CHUNK -> TRAILER_END -> COMPLETE. Require a nonempty hexadecimal size
  token, bounded token/line length and safe size comparison before conversion/
  allocation. Reject sign, nonhex, bare LF, overflow and premature EOF.
  Verify the **exact two bytes CRLF after every nonzero chunk**, including
  when data spans several TLS reads and when the body exactly reaches its cap.
  This preserves E-044's correction without its private stdlib dependency.
- Initial A's narrow lab protocol policy rejects chunk extensions and nonempty
  trailers, including Set-Cookie trailers. Require `0\r\n\r\n` completion;
  enforce chunk count/framing bytes so many zero-payload metadata bytes cannot
  evade resource limits. This deliberate restriction needs independent review;
  it is not an assertion that all such legal HTTP is malformed or that E-044
  exhaustively validates trailers. Supporting them later requires a separately
  bounded grammar and forbidden-trailer policy, not stdlib discard behavior.
- Close-delimited response: complete only on verified TLS close_notify.
  Abrupt TCP EOF/`SSLEOFError` cannot authenticate completeness and must fail.
  For fixed/chunked framing, a completely validated entity may complete before
  close_notify; subsequent local abortive close is not peer-data truncation.
  Unexpected EOF before that framing completion is never success.

Require bounded strict JSON with existing duplicate-member/nonfinite-number
rejection where requested. Byte bounds do not preempt synchronous JSON or
application validation. The operation coordinator owns and propagates the same
deadline across transport return and caller validation (section 8.1); transport
return is only candidate receipt, not permission to commit. A supervisor is
needed to interrupt a stuck parser.
Transport 200/202 or valid JSON never establishes qualified authentication,
schema completeness or operation success.

### 7.5 Completion, cookies and connection policy

Response data remains an uncommitted candidate through caller validation and
successful resource release. Prepare Set-Cookie updates only for successful 2xx as
today, by cloning the owner jar and using the strict existing domain/path/
expiry and Max-Age policy. No permissive warn-and-drop parsing fallback.
Retained cookie count/byte overflow is an explicit A safety rejection, not
eviction that silently changes authentication. If candidate parsing fails,
discard the entire candidate and preserve prior cookies (except confirmed
401's intentional clear). Unknown parser faults become sanitized BACKEND.

The backend returns a private, bounded candidate to the coordinator, retaining
no dispatch permission while it is pending. This is a future design seam, not
a change to the current `send` contract: the existing backend transaction does
not roll back caller validation. A later implementation must supply an internal
prepare/commit/abort integration without silently changing public/mock shapes.
Caller authentication interpretation, schema/contract and candidate-cookie
validation must finish before the commit barrier in section 8.1. No backend
may commit cookies just because it has returned a transport 2xx.

Release network resources without destroying valid candidates (section 9).
Only after all validation, successful release, live authorization/generation
checks and a final deadline check may the coordinator atomically publish the
role authentication state and candidate jar. Then report success under the
same operation deadline. No next dispatch while a candidate is pending.
On caller failure/expiry/cleanup uncertainty, discard candidates and preserve
the old jar except for confirmed 401 invalidation; no temporary new-cookie
visibility or rollback-dependent follow-on send is allowed.

Every attempt sends Connection: close and destroys its socket/TLS/BIO/parser
state. No HTTP pooling, pipelining or cross-origin reuse, even for equal IPs or
certificates. Role cookies are not connection reuse.

## 8. One absolute operation budget

### 8.1 Coverage and accounting

The proposed **operation coordinator**, above session/authentication and
transport, is the sole absolute-deadline owner. Define operation entry `t0`
before initial authorization/policy validation, authentication input/secret
preparation, connection initialization, TLS/context preparation, serialization
or candidate selection. Create one validated monotonic deadline
`D = t0 + operation_timeout`.
It covers all TCP candidates, TLS handshake, request transmission, headers,
body, cookie processing, response construction/copy, eligible GET retries,
required caller-side response validation, final state commitment, local
cleanup/resource disposition and final result reporting.
Do not start it after a synchronous setup call to make timing appear compliant.

Secret resolution and login serialization are inside this boundary.
Current `SessionManager.authenticate` does them before transport entry;
neither it nor existing transport-only accounting implements this proposal.
Each explicitly authorized login/read/logout has its own operation budget;
a workflow-wide request/rate/session budget is separate and must be explicit.

Required setup (including synchronous trust/configuration validation) is also
inside the claimed boundary; preloading cannot exclude it. Only deployment
of the trusted supervisor itself precedes operation admission. The residual
uninterruptible supervisor work is explicitly a limitation in section 15.

Proposed ownership/propagation protocol, not a new implemented runtime contract:

1. The coordinator admits one non-reentrant operation with immutable operation
   ID, role/session generation, approval/binding/policy revision and D/clock
   domain. Missing/broken clock or policy fails explicitly before dispatch.
2. Authorization, secret preparation, transport and all caller validators
   receive the same immutable deadline context, or run under the coordinator's
   enclosing boundary. They cannot create a fresh timeout after return.
   The coordinator checks expiry before and after each synchronous stage.
3. Transport receipt yields only a tagged response/cookie candidate. Interpret
   authentication evidence, validate schema/contracts and the full candidate
   jar without mutating published state. HTTP 200 alone is insufficient.
4. Release network resources successfully while retaining candidates. Then
   revalidate current authorization/revocation, approval-clock health, role/
   session generation, binding/policy revision and D. Serialize this barrier
   with cancellation/revocation and reject reentrant sends.
5. Commit authentication and jar as one coordinator-owned transaction, never
   separate visible writes. Commit and the immediate post-commit clock check
   remain unpublished; if they cross D or generation changes, invalidate the
   transaction and discard candidates. Publish only a generation-bound success
   with a final live-deadline check; result reporting is part of the operation.
   No published role or cookie lease authorizes a dispatch without fresh checks.
6. Any failure/expiry retires the operation generation, rejects all pending or
   late results and prohibits success, role authentication, cookie commitment
   or another dispatch. A previously valid session need not be mislabeled
   expired: confirmed 401 expires its role; 403 does not. Quarantine on uncertain
   disposition independently blocks use. No automatic renewal/replay follows.

Session expiration is a separate lifetime limit, not D and not renewable by
transport progress. Authorization requires BOTH live session lifetime (where
applicable) and live operation D plus current approval. Approval wall-clock
rollback/uncertain freshness fails closed, not an extended permission. A
revocation arriving between validation and dispatch must prevent dispatch at
the serialized dispatch barrier; inability to enforce that barrier blocks use.
The approved policy requires fencing after observed expiry/revocation, not a claim
of instantaneous asynchronous preemption. An in-process check cannot preempt a stuck
call or close a scheduling gap with an unconditional real-time proof; sections 14-15
retain that limitation. Authorization-revocation race handling remains a prerequisite.

Proposed cleanup reserve `R` is mandatory and finite, `0 < R < timeout`.
Active work stops at `W = D - R`; `[W,D]` is reserved for disposition/reporting.
Authentication/schema/cookie validation and any role/jar commitment must finish
before W. Reserve work is limited to local disposition and bounded final result
handoff/reporting (including the supervisor's final metadata checks), never
renewed validation, network dispatch or a new role/jar commitment.
No approved reserve or numeric timeout is supplied here. Existing at-most-300
second contract ceilings are validation constraints, not lab authorization.

For a readiness wait compute immediately before waiting:

`wait = min(D - now, W - now, phase_end - now, candidate_end - now)`

Omit candidate_end only outside candidate connect. Reject nonfinite/broken
clock state; expire when any applicable budget is <=0. Each phase cap is set
once on phase entry; repeated bytes/WANT/spurious-ready events do not reset it.
Retries and addresses cannot reset D/W. Recheck after each wait/native call,
before consuming/committing results and after cleanup. Cleanup uses `D-now`,
not W. Never sleep for Retry-After, block on a queue or join a worker.

### 8.2 Preserved retry/error semantics

`HttpTransport` alone may retry eligible GET CONNECTION/TIMEOUT failures with
the same deadline; generic 0..3 retry policy remains unchanged. No retry on
TLS, malformed response, authorization, known HTTP rejection or cleanup failure.
A's active cutoff must be checked before a new attempt so the existing loop
cannot consume cleanup reserve through repeated immediate failures.
Initial lab policy explicitly requires `read_retries=0`.

Known non-2xx status retains priority over secondary timeout/cleanup/malformed
failures: 401 expires, 403 does not. 408/5xx after a write retain indeterminate
outcome with HTTP reason. Other IO/TLS/deadline failures of non-GET retain the
existing conservative write uncertainty, no replay. An initial expired deadline
remains TIMEOUT (indeterminate-write category with timeout reason for non-GET),
preserving E-044, not a generic BACKEND error. No status can be inferred if the
status line never completed.

### 8.3 What is and is not enforceable

**Plausible in-process control:** never intentionally initiate a readiness wait
longer than remaining budget; avoid blocking network helpers; check expiry
between bounded steps; never extend deadline on progress; reject late success.
This can eliminate resolver waits and ordinary stalled-peer indefinite waits
if the platform mechanisms work as designed.

**Not a hard whole-operation guarantee:** Python scheduling/GIL/GC, arbitrary
clock/adapters, memory allocation/copy, regex/JSON/cookie parsing, context and
CA/store loading, socket creation/options/getpeername, WinSock providers,
SSL certificate/handshake/read/write computation, select return scheduling,
close and finalizers have no defensible Python API worst-case wall-time bound.
A nonblocking flag is not native CPU preemption or cancellation of filesystem/
OS provider calls. Even finite wait timeouts can return after nominal expiry.
Reserve R allows best-effort cleanup; it cannot force close to return within R.

No finite maximum deadline overrun or hard resource-release time is claimed.
The former unconditional requirement was replaced by the 2026-11-20 owner policy
decision; that does not make transport-only accounting sufficient. Acceptance
still requires the complete-operation checks, termination escalation, exit/reap/
resource evidence, quarantine/no replacement and measured overruns under explicit
approved runtime assumptions. Continue fail-closed pending separately authorized
implementation, independent review and qualification. Do not label cooperative
accounting or synthetic clocks hard-real-time compliance.

## 9. Ownership, cleanup and quarantine

One operation owns one raw socket, one readiness registration, one TLS object,
two BIOs, bounded pending buffers and an uncommitted response/cookie candidate.
Record ownership immediately after acquisition and before the next failure
point. `SSLObject` has no raw-socket ownership; this avoids ambiguous
`SSLSocket`/file reference transfer. Backend owns role jar and any retained
uncertain resources. No destructor is the primary cleanup mechanism.

**Successful network-resource release:** mark the operation non-dispatchable;
retain bounded response and candidate jar plus generation/validation metadata;
remove readiness interest; explicitly close the raw socket without TLS unwrap/
close_notify waiting; release TLS/BIO/network buffers when safe. Confirm release
of every owned network resource. Required caller validation may precede release,
but both must complete before commitment. Keep response/cookie candidates until
the coordinator's section 8.1 barrier, atomic state publication and result
handoff complete. Only then release candidate references not needed by committed
state. Normal close must not destroy the successful result before validation.

**Failure/abort disposition:** retire dispatch permission/generation first;
discard response/cookie/authentication candidates; remove readiness interest;
close raw socket and release network state as above; retain uncertain handles
with explicit safe disposition status. Caller validation failure never commits
new cookies. Failed release converts a would-be success to failure/quarantine,
not a success with a warning. A confirmed non-2xx keeps status priority over
secondary cleanup/timeout, including 401 expiry and 403 non-expiry. No remote
logout is implied by either path.

| Trigger | Required disposition |
| --- | --- |
| Connect failure | Close before next candidate; no concurrent leftover attempt. |
| TLS failure / partial handshake | Close raw transport, discard all TLS state; no fallback/session export. |
| Malformed/oversized response | Reject candidate, close without reading/draining the rest; preserve confirmed status and old cookies as applicable. |
| Timeout / active cutoff | Stop all sends/reads; use reserve only for local disposition; late successful results cannot commit. |
| Confirmed 401 | Clear only affected role jar immediately; credentials/local session expiry follow existing manager rules even if release fails. |
| Local lifetime / revocation | Block next dispatch and release local role state; do not infer remote revocation or weaken 403 non-expiry. Future integration must explicitly dispose unused jar/TLS state rather than only dropping credential references. |
| Cleanup exception / uncertain ownership | Preserve primary category/status; flag cleanup failure; retain known uncertain resources, quarantine backend and prohibit retries/new sessions on it. |

No positive SO_LINGER/graceful shutdown wait. Audit socket option defaults and
WinSock closesocket/provider behavior; changing linger to a zero/abortive form
requires platform review and may not guarantee bounded close. Do not call
`shutdown`, `unwrap`, drain-to-EOF or blocking buffered close as a cleanup ritual.
If graceful TLS closure is later required, it becomes an explicitly timed state,
not a hidden unbounded finalizer.

Explicit local close is idempotent only after verified disposition. Failed close
keeps a reference/ownership record; retrying release is explicit local recovery,
not an infinite loop. Limit quarantine to the fixed resources of the one failed
operation and disable acquisition before it can grow across attempts. Do not
record resources as closed merely because close was attempted or a Python
attribute cleared. Readiness-close failures are explicit too.

**Guaranteed by design logic:** no reuse after uncertainty, no silent cleanup
success, candidate cookies withheld, status/primary reason preserved, independent
role ownership. **Best-effort in-process:** actual close and reference release,
completion before D, memory clearing. If cleanup itself never returns, Python
cannot run the reporting/quarantine code after it. An external supervisor must
then quarantine/terminate the whole worker; a timeout thread is insufficient.
Object release cannot guarantee credential memory erasure or server-session
revocation. Process termination cannot undo remote effects.

## 10. Authentication and session compatibility

Preserve Vision and Cyber Controller strategies and synthetic evidence labels;
do not merge their wire recipes. A backend only transports already-authorized
requests and owns cookies. It does not interpret login JSON or synthesize
JSESSIONID from body fields. No alternate Basic/cookie recipe is tried after a
denial, and no credentials are replayed automatically.

Every role gets independent manager ownership, binding, backend, private cookie
jar, TLS context/state and credential reference, even at the same origin/IP.
Reject sharing an already-owned backend without closing the other role's
resource. No authorization/cookie/proxy-auth caller override. Explicit successive
CC requests may use its existing strategy's managed Basic header; that is not
permission for automatic retries of authentication or fallback/relogin.

Preserve immediate cookie clear on confirmed 401, manager HTTP_REJECTION expiry,
and no renewal; 403 remains AUTHORIZATION with no inferred expiry or privilege
escalation. Quarantining a failed transport can prohibit further sends without
mislabeling a 403 session as expired. Preserve atomic cookie updates and
sanitized diagnostics, including sensitive custom header values and raw exception
chains. Local close never performs remote logout.

Vision status-only and CC HTTP-200-only mock success remain **unverified**.
Before any future laboratory read, an independently approved lab-scoped policy
must require exact build-specific HTTP/application/session evidence, a qualified
relationship between body `jsessionid`, Set-Cookie and outbound JSESSIONID, and
approved RBAC/Basic behavior. HTTP 200 alone is insufficient. Missing/conflicting
cookie evidence must not be repaired by invented tokens. Real authentication,
JSESSIONID compatibility, remote TTL/revocation and CC document provenance
remain unverified. Designing A does not implement that policy, activate a
capability/client, or pass any B gate.

## 11. Python 3.13 / Windows compatibility assessment

Target for subsequent qualification is the recorded **CPython 3.13.14 on
Windows 11**, not a newly inspected interpreter or a broader support claim.
E-044 records Windows-11-10.0.26300-SP0. No runtime/socket/TLS experiment was
performed for this design and no external documentation was fetched.

| Mechanism | API feasibility / required qualification |
| --- | --- |
| `ipaddress`, AF_INET/AF_INET6 numeric tuples | Standard-library mechanisms available in the target Python family. Audit CPython socket address conversion to exclude all resolver calls; qualify malformed/mapped/scope handling and IPv6 availability. |
| `setblocking(False)`, `connect_ex`, `SO_ERROR`, `getpeername` | Supported socket APIs; qualify WinSock codes, immediate/error readiness, tuple forms, provider behavior and ownership failures on exact build. |
| `select.select` | Supported for Windows sockets; qualify writable/exceptional connect behavior, timeout precision, spurious readiness and socket-close interaction. Not a general Windows file/pipe selector. |
| `MemoryBIO`, `SSLObject`, `wrap_bio`, WANT exceptions | Standard-library SSL APIs suitable for an explicit byte pump; exact linked OpenSSL, verification/SNI, pending records, close_notify, session tickets and pathological computation need qualification. API presence is not timing evidence. |
| SAN-only/ALPN/TLS policy | Audit exposed attributes and linked OpenSSL enforcement; reject unsupported policy instead of defaulting insecurely. Do not assume Linux SSL settings behave identically. |
| `time.monotonic` | Supported; E-044 uses it cooperatively. Qualify clock resolution, suspend/resume semantics and scheduling overruns; no hard real-time claim. |
| Local CA/system certificate loading | Synchronous, including Windows trust-store access/providers. Prefer explicitly approved local trust provenance; neither local disk nor store calls have a hard in-process duration guarantee. |
| Close/destruction | Public APIs exist, but neither nonblocking sockets nor BIO TLS proves bounded close/native finalization. The qualified containment policy requires platform lifecycle evidence, termination escalation and quarantine when disposition cannot be confirmed. |

A later exact-runtime audit must identify CPython implementation sources, SSL/
WinSock versions/providers, numerical error mappings and Windows-specific timeout
paths. API descriptions here are design premises pending that audit, not freshly
verified supported-runtime execution evidence. No Unix signal alarm, daemon
resolver threads or uncancellable executor jobs are proposed.

## 12. Permanent offline regression-test plan

No tests are added or executed now. Later implementation must retain all 425
existing cases and add focused permanent regressions that fail without A's
controls. Use only documentation-reserved synthetic identities, deterministic
fake monotonic clocks, scripted sockets, readiness/selector doubles, TLS/BIO
doubles and byte fragments. No real sockets, DNS, socketpair or loopback traffic.

Instrument forbidden resolver/socket/HTTP/URL entry points using the existing
offline guards, including failed attempts, and assert counters remain **zero**.
Inject the proposed socket/TLS adapter doubles without unpatching real socket
creation. Extend guards for any newly reachable API; ordinary real TLS context
construction must not accidentally open key logs. Doubles are test-only trusted
code, not production authorization.

| ID | Synthetic stimulus | Required permanent oracle |
| --- | --- | --- |
| A-01 Binding | Valid IPv4/IPv6; canonical duplicates; wrong family; numeric/Unicode/URL hostname; malformed port/address/scope/CIDR | Exact canonical selected sockaddr and original-host identity; invalid cases create zero sockets and zero resolver calls. |
| A-02 Authorization | Wrong origin/default-port variants, method/target/query, role, expired/revoked/stale approval; mock/version/previous-success bypass | Existing case/default-443 equivalence retained; all other bypasses fail before IO, with sanitized policy failure. |
| A-03 No DNS | Hostname retained for SNI; attempt socket/proxy/CA/download helper fallback | No forbidden DNS/network helper invoked on success, rejection, failure or cleanup; socket double receives numeric family tuple only. |
| A-04 Connect readiness | Immediate success, pending, writable-only failure, exceptional-only failure, both, spurious/empty readiness | `SO_ERROR` and selected peer verified; readiness alone cannot authorize TLS or a send. |
| A-05 TCP errors | Refusal/reset/unreachable, raised/returned errors, interruption, candidate cap, operation cutoff | Finite shared waits, correct CONNECTION/TIMEOUT; no leaked candidate or budget renewal. |
| A-06 Multiple addresses | First fails/second succeeds; first consumes all budget; close fails; peer/TLS mismatch | Approved order only, one open socket; no next address on expiry/quarantine/security failure; zero HTTP before peer/TLS. |
| A-07 Peer | Wrong approved-set member, different port/family, mapped/scope form, malformed tuple, query error | Exact selected-peer rule; no credentials sent and no address fallback after mismatch. |
| A-08 TLS transitions | WANT_READ generating output, WANT_WRITE, buffered plaintext, partial ciphertext flush, no-progress cycle | Correct dual interests, output flushed before read wait, no busy-loop renewal/loss/duplication; verified handshake required. |
| A-09 TLS identity | Certificate/name failure, IP mistakenly used as SNI, insecure context, keylog env/context, ALPN mismatch/session injection | Original hostname supplied; no fallback/retry, no key-log factory/file side effect, no cross-role/origin session use. |
| A-10 Partial writes | SSL and raw short counts, would-block, zero send, reset after partial login | Exact request bytes once; bounded buffers; indeterminate-write semantics and zero automatic replay. |
| A-11 Slow/stalled peer | One byte per clock advance, TLS protocol-only records, repeated readiness/WANT, header/body trickle | Same D/W across states; each wait <= remaining; no late send/commit; encrypted/framing caps independently enforced. |
| A-12 Deadline | Expired at entry/creation, TLS/context/copy/JSON/cookie/cleanup advances clock, invalid clock | E-044 initial TIMEOUT retained; late success rejected; no retries entering reserve; safe BACKEND on clock failure. |
| A-13 Headers | All fragmentation boundaries; bare LF/obs-fold/control/non-ASCII/colonless; duplicate names/equal lengths; 1xx/upgrade | Conservative failure independent of small body; complete status priority retained, no fabricated incomplete status. |
| A-14 Header limits | Exact and plus-one line/total/count; missing terminator; huge length digits | Reject before exceeding accumulator allowance; no body read for declared oversize; sanitized diagnostics. |
| A-15 Body framing | Fixed/exact/truncated/extra-buffered; close-delimited authenticated/abrupt EOF; CL+TE; forbidden compression | Correct completion, no malformed-under-cap success, no decompression/reuse or tail-as-next-response. |
| A-16 Chunk framing | Binary exact-limit split data/CRLF; `XY`, CR-X, bare LF; bad/huge size; missing zero/end; extensions/trailers/count overflow | Explicit E-044 delimiter oracle retained; validate after final payload byte; A-only metadata restrictions reported, not silently discarded. |
| A-17 Payload budget | Missing/misleading length, fragmented limit-1/limit/limit+1, multi-byte binary, excessive encrypted overhead | Exact bytes preserved; bounded read sizes/accumulators; payload cap independent of wire/framing/BIO caps. |
| A-18 Session/status | Confirmed 401/403/500 then header/body/deadline/cleanup failure; incomplete status; login failure | 401 expires only its role, 403 does not; known HTTP priority, write uncertainty and no credential renewal/replay. |
| A-19 Cookies | Independent same-origin roles; path/domain/expiry; malformed Max-Age/unexpected parser fault; cookie-cap overflow | Atomic candidate discard; old jar retained except 401; no warn-and-drop, flattening, secret output or cross-role updates. |
| A-20 Lifetime/reuse | Binding revision replacement, local expiration, backend sharing, retry/new operation on quarantined resource | Fresh independent state, no old cookies/TLS reuse; owner conflict cannot close other role; default live backend remains denied. |
| A-21 Cleanup | Fault at every acquisition/state; unregister/close throws or advances clock; explicit recovery | One owner per acquired handle, primary reason/status retained, cleanup flag, finite quarantine, no success/retry/new resources on uncertainty. |
| A-22 Sanitation | Secret markers in request, response, cookie, TLS/OS/adapter exception and cleanup error | No marker in repr, traceback chains, notes, stdout/stderr or safe evidence; categories/counts only. |

Assert exact scripted event sequences, byte counts, resource ownership and wait
values, not merely exception occurrence. Split short fixtures at every byte
boundary and combine WANT/partial-write/error transitions. Use small synthetic
limits and check equality and plus-one, including chunk delimiter processing
after reaching the payload cap. Measure guarded attempts, not only successful
connections. Keep address fallback distinct from transport attempt counts.

Doubles that throw or advance clocks verify deterministic control logic.
A double that returns cannot prove behavior of a native call that never returns.
Do not run deliberate infinite hangs in the test process to pretend to prove
cancellation. Supervisor hang/termination tests belong to a separately approved
containment implementation, with bounded externally controlled workers.

### 12.1 Additional negative-test oracles

The original **22 groups A-01..A-22 above are retained**, not replaced.
The following are proposed additions, not executed tests or runtime evidence.
All fault outcomes must assert no success, no candidate publication and no
unauthorized next dispatch, in addition to the stated oracle.

| Extends | Negative stimulus | Required additional oracle |
| --- | --- | --- |
| A-02, A-20 | Revoke approval after validation but before first/next dispatch; roll approval wall clock backward; replace generation during validation | Dispatch barrier rejects stale permission, zero sends after observed revocation; rollback cannot extend approval; old result cannot modify replacement role. Qualify check-to-use races separately. |
| A-03 | Python resolver mocks stay quiet while a native wrapper could resolve | Synthetic mocks prove only guarded paths. Exact CPython/WinSock source audit plus separately authorized native resolver/provider observation must establish no native DNS/hosts/service lookup; an unobservable path blocks qualification. |
| A-04, A-07 | `SO_ERROR` raises/nonzero/still-pending; `getpeername` raises or returns invalid data after write/exception readiness | No inferred connection/peer, no TLS credentials, no address fallback on query failure; separately qualify actual Windows readiness/error mappings. |
| A-08, A-10 | Outgoing BIO/pending-send saturation; WANT_READ/WANT_WRITE between partial plaintext and ciphertext writes | Backpressure stops production before cap; original segment/offset resumes exactly once, including WANT-generated output; no loss/duplication, busy spin or unbounded buffer growth. |
| A-12, A-19 | Auth interpreter, schema validator or cookie parser advances beyond D after transport returns; caller validation rejects an otherwise valid cookie response | Role remains unauthenticated for attempted login; candidate jar never visible, old jar retained except 401; no success or follow-on send. |
| A-13, A-15 | HTTP/1.0 TE; 204 with length/TE/body, 205 nonzero/TE/missing explicit zero, 304 metadata length with tail bytes | Reject unsupported framing under section 7.3; no read of a 304 representation length; 304 status priority retained; buffered illegal no-body payload rejected. |
| A-14, A-16, A-17 | Fragment every byte of `0\r\n\r\n` and data CRLF, including exact body cap; header/body/framing/wire/BIO limit-1, limit, limit+1 independently | Completion only after full terminal delimiter; exact permissible bounds accepted without over-allocation; plus-one rejected at responsible budget, no budget substitution. |
| A-19 | Huge single cookie/attribute, many Set-Cookie lines, candidate clone/parser expansion, conversion overflow | Preallocation/count/byte caps include old+candidate+parser copies; reject atomically before exceeding reviewed application allocation allowance. Native/parser hidden allocations require runtime memory qualification, not a hard RSS claim. |
| A-20 | Callback/validator reenters send, simultaneous role calls while candidate pending | Explicit sanitized ownership rejection, no recursive dispatch, no closing another operation's resources. |
| A-18, A-22 | Secret markers in IPC frames, malformed fields, crash/startup/cleanup diagnostics and chained exceptions | No markers in public result/log/stdout/stderr/crash evidence; 401/403 priority retained when confirmed evidence arrived; no raw IPC/body dump. |

### 12.2 Supervised-containment regression proposals

Use deterministic supervisor/process/IPC/clock doubles offline; never hang the
test runner or start real workers for these synthetic tests. Later Windows
lifecycle qualification is a separate, explicitly authorized evidence tier.

| ID | Synthetic stimulus | Required oracle / runtime distinction |
| --- | --- | --- |
| S-01 Admission | Invalid/oversized request, missing approval/limits, occupied or quarantined worker slot, reentrant start | Zero process creation/secret resolution; explicit safe failure; maximum one active worker across roles. |
| S-02 Stage timeout | Expiry during parent preflight, spawn/READY, worker authorization, secret preparation, trust load, TCP, TLS, send, receive, auth interpretation, JSON/schema, cookies, release, candidate IPC, parent decision, final report | Same parent D; no renewed deadline or late success. In-process doubles only demonstrate observations; native stalls and delayed parent scheduling remain runtime risks. |
| S-03 IPC | Oversized length prefix, truncation at every frame byte, malformed UTF-8/JSON, duplicate/unknown fields, nonfinite/deep values, bad version/sequence/generation, extra frame | Bounded reject before allocation/semantic work; no partial candidate commit; terminate/quarantine as needed; no pickle/object execution. |
| S-04 Late/crash | Candidate after timeout, duplicate old candidate, worker exit before complete frame, crash after 401/403 observation | Retired generation never revived, no restart/replay; confirmed 401 invalidates only its role, 403 non-expiry, missing status stays unknown. |
| S-05 Lifecycle | Spawn/assignment/READY failure, cancellation, termination request error, exit wait expiry, reap/handle-close failure, parent crash model | No assumed release or replacement worker; uncertain ownership retained/quarantined. Real Job Object, exit, descendant and handle behavior requires Windows qualification. |
| S-06 Commit race | Revoke/change session at candidate receipt; D passes during result checks, worker exit or report publication | Reject transaction and retire generation; no success or cookie/token export, even if worker claimed completion before D. |
| S-07 Remote effects | Terminate during login, after response before status IPC, after confirmed 401/403 | Explicit remote-session uncertainty; no automatic login/logout/write replay; separately approved operator recovery required. |

### 12.3 Evidence tiers

1. **Offline synthetic:** state transitions, byte/framing limits, no authorized
   code path to resolver helpers, failure priority and ownership. Requires no
   network and is the only proposed next implementation verification scope.
2. **Offline exact-runtime source audit:** CPython/SSL wrapper and Windows API
   paths, resolver exclusion and native-call inventory. Does not measure timing.
3. **Windows runtime qualification, separately authorized:** approved isolated
   synthetic TLS peer/platform fault scenarios, IPv4/IPv6, SNI/SAN/trust/EOF,
   readiness/error/close timing, resource exhaustion and lifecycle. It can
   require network and therefore is **not authorized or performed here**.
   Record exact Python/OpenSSL/OS/provider builds and measured overruns/leaks.
4. **Product qualification, separately authorized:** exact target/build/role/
   auth/cookie/schema/session evidence and all B gates. Neither prior tier
   establishes this compatibility.

## 13. Feasibility, risks and process fallback

### A. Requirements plausibly satisfiable

Explicit static address authorization; no application resolver/fallback;
original-host SNI/certificate/Host/cookie identity; selected peer checks;
nonblocking TCP/TLS byte pumping; bounded request/header/framing/entity buffers;
strict malformed/chunk/compression handling; one cooperative monotonic budget;
status/cookie/session/replay contracts; no connection reuse; deterministic
offline regression evidence. These are engineering hypotheses, not implemented
controls or runtime qualification.

### B. Platform-specific validation required

Resolver-free sockaddr conversion; WinSock pending/error mappings and exceptional
readiness; IPv6/peer tuple behavior; SSL/OpenSSL verification, SNI/ALPN/SAN-only/
resumption behavior; BIO/WANT pumping and EOF semantics; local trust providers;
timeout overruns, suspend/resume and close/resource lifetime under faults.

### C. Requirements not guaranteed in-process

Hard preemption of all synchronous Python/native/OS operations, fixed worst-case
operation return time, fixed cleanup-release time, secure memory erasure,
remote write reversal or remote authentication-session revocation. A cannot
honestly claim full hard-deadline compliance solely with nonblocking sockets.

### D. Remaining synchronous risks

Setup/authorization/trust/secret calls before existing transport entry; Python
parser/cookie/copy/GC work; native SSL verification/computation/allocation;
socket setup/peer/option/provider calls; readiness scheduling; close/finalizers.
Static IP approval can become operationally stale; peer match plus a valid
certificate is not proof of exact installed product/build. New parser/BIO
complexity and cookie/wire bounds need careful maintenance and failure tests.
CN/extension/trailer/EOF restrictions may reject an otherwise legal laboratory
server; incompatibility must stop, not trigger a permissive fallback.

### E. Complete-operation containment, not resolver fallback

The approved qualified containment policy requires evaluating the combined proposal in
[section 14](#14-complete-operation-supervised-containment). This does not
permit DNS: A still requires a proven resolver-free numeric connection path.
Containment cannot repair missing destination/authentication authorization.
The guarantee classification and A-versus-combined comparison in
[section 15](#15-guarantees-comparison-and-recommendation) control feasibility;
process isolation alone is not deadline-containment acceptance evidence.

### F. Minimum later implementation sequence

Only after explicit offline-implementation authorization and independent design
review:

1. Freeze binding/resource-policy contracts, A-only protocol restrictions,
   error/status compatibility and exact-runtime no-DNS audit acceptance criteria.
2. Add pure validators and synthetic binding/bypass tests; keep built-in dispatch
   disabled and production/mock capability separation intact.
3. Implement raw TCP/readiness ownership with synthetic candidate/peer/deadline/
   cleanup regressions; no real adapter execution.
4. Add BIO TLS pump and hostname/context policy doubles; verify WANT/output/
   partial-write/EOF/ownership transitions.
5. Add incremental parser and request serializer with malformed/header/chunk/
   binary/limit tests; reuse strict cookie policy and test atomic updates.
6. Integrate explicit backend injection, one budget/reserve, transport error
   priority, independent sessions and existing tests. Run targeted cases then
   the full retained offline suite; no production client/auth activation.
7. Obtain independent implementation review and exact-runtime source audit.
   Review the combined containment proposal against the 2026-11-20 policy,
   including explicit uncertainty and disposition evidence, not just test counts.
8. Seek separate Windows/runtime/auth/laboratory qualification authorization
   only after unresolved platform and B prerequisites are addressed. No step
   above authorizes it.

**Current policy assessment:** the independent E-046 review accepted architectural
direction with explicit limitations; the owner then approved qualified containment
policy direction only. Synthetic offline engineering is plausible but requires
separate implementation authorization. Complete-operation integration, exact IPC,
Windows lifecycle/recovery, revocation races, termination/reaping evidence,
runtime-specific deadline and TLS/product qualification, plus independent
implementation/security review remain prerequisites. Full CCV-010-C acceptance
remains withheld. Continue fail-closed; do not activate A alone or containment.

## 14. Complete-operation supervised containment

### 14.1 Narrow workflow and responsibility model

This is a proposal for a **separately authorized laboratory read-only workflow**,
not authority to execute it. Select one one-shot worker, one role, one immutable
binding and one finite approved procedure per run. It may prepare authentication
and perform only the fixed approved reads; authentication is the sole separately
authorized session-creating exception, not permission for configuration writes.
No arbitrary operation list, discovery, polling, automatic login refresh,
logout or mutation is admitted. Product/RBAC/schema qualification and all B
gates remain prerequisites. No numeric laboratory values are supplied.

The single operation boundary covers the entire procedure: initial authorization,
input/secret preparation, required setup, dispatch, receipt, authentication
interpretation, schema/contracts, candidate cookies, validated state commitment,
resource disposition and final reporting. DNS-only isolation is rejected.
No product payload/authentication/cookie parser runs in the parent after worker
return. Parent envelope checks are deliberately minimal but remain a residual
uninterruptible supervisor surface, not hidden outside the acceptance claim.

| Component | Sole responsibility / forbidden shortcut |
| --- | --- |
| Parent supervisor / operation coordinator | Admit bounded request; own D, current authorization and generation registry, worker slot, IPC endpoints, process/job handles and final result publication. Never perform product authentication/parsing or own reusable role cookies. Worker success is evidence to validate, not authority to commit. |
| Isolated worker | Execute complete approved procedure, including authorization snapshot validation, secret resolution, trust setup, auth interpretation, schema/cookie validation and local release, under inherited D. Own all network resources. No spawning children, dynamic executable payloads or writes outside approved scope. |
| A transport state machine | Exact numeric selected destination, no DNS, original-host TLS identity, nonblocking I/O, strict HTTP framing/status and bounded resources; no auth interpretation or independent deadline renewal. |
| Worker session coordinator | One private role/session generation and jar transaction; only validated provisional authentication/cookies can serve the fixed approved reads. No externally reusable authenticated role is published while the run is pending. |
| IPC channel | Bounded, sequenced control/status and sanitized result-candidate frames, not a token/cookie transport or arbitrary Python-object channel. |
| Deadline owner | Parent establishes D before initial request validation/spawn; worker receives same expiry/clock domain and a stricter active cutoff. Neither READY nor transport return resets it. |
| Cleanup/termination owner | Worker owns orderly socket/TLS/reference release; parent owns cancellation, Job Object termination, exit confirmation, reaping and closure of parent-owned handles. Neither claims the other's release based only on a message. |

The worker's private provisional jar may be used for a subsequent fixed read
only after full preceding response/auth/schema/cookie validation, successful
network release, current authorization and generation checks and sufficient
remaining D. No unvalidated candidate is usable. This is a whole-workflow
transaction: provisional auth is never an externally successful login; a later
failure discards it and blocks the remaining procedure. Parent final commitment
publishes only the sanitized validated read result and completion metadata.
All worker credentials/jars are destroyed on exit; no reusable session export.
This intentionally narrow future workflow is not a drop-in replacement for
the current generic session API and does not change it in this task.

### 14.2 Deadline, generation and commitment protocol

Before any preflight work, parent starts D and reserves finite startup,
active-work, termination/reap and final-report allowances within it. Mandatory
policy defines `startup_end <= W < D`, where W leaves cleanup/report reserve;
no numeric defaults are approved. Spawn and READY must complete by startup_end;
late READY cannot restart the clock. All work uses the same monotonic epoch on
the same machine, subject to exact-runtime verification; disagreement fails.

Parent validates request shape/size, complete numeric limits, exact procedure/
role/binding/policy approval, freshness and available worker slot **before
creation**. Secret preparation stays in worker. Parent preflight duration is
accounted and checked, not claimed forcibly interruptible by that worker.
The parent sends bounded dispatch permits scoped to operation/process/session
generation, exact step and current approval revision. A worker cannot renew
them or start a step after cutoff. Revocation cancels the run; serialize parent
permit issuance with revocation, then recheck in worker immediately before
dispatch. IPC delay or a paused worker creates a residual check-to-use race.
The approved policy prohibits dispatch after observed expiry/revocation; it does
not prove instantaneous asynchronous preemption. The authorization-observation
and dispatch-fencing mechanism still needs exact specification, tests and review;
unresolved races cannot be silently waived by this policy approval.

Use independent opaque operation ID, parent-run ID, process-generation ID and
role/session generation, never a PID alone (PIDs can be reused). Every message
includes all IDs plus sequence and policy revision. Cancellation, timeout,
replacement or approval change irrevocably retires that generation. Session
lifetime/remote TTL is independent of D and cannot extend it.

After worker validation and successful network release, it stages one bounded
sanitized RESULT_CANDIDATE and exits normally with no remaining role state.
The parent stages that frame, confirms complete IPC and expected normal exit,
reaps the worker, closes owned handles, then checks current authorization,
IDs, session lifetime where applicable, cleanup evidence and D. Only then may
it publish success, with a final deadline/generation check during reporting.
There is no parent cookie/auth-token commitment to race against worker death.
Any failed check discards the candidate and yields failure, never an attempt
to salvage partial success. If reporting crosses D, no successful completion
is valid; generation-bound results cannot authorize later work. Scheduler
delays around the last check/publication preclude an unconditional hard bound.

### 14.3 Windows lifecycle: CPython 3.13.14 qualification target

Use a fixed reviewed interpreter and worker entry point with Windows process
creation, not fork assumptions or an executor with uncancellable jobs.
Ordinary `multiprocessing` object queues are not the proposed IPC; they can
deserialize executable objects and hide feeder/finalizer lifecycle. A future
adapter must explicitly own process creation, allowlisted handle inheritance
and job membership. No command-line/environment credentials, shell launch or
inherited network sockets. Import/startup work is inside startup_end and D.

**Maximum active workers: one across all roles**, with at most one unreaped/
uncertain slot. Reject a second operation explicitly; no unbounded queue or
automatic replacement/restart. A quarantined slot is occupied until separately
authorized recovery confirms disposition, never hidden by a new supervisor.

Proposed Windows containment uses a parent-owned Job Object configured to
terminate members when its last owning handle closes, no worker job handle
inheritance and no breakaway/descendants. Create the process suspended, assign
it to the job before execution, and resume only after ownership is recorded.
Atomic job assignment at creation is an alternative only after source/API
qualification. Plain spawn-then-assign leaves an orphan/escape window and is
not accepted. CPython's high-level process APIs alone are not assumed to
provide these guarantees; reviewed Windows-specific integration is a blocking
design dependency. Nested-job restrictions, parent crash between creation and
assignment, handle duplication and suspended-process cleanup require explicit
proof/qualification. If orphan prevention cannot be demonstrated, do not spawn.

| State | Parent action and required transition |
| --- | --- |
| IDLE / PREFLIGHT | Own D and validate before acquisition; failure -> FAILED without worker. |
| STARTING | Record handles immediately; assign containment before run; wait boundedly for READY with exact IDs/version. Startup failure -> STOPPING, not respawn. |
| RUNNING | Issue only exact authorized permits; observe bounded health/stage frames. Heartbeat is liveness evidence only; it never extends D or proves native work interruptible. |
| CANDIDATE | Stage one full result; require normal exit and cleanup evidence before commit. No further dispatch. |
| STOPPING | Retire generation, close dispatch gate, request cooperative stop if time allows, then terminate job/worker within reserve; no dependency on worker Python finally blocks. |
| EXIT_OBSERVED | Confirm signaled process exit and exit code; collect/reap, verify job has no live members, close IPC/process/thread/job handles under recorded ownership. |
| COMMITTED / FAILED | Final classification only after required disposition and deadline checks; slot reusable only after confirmed release, not after termination request. |
| QUARANTINED | Termination, exit, reap, job membership or handle release uncertain: retain safe ownership ledger and occupied slot, failure only; prohibit further creation/dispatch pending authorized recovery. |

Use finite cancellable/observed IPC/process waits supported on Windows; socket
`select` is not a process/pipe waiter. Do not introduce blocking reader threads
that outlive the operation. Parent owns its IPC ends, job/process/primary-thread
handles; worker owns only explicitly inherited channel ends and its resources.
Close unused channel ends promptly so EOF means what the protocol expects.
Track acquisition and disposition individually; Python finalization is not a
reaping plan. Parent crash recovery depends on qualified job/handle behavior,
not a daemon flag, PID file or atexit handler.

A successful termination API request is **not proof** of process exit,
reaping, socket release or handle closure. Even observed exit does not prove
remote session revocation or instantaneous kernel/provider cleanup. If time
runs out before confirmation, report failed/quarantined with cleanup uncertainty
as soon as the parent can run; retain ownership for controlled recovery. Never
wait indefinitely to manufacture a clean result, drop a live process record,
or claim unconditional orphan prevention without the qualified creation path.

### 14.4 Authentication, cookies and secrets

Parent passes only an opaque approved secret reference, not secret values.
Worker resolves it inside D using a separately approved bounded provider.
The provider, ACLs and debugger/crash-dump access need qualification; no new
secret backend is authorized here. Worker exclusively owns credentials, Basic
material, tokens, private jar and candidate jar. Their lifetimes end with the
one-shot role generation; no cross-role sharing even at one origin.

Trust/authentication interpretation and strict cookie validation remain in
worker, not in a privileged parent callback. A pending candidate jar cannot
replace a committed/provisionally validated jar after caller validation failure.
HTTP 200 alone never qualifies authentication; exact build-specific evidence
and separate laboratory authorization remain mandatory. No cookie/token/body
`jsessionid` invention or credential recipe fallback.

On syntactically confirmed 401, worker invalidates only that role immediately,
discards its cookie candidates and emits a bounded confirmed-status frame as
soon as practical; 403 emits denial without semantic session expiry. Neither
allows replay/escalation. On parent receipt before timeout, confirmed non-2xx
priority survives later malformed body, crash, timeout and cleanup failure.
If worker dies before status transmission completes, parent cannot invent 401
or 403: outcome is unknown, all local worker state becomes unusable regardless.
Late status may refine failure-only recovery evidence, never revive success
or alter a replacement generation. Quarantine is not relabeled 403 expiry.

Termination during authentication or after remote session creation may leave
a live remote session, even with no local success/token. Termination after 401
does not prove remote logout; after 403 it does not prove remote expiration.
Record only sanitized remote-session uncertainty; require separately approved
operator disposition and remote TTL/RBAC policy. No automatic login/logout/
authentication/write replay, retry or worker restart to resolve uncertainty.
No claim of secure memory erasure, token revocation or deletion of OS paging/
crash-dump copies is made by reference release or process death.

### 14.5 Bounded IPC and trust boundary

Use a private local byte channel with access restricted to the approved account
and explicitly inherited endpoints; reject remote pipe access. Confidentiality
assumes a trusted OS/account and no hostile same-account debugger/admin.
IPC is not encryption, a secure enclave or protection from a compromised OS.
Worker is trusted fixed code but treated as fallible/untrusted for framing,
timing and state claims; a compromised worker can lie about semantic validation.
Containment is fault/lifecycle isolation, not a sandbox proof.

Finite policy maxima are mandatory before creation: `IPC_REQUEST_MAX`,
`IPC_RESPONSE_MAX`, `IPC_FRAME_MAX`, total IPC bytes, frame count, JSON nesting/
field count/string bytes and result-record count. Each maximum must be positive
and <= a reviewed finite implementation ceiling; request/response maxima must
fit their aggregate caps. Proposed protocol ceilings for independent review:
request payload **16 KiB**, result-candidate payload **64 KiB**, any frame
payload **64 KiB**, aggregate bidirectional payload **256 KiB**, **32 frames**
per run, JSON depth **8**, **32 fields** per object, string **4 KiB** UTF-8 and
**128 result records**. A fixed **4-byte unsigned length prefix** is also
charged to a separate total-wire cap of **256 KiB + 128 bytes**. Fail rather
than truncate a read result that cannot fit. These are proposed IPC design
ceilings, not installed defaults or approved laboratory resource settings;
explicit approved policy may only narrow them. No unbounded body pass-through.
Reject missing/unapproved maxima before spawning. Reject an oversize prefix
before reading/allocating payload; enforce total
bytes/count as well as per-frame caps, including error/status/health messages.

Versioned strict UTF-8 JSON records contain only bounded primitives:

| Direction / type | Permitted contents |
| --- | --- |
| Parent REQUEST | IDs, sequence, D/cutoffs/clock-domain tag, exact approved procedure and binding/policy references or bounded validated snapshot, role and opaque secret reference; no executable code. |
| Worker READY / STAGE | Matching IDs/version/sequence, fixed stage enum and bounded health counters, never payload/credential fragments. |
| Parent PERMIT / CANCEL | Matching IDs, fixed step and approval revision or fixed cancel reason; no broader delegated permission. |
| Worker CONFIRMED_STATUS / FAILURE | Exact supported status if confirmed, fixed safe category/reason/stage, possible-dispatch/remote-uncertainty/cleanup flags; no exception strings, wire data or secrets. |
| Worker RESULT_CANDIDATE | Matching IDs, procedure/schema version, complete validated flag, fixed authentication-evidence classification without token values, bounded allowlisted nonsecret read records and cleanup summary. No raw body, cookies or reusable authenticated-session handle. |

Reject duplicate/unknown keys, types outside exact schema, nonfinite numbers,
unsupported versions, wrong direction/order, repeated terminal frames, stale
IDs/revisions and excessive nesting. No pickle, marshal, eval, import-by-name
or arbitrary executable-object transfer. JSON bounds apply before expensive
semantic work; parser CPU/hidden allocation still lacks a hard bound.

Parent states are REQUEST -> READY -> authorized STAGE/PERMIT exchanges ->
one CANDIDATE -> confirmed exit/disposition -> final commitment, or FAILURE/
timeout -> STOPPING. READY/health/status alone cannot mean success. Truncated
prefix/payload, EOF before a terminal frame, malformed data or unexpected worker
exit yields explicit sanitized failure; discard all partial results. A complete
candidate followed by crash/nonzero exit is not success. Parent timeout retires
IDs before termination; drain/drop any late data only within bounded cleanup,
never deserialize it into live state. Success requires complete timely evidence
and final checks; timeout/crash/protocol/cleanup classifications retain known
HTTP status priority and conservative uncertain authentication/write effects.

## 15. Guarantees, comparison and recommendation

### 15.1 Guarantee classification

These are proposed mechanisms, not measured guarantees. Categories distinguish
logical control from actual return/resource-release timing.

| Subject / proposed guarantee | Classification and limit |
| --- | --- |
| Stalled TCP/TLS network readiness | **Enforceable by nonblocking I/O:** bound requested waits and incremental steps; cannot bound OS scheduling or synchronous SSL work. |
| Reject late/stale candidate; no new permit after observed expiry | **Enforceable by supervisor observation:** generation/deadline barrier when parent runs; not instantaneous cancellation while descheduled. |
| Stop stuck trust loading, native calls, TLS computation, HTTP/auth/schema/cookie parsing | **Dependent on process termination:** worker boundary contains them; actual interruption depends on OS termination and parent scheduling. |
| Worker startup/process creation and parent preflight/IPC parsing/commit/report | **Platform/runtime qualified only:** parent cannot forcibly interrupt itself; accounting is not a hard latency bound. |
| Clock epoch, startup latency, WinSock/no-DNS conversion, job assignment, descendant/handle semantics, exit/reap observation | **Platform/runtime qualified only:** require CPython 3.13.14, exact Windows/OpenSSL/provider source and runtime evidence; observations do not prove universal worst cases. |
| Orderly socket cleanup and Python finalization | **Best-effort:** bounded opportunity/reserve; never required for kill to take effect; failures prohibit success. |
| Worker termination/reaping and socket/kernel reclamation | **Dependent on process termination**, with **platform/runtime qualification** of exit/job/handle observations; no finite release guarantee from requesting kill or seeing exit alone. |
| Report/quarantine by D despite OS starvation, kernel/provider stall or supervisor failure | **Not currently achievable** as an unconditional guarantee on this target. |
| Whole-operation hard-real-time completion AND confirmed resource release by D | **Not currently achievable** as an unconditional guarantee; explicitly excluded from the revised acceptance policy, not retroactively demonstrated by either proposal. |
| Secure memory erasure / undo remote login or write / forced remote revocation | **Not currently achievable** by these mechanisms; remote operator disposition is separate, not a cleanup guarantee. |

Finite policy budgets limit application-observed allocations, not all OpenSSL/
JSON/native or OS memory. Scheduler delays, GC, suspend/resume and process
creation/termination calls may overrun reserves. Parent OS/API calls and its
own small parser/reporting path cannot be recursively solved by adding another
unbounded supervisor. These are explicit residual uncertainties, not omitted tests
or claims cured by policy approval. The approved acceptance evidence must measure
startup, termination, cleanup and reporting overruns on pinned approved builds and
separately classify observed expiry, safe reporting, termination requests, confirmed
exit, reaping and resource disposition. Unconfirmed termination/disposition requires
quarantine and no replacement operation, including across parent recovery.

### 15.2 A versus A plus complete-operation containment

| Dimension | Standalone A | A + supervised complete operation |
| --- | --- | --- |
| Satisfiable design scope | Numeric authorization/no-DNS path, original-host TLS, strict bounded HTTP, cooperative deadline and corrected transactional state | Same A controls plus external observation, generation fencing and termination option for stuck worker stages |
| Remaining gaps | No preemption of setup/native/auth/parser/cleanup calls; caller integration not implemented | No unconditional bound for supervisor scheduling/preflight/spawn/IPC/commit/kill/reap/kernel release; revocation check-to-use and orphan-safe creation unresolved |
| Windows dependencies | Numeric conversion, WinSock readiness/peer errors, SSL/trust, monotonic clock and close | All A dependencies plus same-clock IPC, secure channel ACL/handles, job-before-run creation, crash/descendant/exit/reap qualification |
| Lifecycle risk | In-process stuck close/finalizers can block reporting/quarantine | Job/handle ownership, partial spawn, uncertain kill/reap can leave occupied quarantined slot; remote sessions survive worker death |
| Auth/session implications | Coordinator must prevent early backend cookie commit and stale-role success | One role per one-shot worker, private provisional jar, no token export or reusable external session; uncertain remote login, no replay |
| Complexity / maintenance | High: custom parser, TLS pump, budgets and compatibility maintenance | Higher: all A work plus Windows adapter, IPC schemas/state machine, supervisor security, lifecycle and generation review |
| Required offline tests | Retain historical 425 cases plus all A-01..A-22 and section 12.1 additions | Same plus S-01..S-07 deterministic process/IPC/timeout/secret/lifecycle oracles |
| Required runtime qualification | Exact Windows/CPython/SSL/no-DNS/native allocation/readiness/cleanup evidence; independent auth/product gates | All A evidence plus spawn/job/orphan, parent crash, ACL/handle inheritance, real stage hangs, exit/reap/kill failures, stale frames and measured overruns |
| Acceptance conclusion | Transport-only accounting does not satisfy the approved complete-operation containment policy | Plausible direction for qualified acceptance; implementation, lifecycle evidence, measured overruns and review/qualification remain pending |

**Recommendation:** continue current fail-closed dispatch. The owner's 2026-11-20
decision explicitly replaces unconditional hard-interruption acceptance with
qualified deadline-accounted fail-closed containment; it is not acceptance of
observed timeout/cooperative return/kill request alone. Freeze exact IPC wire
schemas, worker/session ownership, Windows job-before-run creation and parent-crash/
quarantine recovery, authorization revocation fencing and termination/reaping
verification before separately authorized implementation. Require runtime-specific
deadline/overrun evidence, TLS/product compatibility qualification and independent
implementation/security review. No such implementation or execution is approved here.
Full CCV-010-C acceptance remains withheld; Gates A-D remain NOT PASSED.

## 16. Independent design-review requirements and stop

An independent reviewer must inspect the cited current modules/tests and
E-043/E-044 directly, not rely on this summary, and produce a requirement-by-
requirement evidence table and severity-ordered findings. Required review scope:

1. Binding schema/canonicalization, protected approval provenance/revocation,
   numeric parsing and exact selected peer; distinguish endpoint authorization
   from capability/build/role and prove there is no DNS/proxy fallback.
2. Exact CPython 3.13.14 Windows socket/SSL implementation path inventory;
   distinguish API availability, source reasoning, synthetic verification and
   executed platform evidence. Identify every remaining synchronous call.
3. TCP result/readiness/error/interruption/candidate budgets and release,
   including exceptional-only WinSock failure and no renewed address timeout.
4. TLS original-host SNI/SAN/chain verification, key-log prevention before
   factory side effects, trust/resumption/ALPN policy, WANT dual-direction pump,
   buffered data, handshake output flushing and partial write ownership.
5. Parser grammar/limits/EOF/no-body framing and exact-limit chunk delimiters;
   explicitly approve or reject A-only 1xx/extension/trailer/SAN/EOF restrictions.
   Reject private blocking parser/file helper reuse and malformed-under-cap success.
6. Peak and lifetime request/body/header/BIO/framing/cookie resource accounting;
   limits must be mandatory, finite and independently approved, not inherited
   from unapproved laboratory examples.
7. Deadline start/coverage/reserve/retries, response/cookie commit boundaries,
   initial TIMEOUT correction and confirmed status priority. Require an explicit
   verdict on hard interruption; a cooperative test result is insufficient.
8. Ownership/cleanup faults at every state, quarantine growth, blocking close
   and necessity of whole-process containment with verified termination/reaping.
9. Vision/CC strategy compatibility, independent roles/private cookies,
   401/403, strict atomic cookie policy, sanitation, no replay and unresolved
   laboratory JSESSIONID/auth/remote-session evidence.
10. Permanent A-01..A-22 tests and retention of all 425 existing cases; zero
    guarded attempts. Separate exact-runtime/platform/product qualification
    prerequisites and all unchanged authorization gates.
11. Corrected shared coordinator deadline, caller-validation transaction and
    separate successful-release/abort paths; prove no candidate is discarded
    early or cookies committed before caller validation and cleanup.
12. Sections 14-15 complete-operation boundary, one-shot role/session semantics,
    supervisor residual synchronous work, permit/revocation race and generation
    commitment; no resolver-only or transport-only interruption claim.
13. Windows suspended/job-before-run creation and parent-crash orphan prevention,
    ownership of every inherited/created handle, termination versus confirmed
    exit/reaping, quarantine recovery without uncontrolled replacement.
14. IPC framing/limits/ACL/trust assumptions, sanitized typed candidate schema,
    401/403 status-loss races, remote-session uncertainty and secret diagnostics;
    no unsafe deserialization or credential export.
15. Additional section 12.1 and S-01..S-07 negative oracles, synthetic versus
    runtime evidence, and an explicit verdict against the approved 2026-11-20
    deadline-containment policy. Reject tests-as-hard-real-time-proof.

Review must return: findings with source/policy anchors; unresolved assumptions
and required platform experiments; restriction decisions; explicit A-versus-
containment feasibility verdict; and a recommendation limited to offline
implementation, not laboratory execution or owner acceptance. Numeric policies,
actual restricted bindings and strengthened lab auth require separate approval.

**Stop here.** Design/documentation only is complete. No implementation,
test execution, connectivity, gate promotion, owner acceptance or subsequent
milestone follows from this document.

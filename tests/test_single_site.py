import copy
import hashlib
import importlib
import io
import json
import os
import ssl
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import Mock, patch

from offline_support import OfflineTestCase
from test_http_backend import MemoryConnection, MemoryResponse
from test_site_comparison import site


class SingleSiteTests(OfflineTestCase):
    def setUp(self):
        super().setUp()
        self.module = importlib.import_module("cc_vision_import.single_site")
        self.discovery = importlib.import_module("cc_vision_import.destination_discovery")
        self.comparison = importlib.import_module("cc_vision_import.site_comparison")
        self.http = importlib.import_module("cc_vision_import.http_backend")
        self.cli = importlib.import_module("cc_vision_import.master_cli")
        self.output = self.directory / "reports"
        self.output.mkdir()
        self.credentials = self.directory / "credentials.json"
        self.source_path = self.directory / "source.json"
        self.snapshot_path = self.directory / "snapshot.json"
        self.comparison_path = self.directory / "comparison.json"
        self.profile_path = self.directory / "profile.json"
        self.profile = {
            "destination": {"name": "destination", "base_url": "https://destination.invalid"},
            "tls": {"verify": True}, "output_directory": str(self.output),
        }
        self.source = {
            "schema_version": 1, "domain": "vision-organization-tree",
            "source": {"product": "vision", "version": "5.4.9", "name": "private-source"},
            "collected_at": "2026-11-25T12:00:00+00:00",
            "request": {"method": "GET", "path": "/mgmt/system/config/tree/Organization"},
            "scope": {"migration_input": False, "complete_configuration_backup": False},
            "evidence": {}, "record_count": 1, "record_count_basis": "top_level_json_records",
            "redacted_fields": 0, "issue_codes": [],
            "tree": site("private-source-root-id", "private-source-root",
                         site("private-source-site-id", "private-candidate")),
        }
        self.tree = site("destination-root-id", "Default")
        self.snapshot = {
            "schema_version": 1, "domain": "cc-destination-organization-sites",
            "destination": {"product": "cyber-controller", "version": "unknown"},
            "collected_at": "2026-11-25T13:00:00+00:00",
            "request": {"method": "GET", "path": "/mgmt/system/config/tree/Organization"},
            "scope": {"read_only": True, "configuration_writes_authorized": False,
                      "complete_site_enumeration": False, "migration_input": False, "devices_excluded": True},
            **self.discovery.project_site_tree(self.tree),
        }
        self.parent = {"ormID": "destination-root-id", "name": "Default", "parentOrmID": None, "type": "Site"}
        self.created = {"ormID": "destination-created-id", "name": "private-candidate",
                        "parentOrmID": "destination-root-id", "type": "Site", "token": "private-token"}
        self.result_tree = copy.deepcopy(self.tree)
        self.result_tree["children"].append({
            **site("destination-created-id", "private-candidate"), "parentOrmID": "destination-root-id",
        })
        self.save_inputs()

    def save_inputs(self):
        self.source_path.write_text(json.dumps(self.source))
        self.snapshot_path.write_text(json.dumps(self.snapshot))
        self.profile_path.write_text(json.dumps(self.profile))
        report = self.comparison.compare_sites(
            self.source, self.snapshot, source_root_name="private-source-root",
            destination_root_name="Default", confirm_root_mapping=True,
        )
        report["input_bindings"] = [
            {"slot": slot, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
            for slot, path in (("source-organization-tree", self.source_path),
                               ("destination-organization-sites", self.snapshot_path))
        ]
        self.comparison_path.write_text(json.dumps(report))

    def connection(self, payload, status=200):
        return MemoryConnection(MemoryResponse(
            status, json.dumps(payload).encode(), [("Content-Type", "application/json")],
        ))

    def login(self):
        return self.connection({"status": "ok", "jsessionid": "private-session"})

    def preflight(self, *, parent=None, tree=None, collision=None):
        return [
            self.connection(self.parent if parent is None else parent),
            self.connection({"status": "error"} if collision is None else collision,
                            404 if collision is None else 200),
            self.connection(self.tree if tree is None else tree),
        ]

    def sequence(self):
        return [
            self.login(), *self.preflight(), *self.preflight(),
            self.connection(self.created), self.connection(self.created), self.connection(self.result_tree),
        ]

    def run_engine(self, connections=(), *, execute=False, approve=None, reference="source:node-2", use_cli=False):
        before = [path.read_bytes() for path in (self.source_path, self.snapshot_path, self.comparison_path)]
        factory = Mock(side_effect=connections)
        out, err = io.StringIO(), io.StringIO()
        approval = Mock(return_value=True) if approve is None else approve
        with (
            patch.object(self.http.http.client, "HTTPSConnection", factory),
            patch.object(self.discovery, "_read_credentials", return_value={
                "username": "private-user", "password": "private-password",
            }),
            patch.object(self.module, "_interactive_approval", approval),
            redirect_stdout(out), redirect_stderr(err),
        ):
            if use_cli:
                status = self.cli.main([
                    "--operation", "single-site-create" if execute else "single-site-dry-run",
                    "--discovery-profile", str(self.profile_path), "--credentials-file", str(self.credentials),
                    "--input", str(self.source_path), "--comparison", str(self.comparison_path),
                    "--destination-snapshot", str(self.snapshot_path), "--site-reference", reference,
                ])
                report = json.loads(out.getvalue())
            else:
                report, status = self.module.run_single_site(
                    str(self.profile_path), str(self.credentials), str(self.source_path),
                    str(self.comparison_path), str(self.snapshot_path), reference,
                    execute=execute, target_version="10.10.7",
                )
        self.assertEqual(before, [path.read_bytes() for path in
                                 (self.source_path, self.snapshot_path, self.comparison_path)])
        serialized = json.dumps(report) + out.getvalue() + err.getvalue()
        for value in ("private-", "destination-root-id", "destination-created-id"):
            self.assertNotIn(value, serialized)
        for path in self.output.glob("*.json"):
            for value in ("private-", "destination-root-id", "destination-created-id"):
                self.assertNotIn(value, path.read_text())
        return int(status), report, factory, approval

    def assert_one_post(self, connections):
        writes = [r for c in connections for r in c.requests if r[0] != "GET" and r[1] != "/mgmt/system/user/login"]
        self.assertEqual(len(writes), 1)
        self.assertEqual(writes[0][:2], ("POST", "/mgmt/system/config/tree/site"))
        self.assertEqual(json.loads(writes[0][2]), {
            "name": "private-candidate", "parentOrmID": "destination-root-id",
        })

    def test_hash_bound_dry_run_cli_resolves_destination_parent_without_writes(self):
        connections = [self.login(), *self.preflight()]
        status, report, factory, approval = self.run_engine(connections, use_cli=True)
        self.assertEqual(status, 0)
        self.assertEqual(report["status"], "dry-run-ready")
        self.assertEqual(report["create_attempts"], 0)
        self.assertFalse(report["request_preview"]["body_generated"])
        self.assertEqual(factory.call_count, 4)
        approval.assert_not_called()
        self.assertFalse(list(self.output.glob(".ccv-site-attempt-*")))
        self.assertTrue(all(c.close_calls for c in connections))
        self.assertFalse(any(r[0] != "GET" and r[1] != "/mgmt/system/user/login"
                             for c in connections for r in c.requests))

    def test_authorized_one_create_cli_requires_new_destination_identity_and_hierarchy(self):
        connections = self.sequence()
        status, report, factory, approval = self.run_engine(connections, execute=True, use_cli=True)
        self.assertEqual(status, 0)
        self.assertEqual(report["status"], "single-site-verified")
        self.assertFalse(report["migration_ready"])
        self.assertTrue(report["readback_verified"])
        self.assertFalse(report["manual_reconciliation_required"])
        self.assertEqual(report["compatibility"], "experimental-unverified")
        self.assertEqual(report["create_attempts"], 1)
        approval.assert_called_once_with("https://destination.invalid", "source:node-2")
        self.assert_one_post(connections)
        self.assertEqual(factory.call_count, 10)
        self.assertTrue(all(c.close_calls for c in connections))
        self.assertEqual(len(list(self.output.glob(".ccv-site-attempt-*"))), 1)

    def test_declined_authorization_never_arms_create(self):
        connections = [self.login(), *self.preflight()]
        status, report, factory, _ = self.run_engine(connections, execute=True, approve=Mock(return_value=False))
        self.assertEqual(status, 1)
        self.assertEqual(report["status"], "cancelled")
        self.assertEqual(report["create_attempts"], 0)
        self.assertEqual(factory.call_count, 4)
        self.assertFalse(list(self.output.glob(".ccv-site-attempt-*")))

    def test_real_approval_requires_terminal_and_exact_separate_phrase(self):
        for terminal, phrase, approved in (
            (False, "CREATE source:node-2\n", False),
            (True, "\n", False), (True, "yes\n", False),
            (True, "CREATE source:node-3\n", False), (True, "CREATE source:node-2\n", True),
        ):
            with self.subTest(terminal=terminal, phrase=phrase):
                stdin = Mock()
                stdin.isatty.return_value = terminal
                stdin.readline.return_value = phrase
                with patch.object(self.module.sys, "stdin", stdin), redirect_stderr(io.StringIO()):
                    self.assertIs(self.module._interactive_approval(
                        "https://destination.invalid", "source:node-2",
                    ), approved)
                if not terminal:
                    stdin.readline.assert_not_called()

    def test_unavailable_private_report_storage_blocks_before_authentication(self):
        with patch.object(self.module.os, "open", side_effect=PermissionError("private-path")):
            status, report, factory, approval = self.run_engine((), execute=True)
        self.assertNotEqual(status, 0)
        self.assertEqual(report["issue_codes"], ["local_report_or_attempt_guard_failure"])
        self.assertEqual(report["create_attempts"], 0)
        factory.assert_not_called()
        approval.assert_not_called()

    def test_collisions_missing_parent_and_duplicate_parent_identity_block(self):
        duplicate = copy.deepcopy(self.tree)
        duplicate["children"].append(site("destination-root-id", "Other"))
        collision_tree = copy.deepcopy(self.tree)
        collision_tree["children"].append(site("another-id", "PRIVATE-CANDIDATE"))
        cases = [
            [self.login(), self.connection({}, 404)],
            [self.login(), *self.preflight(collision=self.created)],
            [self.login(), *self.preflight(parent={**self.parent, "ormID": None})],
            [self.login(), *self.preflight(tree=duplicate)],
            [self.login(), *self.preflight(tree=collision_tree)],
            [self.login(), *self.preflight(parent={**self.parent, "ormID": "private-source-root-id"})],
        ]
        for connections in cases:
            with self.subTest(count=len(connections)):
                status, report, _, approval = self.run_engine(connections, execute=True)
                self.assertNotEqual(status, 0)
                self.assertEqual(report["create_attempts"], 0)
                approval.assert_not_called()

    def test_parent_changes_after_authorization_block_before_post(self):
        connections = [self.login(), *self.preflight(),
                       self.connection({**self.parent, "ormID": "changed-id"}),
                       *self.preflight()[1:]]
        status, report, _, _ = self.run_engine(connections, execute=True)
        self.assertEqual(status, 1)
        self.assertEqual(report["create_attempts"], 0)
        self.assertFalse(list(self.output.glob(".ccv-site-attempt-*")))

    def test_unexpected_json_auth_or_read_errors_never_reach_authorization(self):
        for connection in (
            self.connection({"name": "Other", "ormID": "private-unexpected-id"}),
            self.connection([self.parent, self.parent]),
            self.connection({**self.parent, "status": "failed"}),
            self.connection(self.parent, 500),
            MemoryConnection(MemoryResponse(200, b"private-invalid-json")),
            MemoryConnection(failure=("getresponse", TimeoutError("private-timeout"))),
        ):
            with self.subTest(response=type(connection.response).__name__):
                status, report, factory, approval = self.run_engine([self.login(), connection], execute=True)
                self.assertNotEqual(status, 0)
                self.assertEqual(report["create_attempts"], 0)
                self.assertEqual(factory.call_count, 2)
                approval.assert_not_called()

    def test_failed_or_uncertain_create_never_retries_and_persistent_guard_blocks_reexecution(self):
        connection = MemoryConnection(failure=("getresponse", TimeoutError("private-timeout")))
        connections = [self.login(), *self.preflight(), *self.preflight(), connection]
        status, report, factory, _ = self.run_engine(connections, execute=True)
        self.assertEqual(status, 1)
        self.assertEqual(report["status"], "indeterminate")
        self.assertTrue(report["manual_reconciliation_required"])
        self.assert_one_post(connections)
        self.assertEqual(factory.call_count, 8)
        status, report, factory, approval = self.run_engine((), execute=True)
        self.assertEqual(status, 1)
        self.assertIn("prior_attempt_requires_manual_reconciliation", report["issue_codes"])
        factory.assert_not_called()
        approval.assert_not_called()

    def test_http_create_error_requires_reconciliation_no_rollback(self):
        connections = [self.login(), *self.preflight(), *self.preflight(),
                       self.connection({"message": "private-rejection"}, 500)]
        status, report, factory, _ = self.run_engine(connections, execute=True)
        self.assertEqual(status, 1)
        self.assertTrue(report["manual_reconciliation_required"])
        self.assertEqual(report["http_status"], 500)
        self.assert_one_post(connections)
        self.assertEqual(factory.call_count, 8)

    def test_missing_returned_identity_does_not_invent_by_name_success(self):
        connections = [self.login(), *self.preflight(), *self.preflight(),
                       self.connection({"name": "private-candidate", "status": "ok"})]
        status, report, factory, _ = self.run_engine(connections, execute=True)
        self.assertEqual(status, 1)
        self.assertEqual(report["status"], "indeterminate")
        self.assertEqual(factory.call_count, 8)
        self.assert_one_post(connections)

    def test_returned_identity_already_in_preflight_tree_is_not_a_new_site(self):
        baseline = copy.deepcopy(self.tree)
        baseline["children"].append(site("destination-created-id", "Other"))
        connections = [self.login(), *self.preflight(tree=baseline), *self.preflight(tree=baseline),
                       self.connection(self.created)]
        status, report, factory, _ = self.run_engine(connections, execute=True)
        self.assertEqual(status, 1)
        self.assertEqual(report["issue_codes"], ["created_identity_preexisted"])
        self.assertEqual(factory.call_count, 8)
        self.assertTrue(report["manual_reconciliation_required"])
        self.assert_one_post(connections)

    def test_wrong_parent_and_incomplete_tree_never_report_success(self):
        connections = [self.login(), *self.preflight(), *self.preflight(), self.connection(self.created),
                       self.connection({**self.created, "parentOrmID": "wrong-parent"})]
        status, report, factory, _ = self.run_engine(connections, execute=True)
        self.assertEqual(status, 1)
        self.assertEqual(report["status"], "indeterminate")
        self.assertEqual(factory.call_count, 9)
        self.assert_one_post(connections)

    def test_readback_polling_is_bounded_and_never_recreates(self):
        connections = [self.login(), *self.preflight(), *self.preflight(), self.connection(self.created),
                       *(self.connection({}, 404) for _ in range(3))]
        status, report, factory, _ = self.run_engine(connections, execute=True)
        self.assertEqual(status, 1)
        self.assertEqual(report["issue_codes"], ["bounded_readback_incomplete"])
        self.assertEqual(factory.call_count, 11)
        self.assert_one_post(connections)

    def test_created_object_missing_from_hierarchy_is_not_completed(self):
        connections = [self.login(), *self.preflight(), *self.preflight(), self.connection(self.created),
                       *(connection for _ in range(3)
                         for connection in (self.connection(self.created), self.connection(self.tree)))]
        status, report, factory, _ = self.run_engine(connections, execute=True)
        self.assertEqual(status, 1)
        self.assertEqual(report["issue_codes"], ["bounded_readback_incomplete"])
        self.assertEqual(factory.call_count, 14)
        self.assert_one_post(connections)

    def test_existing_tree_native_identity_contradictions_are_not_aliased(self):
        for tree in (
            {**self.tree, "ormID": "different-native-id"},
            {**self.tree, "children": [site("other-id", None)]},
            {**self.tree, "ormID": "same-id",
             "children": [{**site("other-id", "Other"), "ormID": "same-id"}]},
        ):
            with self.subTest(tree_keys=tuple(tree)):
                status, report, _, approval = self.run_engine(
                    [self.login(), *self.preflight(tree=tree)], execute=True,
                )
                self.assertNotEqual(status, 0)
                self.assertEqual(report["create_attempts"], 0)
                approval.assert_not_called()

    def test_binding_changes_unconfirmed_roots_and_unresolved_children_fail_before_auth(self):
        self.source_path.write_text(self.source_path.read_text() + "\n")
        with self.assertRaises(self.module.SiteBlocked):
            self.module.load_selection(str(self.source_path), str(self.comparison_path),
                                       str(self.snapshot_path), "source:node-2")
        self.source["tree"]["children"][0]["children"].append(site("private-child-id", "private-child"))
        self.save_inputs()
        with self.assertRaises(self.module.SiteBlocked) as caught:
            self.module.load_selection(str(self.source_path), str(self.comparison_path),
                                       str(self.snapshot_path), "source:node-3")
        self.assertEqual(caught.exception.code, "destination_parent_dependency_unresolved")
        report = json.loads(self.comparison_path.read_text())
        report["root_mapping"]["operator_confirmed"] = False
        self.comparison_path.write_text(json.dumps(report))
        status, report, factory, _ = self.run_engine((), use_cli=True)
        self.assertNotEqual(status, 0)
        factory.assert_not_called()

    def test_non_hardcoded_candidate_reference(self):
        self.source["tree"]["children"].insert(0, site("private-other-id", "private-other"))
        self.save_inputs()
        connections = [self.login(), *self.preflight()]
        status, report, _, _ = self.run_engine(connections, reference="source:node-3")
        self.assertEqual(status, 0)
        self.assertEqual(report["source_reference"], "source:node-3")

    def test_exact_allowlist_dry_run_no_create_and_backend_one_attempt_limit(self):
        selection = self.module.load_selection(str(self.source_path), str(self.comparison_path),
                                              str(self.snapshot_path), "source:node-2")
        profile = self.discovery.DiscoveryProfile.read(str(self.profile_path))
        backend = self.module.SingleSiteBackend(profile, selection)
        transport = importlib.import_module("cc_vision_import.transport")
        factory = Mock()
        with patch.object(self.http.http.client, "HTTPSConnection", factory):
            client = transport.HttpTransport(profile.transport, backend)
            for method in transport.HttpMethod:
                for segments in (
                    ("mgmt", "system", "config", "tree", "device"),
                    (*self.module._SITE_PATH, "byname", "Other"),
                    self.module._SITE_PATH,
                ):
                    with self.assertRaises(transport.TransportError):
                        client.request(method, segments)
        factory.assert_not_called()
        backend.close()

    def test_armed_backend_denies_second_post_arbitrary_origin_query_and_device_scope(self):
        selection = self.module.load_selection(str(self.source_path), str(self.comparison_path),
                                              str(self.snapshot_path), "source:node-2")
        profile = self.discovery.DiscoveryProfile.read(str(self.profile_path))
        transport = importlib.import_module("cc_vision_import.transport")
        backend = self.module.SingleSiteBackend(profile, selection)
        for method, path in (
            (transport.HttpMethod.PUT, "/mgmt/system/config/tree/site"),
            (transport.HttpMethod.DELETE, "/mgmt/system/config/tree/site"),
            (transport.HttpMethod.POST, "/mgmt/system/config/tree/device"),
            (transport.HttpMethod.GET, "/mgmt/system/config/tree/site/byname/Default?other=1"),
        ):
            with self.assertRaises(ValueError):
                self.http.SingleSiteAuthorization(profile.transport.base_url, ((method, path),))
        client = transport.HttpTransport(profile.transport, backend)
        connection = MemoryConnection(failure=("getresponse", TimeoutError("private-timeout")))
        with patch.object(self.http.http.client, "HTTPSConnection", return_value=connection) as factory:
            with self.assertRaises(transport.TransportError):
                client.request(transport.HttpMethod.GET, (*self.module._SITE_PATH, "byname", "Default"),
                               query=(("arbitrary", "1"),))
            other = transport.HttpTransport(
                transport.TransportConfig(
                    base_url="https://other.invalid", connect_timeout=10, read_timeout=30, operation_timeout=60,
                ), backend,
            )
            with self.assertRaises(transport.TransportError):
                other.request(transport.HttpMethod.GET, (*self.module._SITE_PATH, "byname", "Default"))
            factory.assert_not_called()
            backend.arm_create()
            for _ in range(2):
                with self.assertRaises(transport.TransportError):
                    client.request(transport.HttpMethod.POST, self.module._SITE_PATH, body=b"{}")
            self.assertEqual(factory.call_count, 1)
        self.assertEqual(backend.create_count, 1)
        backend.close()

    def test_attempt_guard_canonicalizes_default_https_port_across_invocations(self):
        connections = [self.login(), *self.preflight(), *self.preflight(), self.connection({}, 500)]
        status, _, _, _ = self.run_engine(connections, execute=True)
        self.assertEqual(status, 1)
        self.profile["destination"]["base_url"] = "https://destination.invalid:443"
        self.save_inputs()
        status, report, factory, _ = self.run_engine((), execute=True)
        self.assertNotEqual(status, 0)
        self.assertIn("prior_attempt_requires_manual_reconciliation", report["issue_codes"])
        factory.assert_not_called()

    def test_tls_failure_authentication_failure_and_explicit_lab_consent(self):
        connection = MemoryConnection(failure=("connect", ssl.SSLCertVerificationError("private-certificate")))
        status, report, factory, approval = self.run_engine([connection], execute=True)
        self.assertEqual(status, 1)
        self.assertEqual(report["issue_codes"], ["tls_certificate_failure"])
        self.assertFalse(report["authenticated"])
        self.assertEqual(connection.requests, [])
        self.assertEqual(factory.call_count, 1)
        approval.assert_not_called()
        status, report, factory, _ = self.run_engine([self.connection({"status": "error"})], execute=True)
        self.assertEqual(status, 1)
        self.assertFalse(report["authenticated"])
        self.assertEqual(factory.call_count, 1)
        self.profile["tls"] = {
            "verify": False, "lab_authorized": True, "authorized_origin": "https://destination.invalid",
        }
        self.save_inputs()
        with patch("cc_vision_import.tls_policy._private_file"), patch.dict(os.environ, {
            "CCV_ALLOW_INSECURE_TLS_EXCEPTION": "true",
        }):
            status, _, factory, _ = self.run_engine((), use_cli=True)
            self.assertNotEqual(status, 0)
            factory.assert_not_called()
            (self.directory / "tls-exception.json").write_text(json.dumps(self.profile["tls"]))
            connections = self.sequence()
            status, report, _, _ = self.run_engine(connections, execute=True)
            self.assertEqual(status, 0)
            self.assertEqual(report["tls"]["exception_scope"], "selected_origin_current_execution")
            self.assert_one_post(connections)

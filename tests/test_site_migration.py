import copy
import hashlib
import importlib
import io
import json
import ssl
import time
from contextlib import redirect_stderr, redirect_stdout
from urllib.parse import unquote
from unittest.mock import Mock, patch

from offline_support import OfflineTestCase
from test_http_backend import MemoryConnection, MemoryResponse
from test_site_comparison import site


class SiteServer:
    def __init__(self):
        self.root_id = "destination-root-id"
        self.sites = {"Default": {"name": "Default", "ormID": self.root_id, "parentOrmID": None}}
        self.posts = []
        self.calls = []
        self.verified = {self.root_id}
        self.last_readback = None
        self.fault_at = None
        self.fault = None
        self.remote_create_on_failure = True
        self.missing_returned_identity = False
        self.readback_404s = 0
        self.omit_created_from_tree = False
        self.invalid_lookup = False
        self.change_parent_after_create = False
        self.wrong_readback_parent = False
        self.duplicate_tree_identity = False
        self.before_post = None
        self.post_http_status = 200

    def seed(self, name, parent):
        identity = f"destination-site-{len(self.sites)}"
        self.sites[name] = {"name": name, "ormID": identity, "parentOrmID": parent}
        return identity

    def tree(self):
        def node(item):
            result = site(item["ormID"], item["name"])
            result["parentOrmID"] = item["parentOrmID"]
            result["children"] = [
                node(child) for child in self.sites.values() if child["parentOrmID"] == item["ormID"]
                and not (self.omit_created_from_tree and any(p["name"] == child["name"] for p in self.posts))
            ]
            return result
        return node(self.sites["Default"])

    def respond(self, request):
        method, path, body, _ = request
        self.calls.append((method, path))
        status = 200
        if path == "/mgmt/system/user/login":
            payload = {"status": "ok", "jsessionid": "private-session"}
        elif method == "POST" and path == "/mgmt/system/config/tree/site":
            payload = json.loads(body)
            self.posts.append(payload)
            if self.before_post is not None:
                self.before_post(payload)
            if payload["parentOrmID"] not in self.verified or payload["name"] in self.sites:
                raise AssertionError("Duplicate create or unverified destination parent.")
            if self.fault_at == len(self.posts) and not self.remote_create_on_failure:
                raise self.fault
            self.seed(payload["name"], payload["parentOrmID"])
            if self.fault_at == len(self.posts):
                raise self.fault
            payload = copy.deepcopy(self.sites[payload["name"]])
            status = self.post_http_status
            if self.missing_returned_identity:
                payload.pop("ormID")
        elif method == "GET" and "/site/byname/" in path:
            name = unquote(path.rsplit("/", 1)[-1])
            payload = self.sites.get(name)
            if payload is None:
                status = 400
                payload = {"status": "error", "message": (
                    "Invalid request private-token" if self.invalid_lookup else
                    f"M_00734: There is no device with name {name} configured in Cyber Controller."
                )}
            else:
                payload = copy.deepcopy(payload)
                if self.change_parent_after_create and self.posts and name == "Default":
                    payload["ormID"] = "changed-root-id"
        elif method == "GET" and "/site/byid/" in path:
            identity = unquote(path.rsplit("/", 1)[-1])
            payload = next((copy.deepcopy(row) for row in self.sites.values() if row["ormID"] == identity), None)
            if self.readback_404s:
                self.readback_404s -= 1
                payload = None
            if payload is None:
                status, payload = 404, {"status": "error"}
            else:
                self.last_readback = identity
                if self.wrong_readback_parent:
                    payload["parentOrmID"] = "private-wrong-parent"
        elif method == "GET" and path == "/mgmt/system/config/tree/Organization":
            payload = self.tree()
            if self.duplicate_tree_identity:
                payload["children"].append(site(self.root_id, "private-duplicate-identity"))
            if self.last_readback is not None and not self.omit_created_from_tree:
                self.verified.add(self.last_readback)
                self.last_readback = None
        else:
            raise AssertionError("Unexpected API operation.")
        return MemoryResponse(status, json.dumps(payload).encode(), [("Content-Type", "application/json")])


class ServerConnection(MemoryConnection):
    def __init__(self, server):
        super().__init__()
        self.server = server

    def getresponse(self):
        self.response = self.server.respond(self.requests[-1])
        return self.response


class SiteMigrationTests(OfflineTestCase):
    def setUp(self):
        super().setUp()
        self.module = importlib.import_module("cc_vision_import.site_migration")
        self.discovery = importlib.import_module("cc_vision_import.destination_discovery")
        self.http = importlib.import_module("cc_vision_import.http_backend")
        self.cli = importlib.import_module("cc_vision_import.master_cli")
        self.transport = importlib.import_module("cc_vision_import.transport")
        self.output = self.directory / "reports"
        self.output.mkdir()
        self.source_path = self.directory / "source.json"
        self.snapshot_path = self.directory / "snapshot.json"
        self.comparison_path = self.directory / "comparison.json"
        self.profile_path = self.directory / "profile.json"
        self.credentials = self.directory / "credentials.json"
        self.profile_path.write_text(json.dumps({
            "destination": {"name": "destination", "base_url": "https://destination.invalid"},
            "tls": {"verify": True}, "output_directory": str(self.output),
        }))
        root = site("private-source-root-id", "private-source-root")
        number = 1
        for index in range(8):
            parent = site(f"private-source-{number}", f"private-site-{number}")
            number += 1
            root["children"].append(parent)
            for child_index in range(3 if index < 6 else 2):
                child = site(f"private-source-{number}", f"private-site-{number}")
                number += 1
                parent["children"].append(child)
                if index == 0:
                    parent = child
        self.assertEqual(number - 1, 30)
        self.source = {
            "schema_version": 1, "domain": "vision-organization-tree",
            "source": {"product": "vision", "version": "5.4.9", "name": "private-source"},
            "collected_at": "2026-11-25T12:00:00+00:00",
            "request": {"method": "GET", "path": "/mgmt/system/config/tree/Organization"},
            "scope": {"migration_input": False, "complete_configuration_backup": False},
            "evidence": {}, "record_count": 1, "record_count_basis": "top_level_json_records",
            "redacted_fields": 0, "issue_codes": [], "tree": root,
        }
        server = SiteServer()
        self.snapshot = {
            "schema_version": 1, "domain": "cc-destination-organization-sites",
            "destination": {"product": "cyber-controller", "version": "unknown"},
            "collected_at": "2026-11-25T13:00:00+00:00",
            "request": {"method": "GET", "path": "/mgmt/system/config/tree/Organization"},
            "scope": {"read_only": True, "configuration_writes_authorized": False,
                      "complete_site_enumeration": False, "migration_input": False, "devices_excluded": True},
            **self.discovery.project_site_tree(site(server.root_id, "Default")),
        }
        self.save_inputs()
        self.plan = self.module.load_plan(str(self.source_path), str(self.comparison_path), str(self.snapshot_path))
        self.context = ssl.create_default_context()

    def save_inputs(self):
        self.source_path.write_text(json.dumps(self.source))
        self.snapshot_path.write_text(json.dumps(self.snapshot))
        comparison = importlib.import_module("cc_vision_import.site_comparison").compare_sites(
            self.source, self.snapshot, source_root_name="private-source-root",
            destination_root_name="Default", confirm_root_mapping=True,
        )
        comparison["input_bindings"] = [{
            "slot": slot, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        } for slot, path in (("source-organization-tree", self.source_path),
                             ("destination-organization-sites", self.snapshot_path))]
        self.comparison_path.write_text(json.dumps(comparison))

    def run_batch(self, server, *, mode="dry-run", approval=True, use_cli=False, human=False, **options):
        before = [path.read_bytes() for path in (self.source_path, self.snapshot_path, self.comparison_path)]
        factory = Mock(side_effect=lambda *a, **k: ServerConnection(server))
        approve = Mock(return_value=approval)
        out, err = io.StringIO(), io.StringIO()
        with (
            patch.object(self.http.http.client, "HTTPSConnection", factory),
            patch.object(self.discovery, "_read_credentials", return_value={
                "username": "private-user", "password": "private-password",
            }),
            patch.object(self.transport.TransportConfig, "tls_context", return_value=self.context),
            patch.object(self.module, "_approval", self.module._approval if approval is None else approve),
            redirect_stdout(out), redirect_stderr(err),
        ):
            if use_cli:
                status = self.cli.main([
                    "--operation", "site-batch-" + mode, "--discovery-profile", str(self.profile_path),
                    "--credentials-file", str(self.credentials), "--input", str(self.source_path),
                    "--comparison", str(self.comparison_path), "--destination-snapshot", str(self.snapshot_path),
                    "--operation-delay", "0", "--readback-interval", "0",
                    *([] if human else ["--report-format", "json"]),
                ])
                if human:
                    report = json.loads(max(self.output.glob("ccv-sites-report-*.json"),
                                            key=lambda path: path.stat().st_mtime_ns).read_text())
                else:
                    envelope = json.loads(out.getvalue())
                    self.assertNotIn("dependency_order", envelope)
                    self.assertNotIn("plan_sha256", envelope)
                    report = json.loads((self.output / envelope["report_file"]).read_text())
            else:
                report, status = self.module.run_site_migration(
                    str(self.profile_path), str(self.credentials), str(self.source_path),
                    str(self.comparison_path), str(self.snapshot_path), mode=mode,
                    operation_delay=options.pop("operation_delay", 0), readback_interval=options.pop("readback_interval", 0),
                    **options,
                )
        self.assertEqual(before, [path.read_bytes() for path in
                                 (self.source_path, self.snapshot_path, self.comparison_path)])
        serialized = json.dumps(report) + out.getvalue() + err.getvalue()
        for secret in ("private-", "destination-root-id", "destination-site-", "changed-root-id"):
            self.assertNotIn(secret, serialized)
        for path in self.output.glob("ccv-sites-report-*.json"):
            for secret in ("private-", "destination-root-id", "destination-site-"):
                self.assertNotIn(secret, path.read_text())
        self.assertEqual(json.loads((self.output / report["report_file"]).read_text()), report)
        if human:
            self.assertNotIn('"schema_version"', out.getvalue())
            self.assertNotIn("dependency_order", out.getvalue())
            self.assertNotIn(self.plan.digest, out.getvalue() + err.getvalue())
            self.assertNotIn(self.plan.digest[:12], out.getvalue() + err.getvalue())
            self.assertTrue(out.getvalue().rstrip().endswith(str(self.output / report["report_file"])))
        self.console = out.getvalue() + err.getvalue()
        return int(status), report, approve

    def test_complete_30_site_dry_run_covers_all_22_dependencies_without_writes(self):
        server = SiteServer()
        status, report, approve = self.run_batch(server, use_cli=True)
        self.assertEqual(status, 0)
        self.assertEqual(report["status"], "dry-run-ready")
        self.assertEqual(report["counts"]["total"], 30)
        self.assertEqual(report["counts"]["pending"], 30)
        self.assertEqual(report["create_attempts"], 0)
        self.assertEqual(sum(site.parent_reference != self.plan.root_reference for site in self.plan.sites), 22)
        self.assertEqual([row["source_reference"] for row in report["sites"]],
                         [site.selection.reference for site in self.plan.sites])
        self.assertEqual(server.posts, [])
        self.assertFalse(list(self.output.glob("*.journal.json")))
        approve.assert_not_called()

    def test_entire_batch_executes_in_verified_parent_order_with_destination_id_remapping(self):
        server = SiteServer()
        def verify_reservation(payload):
            journal = json.loads(next(self.output.glob("*.journal.json")).read_text())
            reference = next(site.selection.reference for site in self.plan.sites
                             if site.selection.name == payload["name"])
            self.assertEqual(journal["incomplete_operation"]["reference"], reference)
            self.assertEqual(journal["sites"][reference]["create_attempts"], 1)
            self.assertFalse(journal["sites"][reference]["verified"])
        server.before_post = verify_reservation
        status, report, approve = self.run_batch(server, mode="execute", use_cli=True)
        self.assertEqual(status, 0)
        self.assertEqual(report["status"], "batch-verified")
        self.assertEqual(report["counts"]["created"], 30)
        self.assertEqual(report["counts"]["verified"], 30)
        self.assertEqual(len(server.posts), 30)
        self.assertEqual(len({row["name"] for row in server.posts}), 30)
        self.assertEqual(report["compatibility"], "experimental-unverified")
        approve.assert_called_once_with("https://destination.invalid", 30, self.plan.digest)
        for site_entry, post in zip(self.plan.sites, server.posts, strict=True):
            self.assertEqual(post["name"], site_entry.selection.name)
            expected_parent = "Default" if site_entry.selection.parent_is_root else site_entry.selection.parent_name
            self.assertEqual(post["parentOrmID"], server.sites[expected_parent]["ormID"])
            self.assertNotIn(post["parentOrmID"], site_entry.selection.source_identities)
        journal = json.loads((self.output / report["journal_file"]).read_text())
        self.assertIsNone(journal["incomplete_operation"])
        self.assertEqual(sum(row["verified"] for row in journal["sites"].values()), 30)
        self.assertTrue(all("/device" not in path and method in ("GET", "POST") for method, path in server.calls))

    def test_existing_sites_require_identity_and_parent_readback_without_duplicate_posts(self):
        server = SiteServer()
        parent = server.seed("private-site-1", server.root_id)
        server.seed("private-site-2", parent)
        status, report, _ = self.run_batch(server, mode="execute")
        self.assertEqual(status, 0)
        self.assertEqual(report["counts"]["already_existing"], 2)
        self.assertEqual(report["counts"]["created"], 28)
        self.assertEqual(report["counts"]["verified"], 30)
        self.assertEqual(len(server.posts), 28)
        self.assertFalse(any(row["name"] in ("private-site-1", "private-site-2") for row in server.posts))

    def test_batch_authorization_is_separate_and_cancellation_never_creates(self):
        server = SiteServer()
        status, report, approve = self.run_batch(server, mode="execute", approval=False)
        self.assertEqual(status, 1)
        self.assertEqual(server.posts, [])
        self.assertEqual(report["create_attempts"], 0)
        self.assertFalse(list(self.output.glob("*.journal.json")))
        approve.assert_called_once()

    def test_ambiguous_first_create_stops_batch_and_resume_reconciles_without_second_post(self):
        server = SiteServer()
        server.fault_at, server.fault = 3, TimeoutError("private-uncertain-response")
        status, report, _ = self.run_batch(server, mode="execute")
        self.assertEqual(status, 1)
        self.assertEqual(len(server.posts), 3)
        self.assertEqual(report["counts"]["verified"], 2)
        self.assertEqual(report["counts"]["pending"], 27)
        self.assertTrue(report["manual_reconciliation_required"])
        server.fault_at = None
        status, report, _ = self.run_batch(server, mode="resume")
        self.assertEqual(status, 0)
        self.assertEqual(report["counts"]["verified"], 30)
        self.assertEqual(report["counts"]["reconciled"], 1)
        self.assertEqual(len(server.posts), 30)
        self.assertEqual(len({row["name"] for row in server.posts}), 30)
        self.assertEqual([row["source_reference"] for row in report["sites"]],
                         [site.selection.reference for site in self.plan.sites])
        self.assertEqual(report["counts"]["verified_this_run"], 30)

    def test_interrupt_after_remote_create_is_reconciled_without_repeating_post(self):
        server = SiteServer()
        server.fault_at, server.fault = 1, KeyboardInterrupt()
        status, report, _ = self.run_batch(server, mode="execute")
        self.assertEqual(status, 1)
        self.assertEqual(len(server.posts), 1)
        self.assertEqual(report["counts"]["pending"], 29)
        server.fault_at = None
        status, report, _ = self.run_batch(server, mode="resume")
        self.assertEqual(status, 0)
        self.assertEqual(len(server.posts), 30)

    def test_remote_absence_after_timeout_never_allows_blind_retry(self):
        server = SiteServer()
        server.fault_at, server.fault = 1, TimeoutError("private-timeout")
        server.remote_create_on_failure = False
        status, _, _ = self.run_batch(server, mode="execute")
        self.assertEqual(status, 1)
        server.fault_at = None
        status, report, _ = self.run_batch(server, mode="resume")
        self.assertEqual(status, 1)
        self.assertTrue(report["manual_reconciliation_required"])
        self.assertIn("prior_attempt_requires_manual_reconciliation", report["issue_codes"])
        self.assertEqual(len(server.posts), 1)

    def test_missing_returned_identity_and_incomplete_readback_stop_after_first_post(self):
        for fault in ("missing_returned_identity", "omit_created_from_tree"):
            with self.subTest(fault=fault):
                server = SiteServer()
                setattr(server, fault, True)
                status, report, _ = self.run_batch(server, mode="execute")
                self.assertEqual(status, 1)
                self.assertEqual(len(server.posts), 1)
                self.assertEqual(report["counts"]["verified"], 0)
                self.assertEqual(report["counts"]["pending"], 29)
                self.assertTrue(report["manual_reconciliation_required"])
                if fault == "omit_created_from_tree":
                    by_id = [path for method, path in server.calls if "/byid/" in path]
                    self.assertEqual(len(by_id), 3)
                for path in self.output.glob("*.journal.json"):
                    path.unlink()
                for path in self.output.glob(".ccv-site-attempt-*.json"):
                    path.unlink()

    def test_invalid_collision_response_wrong_parent_and_changed_parent_stop_safely(self):
        server = SiteServer()
        server.invalid_lookup = True
        status, report, _ = self.run_batch(server, mode="execute")
        self.assertEqual(status, 1)
        self.assertEqual(server.posts, [])
        self.assertEqual(report["http_status"], 400)
        journal = self.output / report["journal_file"]
        self.assertFalse(journal.exists())
        other = server.seed("private-other-parent", server.root_id)
        server.seed("private-site-1", other)
        server.invalid_lookup = False
        status, report, _ = self.run_batch(server, mode="execute")
        self.assertEqual(status, 1)
        self.assertEqual(server.posts, [])
        self.assertIn("existing_site_parent_mismatch", report["issue_codes"])

    def test_readback_polling_and_between_site_delays_are_bounded_and_configurable(self):
        server = SiteServer()
        server.readback_404s = 2
        sleep = time.sleep
        with patch("time.sleep", side_effect=lambda seconds: sleep(seconds) if seconds == 0.02 else None) as delay:
            status, report, _ = self.run_batch(server, mode="execute", operation_delay=0.25, readback_interval=0.5)
        self.assertEqual(status, 0)
        self.assertEqual(sum(call.args == (0.25,) for call in delay.call_args_list), 29)
        self.assertEqual(sum(call.args == (0.5,) for call in delay.call_args_list), 2)
        self.assertEqual(report["counts"]["verified"], 30)

    def test_journal_binding_changes_are_rejected_before_authentication(self):
        server = SiteServer()
        server.fault_at, server.fault = 1, TimeoutError("private-timeout")
        _, report, _ = self.run_batch(server, mode="execute")
        path = self.output / report["journal_file"]
        journal = json.loads(path.read_text())
        journal["binding"]["plan"]["source_sha256"] = "0" * 64
        path.write_text(json.dumps(journal))
        calls = len(server.calls)
        status, report, approve = self.run_batch(server, mode="resume")
        self.assertEqual(status, 1)
        self.assertIn("migration_journal_binding_mismatch", report["issue_codes"])
        self.assertEqual(len(server.calls), calls)
        approve.assert_not_called()

    def test_source_hash_and_comparison_order_cannot_be_substituted(self):
        self.source_path.write_text(self.source_path.read_text() + "\n")
        with self.assertRaises(self.module.SiteBlocked):
            self.module.load_plan(str(self.source_path), str(self.comparison_path), str(self.snapshot_path))
        self.save_inputs()
        report = json.loads(self.comparison_path.read_text())
        report["source_dependency_order"].reverse()
        self.comparison_path.write_text(json.dumps(report))
        with self.assertRaises(self.module.SiteBlocked):
            self.module.load_plan(str(self.source_path), str(self.comparison_path), str(self.snapshot_path))

    def test_wrong_parent_readback_stops_before_any_child_or_second_create(self):
        server = SiteServer()
        server.wrong_readback_parent = True
        status, report, _ = self.run_batch(server, mode="execute")
        self.assertEqual(status, 1)
        self.assertEqual(len(server.posts), 1)
        self.assertEqual(report["counts"]["verified"], 0)
        self.assertIn("readback_identity_or_parent_mismatch", report["issue_codes"])

    def test_changed_parent_identity_and_duplicate_remote_identity_block_batch(self):
        server = SiteServer()
        server.duplicate_tree_identity = True
        status, report, _ = self.run_batch(server, mode="execute")
        self.assertEqual(status, 1)
        self.assertIn("duplicate_tree_identity", report["issue_codes"])
        self.assertEqual(server.posts, [])
        server.duplicate_tree_identity = False
        server.change_parent_after_create = True
        status, report, _ = self.run_batch(server, mode="execute")
        self.assertEqual(status, 1)
        self.assertIn("batch_parent_identity_changed", report["issue_codes"])
        self.assertEqual(len(server.posts), 4)

    def test_origin_lock_rejects_concurrent_batch_and_releases_after_exception(self):
        path = self.output / ".test.lock"
        with self.assertRaisesRegex(self.module.SiteBlocked, "batch_operation_already_running"):
            with self.module._origin_lock(path):
                with self.module._origin_lock(path):
                    self.fail("Concurrent owner admitted.")
        with self.module._origin_lock(path):
            pass

    def test_resume_rejects_malformed_and_inconsistent_journal_without_network_calls(self):
        server = SiteServer()
        server.fault_at, server.fault = 1, TimeoutError("private-timeout")
        _, report, _ = self.run_batch(server, mode="execute")
        path = self.output / report["journal_file"]
        original = path.read_bytes()
        calls = len(server.calls)
        for mutation in ("invalid_utf8", "missing_active", "active_after_pending", "verified_without_identity"):
            with self.subTest(mutation=mutation):
                journal = json.loads(original)
                if mutation == "invalid_utf8":
                    path.write_bytes(b"\xff")
                else:
                    first = self.plan.sites[0].selection.reference
                    second = self.plan.sites[1].selection.reference
                    if mutation == "missing_active":
                        journal["incomplete_operation"] = None
                    elif mutation == "active_after_pending":
                        journal["sites"][second]["create_attempts"] = 1
                        journal["sites"][first]["create_attempts"] = 0
                        journal["incomplete_operation"]["reference"] = second
                    else:
                        journal["sites"][first]["verified"] = True
                    path.write_text(json.dumps(journal))
                status, _, approve = self.run_batch(server, mode="resume")
                self.assertEqual(status, 1)
                self.assertEqual(len(server.calls), calls)
                approve.assert_not_called()
        path.write_bytes(original)

    def test_failed_local_journal_persistence_prevents_post(self):
        server = SiteServer()
        original = self.module._write_private
        def persist(path, payload):
            if path.name.endswith(".journal.json") and payload.get("incomplete_operation") is not None:
                raise OSError("private-local-storage-error")
            return original(path, payload)
        with patch.object(self.module, "_write_private", side_effect=persist):
            status, report, _ = self.run_batch(server, mode="execute")
        self.assertEqual(status, 1)
        self.assertEqual(server.posts, [])
        self.assertTrue(report["manual_reconciliation_required"])
        self.assertIn("migration_journal_persistence_failed", report["issue_codes"])

    def test_http_create_failure_is_ambiguous_and_never_automatically_repeated(self):
        server = SiteServer()
        server.post_http_status = 500
        status, report, _ = self.run_batch(server, mode="execute")
        self.assertEqual(status, 1)
        self.assertEqual(report["http_status"], 500)
        self.assertEqual(len(server.posts), 1)
        self.assertTrue(report["manual_reconciliation_required"])
        journal = json.loads((self.output / report["journal_file"]).read_text())
        self.assertEqual(journal["incomplete_operation"]["http_status"], 500)

    def test_existing_journal_requires_explicit_resume_without_new_authentication(self):
        server = SiteServer()
        server.fault_at, server.fault = 1, TimeoutError("private-timeout")
        _, report, _ = self.run_batch(server, mode="execute")
        before = (self.output / report["journal_file"]).read_bytes()
        calls = len(server.calls)
        status, report, approve = self.run_batch(server, mode="execute")
        self.assertEqual(status, 1)
        self.assertIn("batch_journal_exists_resume_required", report["issue_codes"])
        self.assertEqual(len(server.calls), calls)
        self.assertEqual((self.output / report["journal_file"]).read_bytes(), before)
        approve.assert_not_called()

    def test_prior_single_site_guard_blocks_new_batch_post_when_remote_site_is_absent(self):
        server = SiteServer()
        profile = self.module.DiscoveryProfile.read(str(self.profile_path))
        self.module.reserve_site_attempt(profile, self.plan.sites[0].selection, "prior-single-site.json")
        status, report, _ = self.run_batch(server, mode="execute")
        self.assertEqual(status, 1)
        self.assertEqual(server.posts, [])
        self.assertTrue(report["manual_reconciliation_required"])
        self.assertIn("prior_attempt_requires_manual_reconciliation", report["issue_codes"])

    def test_batch_terminal_summary_and_progress_do_not_change_saved_reports_or_journal(self):
        server = SiteServer()
        status, report, _ = self.run_batch(server, mode="execute", use_cli=True, human=True)
        self.assertEqual(status, 0)
        self.assertIn("Site 3/30: VERIFIED", self.console)
        self.assertIn("Destination: https://destination.invalid", self.console)
        self.assertIn("Operation: Sites execute; total Sites: 30; preflight: PASSED", self.console)
        self.assertIn("Created: 30 | Verified: 30 | Existing: 0 | Failed: 0 | Pending: 0", self.console)
        self.assertEqual(report["plan_sha256"], self.plan.digest)
        self.assertEqual(len(report["dependency_order"]), 30)
        journal = json.loads((self.output / report["journal_file"]).read_text())
        self.assertEqual(journal["binding"]["plan"], self.plan.binding)
        self.assertEqual(journal["sites"][self.plan.sites[0].selection.reference]["destination_identity"],
                         server.sites[self.plan.sites[0].selection.name]["ormID"])

    def test_cancelled_batch_prints_compact_result_and_does_not_create(self):
        status, report, _ = self.run_batch(SiteServer(), mode="execute", use_cli=True, human=True, approval=False)
        self.assertEqual(status, 1)
        self.assertEqual(report["create_attempts"], 0)
        self.assertFalse(report["configuration_writes_authorized"])
        self.assertFalse(list(self.output.glob("*.journal.json")))
        self.assertIn("Cancelled; no new Sites created.", self.console)
        self.assertIn("Issue code: batch_operator_declined_or_no_terminal", self.console)

    def test_authorization_accepts_yes_no_and_enter_and_reprompts_without_echoing_invalid_input(self):
        for answer, expected in (("y", True), ("yes", True), ("Y", True), ("YES", True), ("", True),
                                 ("n", False), ("no", False), ("N", False), ("NO", False)):
            with self.subTest(answer=answer):
                out = io.StringIO()
                with (
                    patch.object(self.module.sys.stdin, "isatty", return_value=True), redirect_stdout(out),
                    patch.object(out, "isatty", return_value=True),
                    patch("builtins.input", return_value=answer) as prompt,
                ):
                    self.assertEqual(self.module._approval("https://destination.invalid", 30, self.plan.digest), expected)
                prompt.assert_called_once_with("Proceed with creating 30 Sites? [Y/n] (default Yes): ")
                self.assertNotIn(self.plan.digest[:12], out.getvalue())
        out = io.StringIO()
        with (
            patch.object(self.module.sys.stdin, "isatty", return_value=True), redirect_stdout(out),
            patch.object(out, "isatty", return_value=True),
            patch("builtins.input", side_effect=["private-invalid\x1b[A", "yes"]) as prompt,
        ):
            self.assertTrue(self.module._approval("https://destination.invalid", 30, self.plan.digest))
        self.assertEqual(prompt.call_count, 2)
        self.assertIn("Please enter Y/Yes or N/No.", out.getvalue())
        self.assertNotIn("private-invalid", out.getvalue())
        self.assertNotIn("\x1b", out.getvalue())

    def test_authorization_noninteractive_eof_interrupted_and_unusable_terminal_fail_closed(self):
        for stdin_tty, stdout_tty, error in (
            (False, True, None), (True, False, None),
            (True, True, EOFError()), (True, True, KeyboardInterrupt()), (True, True, OSError()),
            (True, True, ValueError()),
        ):
            with self.subTest(stdin_tty=stdin_tty, stdout_tty=stdout_tty, error=type(error).__name__):
                out, err = io.StringIO(), io.StringIO()
                with (
                    patch.object(self.module.sys.stdin, "isatty", return_value=stdin_tty),
                    redirect_stdout(out), redirect_stderr(err),
                    patch.object(out, "isatty", return_value=stdout_tty),
                    patch("builtins.input", side_effect=error) as prompt,
                ):
                    self.assertFalse(self.module._approval("https://destination.invalid", 30, self.plan.digest))
                if not stdin_tty or not stdout_tty:
                    prompt.assert_not_called()
                self.assertIn("Authorization cancelled", err.getvalue())

    def test_invalid_then_yes_keeps_one_authenticated_session_and_no_authentication_restart(self):
        server = SiteServer()
        original_approval = self.module._approval
        def approval(origin, count, digest):
            with patch.object(self.module.sys.stdout, "isatty", return_value=True):
                return original_approval(origin, count, digest)
        with (
            patch.object(self.module.sys.stdin, "isatty", return_value=True),
            patch("builtins.input", side_effect=["invalid", "yes"]) as prompt,
            patch.object(self.module, "_approval", side_effect=approval),
        ):
            status, report, _ = self.run_batch(server, mode="execute", approval=None)
        self.assertEqual(status, 0)
        self.assertEqual(prompt.call_count, 2)
        self.assertEqual(sum(path == "/mgmt/system/user/login" for _, path in server.calls), 1)
        self.assertEqual(len(server.posts), 30)
        self.assertEqual(report["counts"]["verified"], 30)

    def test_dry_run_terminal_output_never_requests_authorization(self):
        server = SiteServer()
        status, report, approve = self.run_batch(server, use_cli=True, human=True)
        self.assertEqual(status, 0)
        approve.assert_not_called()
        self.assertEqual(server.posts, [])
        self.assertIn("Operation: Sites dry-run; total Sites: 30; preflight: PASSED", self.console)
        self.assertIn("Created: 0 | Verified: 0 | Existing: 0 | Failed: 0 | Pending: 30", self.console)
        self.assertEqual(report["create_attempts"], 0)

    def test_invalid_preflight_never_reaches_default_yes_authorization(self):
        server = SiteServer()
        server.invalid_lookup = True
        status, report, approve = self.run_batch(server, mode="execute", use_cli=True, human=True)
        self.assertEqual(status, 1)
        approve.assert_not_called()
        self.assertEqual(server.posts, [])
        self.assertIn("preflight: FAILED", self.console)
        self.assertIn("Issue code: http_error", self.console)
        self.assertEqual(report["create_attempts"], 0)

    def test_batch_input_errors_use_compact_text_or_launcher_envelope_without_full_report(self):
        self.source_path.unlink()
        for format_name in ("text", "json"):
            with self.subTest(format_name=format_name):
                out = io.StringIO()
                with redirect_stdout(out):
                    status = self.cli.main([
                        "--operation", "site-batch-dry-run", "--discovery-profile", str(self.profile_path),
                        "--credentials-file", str(self.credentials), "--input", str(self.source_path),
                        "--comparison", str(self.comparison_path), "--destination-snapshot", str(self.snapshot_path),
                        "--report-format", format_name,
                    ])
                self.assertNotEqual(status, 0)
                self.assertIn("input_unreadable", out.getvalue())
                if format_name == "json":
                    report = json.loads(out.getvalue())
                    self.assertEqual(report["operation"], "site-batch-migration")
                    self.assertEqual(report["status"], "error")
                    self.assertNotIn("dependency_order", report)
                else:
                    self.assertIn("Issue code:", out.getvalue())
                    self.assertIn("Sanitized report: unavailable", out.getvalue())
                    self.assertNotIn('"operation"', out.getvalue())

    def test_cancelled_resume_preserves_original_journal_and_never_repeats_a_post(self):
        server = SiteServer()
        server.fault_at, server.fault = 1, TimeoutError("private-timeout")
        _, report, _ = self.run_batch(server, mode="execute")
        path = self.output / report["journal_file"]
        before = path.read_bytes()
        server.fault_at = None
        status, _, _ = self.run_batch(server, mode="resume", use_cli=True, human=True, approval=False)
        self.assertEqual(status, 1)
        self.assertEqual(len(server.posts), 1)
        self.assertEqual(path.read_bytes(), before)

    def test_tty_authorization_supports_arrow_and_backspace_editing(self):
        if self.module.os.name != "posix":
            self.skipTest("Real POSIX TTY/readline editing requires Linux/macOS.")
        import errno
        import os
        import pty
        import select
        import subprocess
        import sys

        master, slave = pty.openpty()
        process = subprocess.Popen([
            sys.executable, "-S", "-B", "-u", "-c",
            "from cc_vision_import.site_migration import _approval; "
            "print('APPROVED', _approval('https://destination.invalid', 30, 'protected-list-digest'))",
        ], stdin=slave, stdout=slave, stderr=slave)
        os.close(slave)
        def read_until(marker):
            output = b""
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline and marker not in output:
                if select.select([master], [], [], 0.1)[0]:
                    try:
                        chunk = os.read(master, 4096)
                    except OSError as error:
                        if error.errno != errno.EIO:
                            raise
                        break
                    if not chunk:
                        break
                    output += chunk
            self.assertIn(marker, output)
            return output
        try:
            read_until(b"(default Yes): ")
            os.write(master, b"nx\x1b[D\x7fY\x1b[C\x7f\n")
            output = read_until(b"APPROVED True")
            self.assertNotIn(b"^[[D", output)
            self.assertNotIn(b"^[[C", output)
            self.assertNotIn(b"^?", output)
            self.assertEqual(process.wait(timeout=10), 0)
        finally:
            os.close(master)
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=10)

import importlib
import io
import json
import ssl
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import Mock, patch

from offline_support import OfflineTestCase
from test_backup_inventory import envelope
from test_site_comparison import site
from test_site_migration import ServerConnection, SiteServer


class MigrationTests(OfflineTestCase):
    def setUp(self):
        super().setUp()
        self.module = importlib.import_module("cc_vision_import.migration")
        self.discovery = importlib.import_module("cc_vision_import.destination_discovery")
        self.http = importlib.import_module("cc_vision_import.http_backend")
        self.transport = importlib.import_module("cc_vision_import.transport")
        self.cli = importlib.import_module("cc_vision_import.master_cli")
        self.backup = self.directory / "unrelated-customer-backup"
        self.backup.mkdir()
        self.output = self.directory / "reports"
        self.output.mkdir()
        self.profile = self.directory / "profile.json"
        self.profile.write_text(json.dumps({
            "destination": {"name": "destination", "base_url": "https://destination.invalid"},
            "tls": {"verify": True}, "output_directory": str(self.output),
        }))
        self.credentials = self.directory / "credentials.json"
        root = site("private-source-root", "private-customer-root")
        for branch in range(3):
            parent = site(f"private-parent-{branch}", f"private-parent-name-{branch}")
            root["children"].append(parent)
            for child in range(branch):
                parent["children"].append(site(f"private-child-{branch}-{child}", f"private-child-name-{branch}-{child}"))
        self.source = envelope("vision-organization-tree", "tree", root)
        self.source_path = self.backup / "arbitrary-file.json"
        self.source_path.write_text(json.dumps(self.source))
        self.server = SiteServer(root_name="Tenant Destination")
        self.server.post_response = {"status": "ok"}
        self.server.split_parent_namespaces = True
        self.context = ssl.create_default_context()

    def run_engine(self, mode="dry-run", approval=True, root_approval=True, cli=False, original_inputs=None):
        factory = Mock(side_effect=lambda *args, **kwargs: ServerConnection(self.server))
        approve, approve_root = Mock(return_value=approval), Mock(return_value=root_approval)
        out, err = io.StringIO(), io.StringIO()
        with (
            patch.object(self.http.http.client, "HTTPSConnection", factory),
            patch.object(self.discovery, "_read_credentials", return_value={
                "username": "private-user", "password": "private-password",
            }),
            patch.object(self.transport.TransportConfig, "tls_context", return_value=self.context),
            redirect_stdout(out), redirect_stderr(err),
        ):
            if cli:
                with patch.object(self.module, "_root_approval", approve_root):
                    status = self.cli.main([
                        "--operation", "migration-" + mode, "--backup", str(self.backup),
                        "--discovery-profile", str(self.profile), "--credentials-file", str(self.credentials),
                        "--operation-delay", "0", "--readback-interval", "0", "--report-format", "json",
                        *([part for option, value in zip(
                            ("--input", "--comparison", "--destination-snapshot"), original_inputs,
                        ) for part in (option, str(value))] if original_inputs else []),
                    ])
                result = json.loads(out.getvalue())
                report = json.loads((self.output / result["report_file"]).read_text())
            else:
                if mode == "recovery-assess":
                    from cc_vision_import.migration_recovery import run_recovery_assessment

                    report, status = run_recovery_assessment(
                        str(self.profile), str(self.credentials), str(self.backup), terminal=True,
                        **dict(zip(("source_path", "comparison_path", "snapshot_path"),
                                   map(str, original_inputs))) if original_inputs else {},
                    )
                else:
                    report, status = self.module.run_migration(
                        str(self.profile), str(self.credentials), str(self.backup), mode=mode,
                        approve=approve, approve_root=approve_root, operation_delay=0,
                        readback_interval=0, terminal=True,
                    )
        return report, int(status), approve, approve_root, out.getvalue(), factory

    def test_backup_driven_plan_and_execution_use_all_discovered_sites_and_ids(self):
        plan_report, status, approve, root, out, _ = self.run_engine()
        count = next(item for item in plan_report["modules"] if item["domain"] == "organization-tree")["sites"]
        self.assertEqual(status, 0)
        self.assertEqual(plan_report["plan_status"], "READY")
        self.assertEqual(plan_report["counts"]["total"], count)
        self.assertEqual(self.server.posts, [])
        approve.assert_not_called()
        root.assert_called_once()
        report, status, approval, root, out, _ = self.run_engine("execute")
        self.assertEqual(status, 0)
        self.assertEqual(report["migration_status"], "COMPLETED")
        self.assertEqual(report["counts"]["verified"], count)
        self.assertEqual(len(self.server.posts), count)
        self.assertEqual(len({row["name"] for row in self.server.posts}), count)
        self.assertTrue(all(not row["parentOrmID"].startswith(("private-", "tree:")) for row in self.server.posts))
        approval.assert_called_once()
        root.assert_not_called()
        self.assertNotIn("private-", out)
        self.assertNotIn("ordered_sites", out)
        self.assertNotIn("backup_sha256", out)
        self.assertNotIn(plan_report["inventory"]["backup_sha256"], out)

    def test_populated_unsupported_domains_prevent_full_completion(self):
        (self.backup / "tasks-custom.json").write_text(json.dumps(envelope("vision-scheduler", "tasks", [{}, {}])))
        report, status, _, _, _, _ = self.run_engine("execute")
        self.assertEqual(status, 1)
        self.assertEqual(report["migration_status"], "PARTIAL")
        scheduler = next(item for item in report["modules"] if item["domain"] == "scheduler")
        self.assertEqual(scheduler["records"], 2)
        self.assertEqual(scheduler["migration_status"], "BLOCKED")
        self.assertEqual(scheduler["verified_records"], 0)
        self.assertIn("scheduler_destination_write_and_completion_contract_unqualified", scheduler["issue_codes"])

    def test_resume_reconciles_historical_attempt_without_duplicate_post(self):
        self.server.fault_at = 2
        self.server.fault = TimeoutError("private-network-data")
        report, status, _, _, _, _ = self.run_engine("execute")
        self.assertEqual(status, 1)
        original = json.loads((self.output / report["journal_file"]).read_text())
        self.assertEqual(len(self.server.posts), self.server.fault_at)
        self.server.fault_at = None
        report, status, _, _, _, _ = self.run_engine("resume")
        self.assertEqual(status, 0)
        self.assertEqual(report["migration_status"], "COMPLETED")
        self.assertEqual(len(self.server.posts), report["counts"]["total"])
        self.assertEqual(len({row["name"] for row in self.server.posts}), len(self.server.posts))
        final = json.loads((self.output / report["journal_file"]).read_text())
        self.assertEqual(original["binding"], final["binding"])

    def test_cancellation_does_not_write_and_resume_retains_the_bound_plan(self):
        report, status, _, _, _, _ = self.run_engine("execute", approval=False)
        self.assertEqual(status, 1)
        self.assertEqual(self.server.posts, [])
        original = (self.output / report["journal_file"]).read_bytes()
        report, status, _, _, _, _ = self.run_engine("resume")
        self.assertEqual(status, 0)
        self.assertEqual(json.loads(original)["binding"],
                         json.loads((self.output / report["journal_file"]).read_bytes())["binding"])

    def test_root_review_and_lab_reset_fail_closed_without_replaying_attempts(self):
        report, status, _, _, _, _ = self.run_engine(root_approval=False)
        self.assertEqual(status, 1)
        self.assertIn("root_mapping_review_required", report["issue_codes"])
        self.assertEqual(self.server.posts, [])
        report, _, _, _, _, _ = self.run_engine()
        original = (self.output / report["journal_file"]).read_bytes()
        report, status, approval, _, _, factory = self.run_engine("lab-reset")
        self.assertEqual(status, 1)
        self.assertIn("lab_delete_or_definitive_absence_contract_unqualified_use_reconcile", report["issue_codes"])
        self.assertEqual((self.output / report["journal_file"]).read_bytes(), original)
        self.assertEqual(self.server.posts, [])
        factory.assert_not_called()
        approval.assert_not_called()

    def test_different_backups_and_destinations_cannot_reuse_full_migration_state(self):
        report, _, _, _, _, _ = self.run_engine()
        original = report["journal_file"]
        (self.backup / "new-domain.json").write_text(json.dumps(envelope("vision-ldap-permissions", "objects", [])))
        changed, status, _, _, _, _ = self.run_engine("resume")
        self.assertEqual(status, 1)
        self.assertNotEqual(changed["journal_file"], original)
        self.assertIn("backup_state_missing_use_original_dry_run_or_historical_site_reconcile", changed["issue_codes"])
        profile = json.loads(self.profile.read_text())
        profile["destination"]["base_url"] = "https://another-destination.invalid"
        self.profile.write_text(json.dumps(profile))
        other, status, _, _, _, _ = self.run_engine("resume")
        self.assertEqual(status, 1)
        self.assertNotEqual(other["journal_file"], changed["journal_file"])
        self.assertEqual(self.server.posts, [])

    def test_empty_scope_and_noninteractive_cli_never_authorize_writes(self):
        self.source = envelope("vision-organization-tree", "tree", [])
        self.source_path.write_text(json.dumps(self.source))
        report, status, approve, root, _, _ = self.run_engine("execute")
        self.assertEqual(status, 0)
        self.assertEqual(report["migration_status"], "COMPLETED")
        self.assertEqual(report["counts"]["total"], 0)
        self.assertFalse(report["configuration_writes_authorized"])
        self.assertEqual(self.server.posts, [])
        approve.assert_not_called()
        root.assert_not_called()

    def test_compact_cli_does_not_emit_inventory_or_bindings(self):
        report, status, _, _, out, _ = self.run_engine(cli=True)
        self.assertEqual(status, 0)
        envelope_result = json.loads(out)
        self.assertNotIn("inventory", envelope_result)
        self.assertNotIn("modules", envelope_result)
        self.assertNotIn("private-", out)
        self.assertNotIn("sha256", out)
        saved = self.output / report["report_file"]
        self.assertTrue(saved.is_file())
        self.assertIn("inventory", json.loads(saved.read_text()))

    def test_root_review_reprompts_and_eof_or_missing_tty_rejects(self):
        with patch.object(self.module.sys.stdin, "isatty", return_value=False):
            self.assertFalse(self.module._root_approval("source", "destination"))
        with (
            patch.object(self.module.sys.stdin, "isatty", return_value=True),
            patch.object(self.module.sys.stdout, "isatty", return_value=True),
            patch("builtins.input", side_effect=["invalid", "yes"]),
        ):
            self.assertTrue(self.module._root_approval("source", "destination"))
        with (
            patch.object(self.module.sys.stdin, "isatty", return_value=True),
            patch.object(self.module.sys.stdout, "isatty", return_value=True),
            patch("builtins.input", side_effect=EOFError),
        ):
            self.assertFalse(self.module._root_approval("source", "destination"))

    def test_destination_root_identity_change_blocks_before_any_post(self):
        original, _, _, _, _, _ = self.run_engine()
        self.server.root_id = "replacement-destination-root"
        self.server.sites[self.server.root_name]["ormID"] = self.server.root_id
        self.server.verified = {self.server.root_id}
        report, status, _, _, _, _ = self.run_engine("execute")
        self.assertEqual(status, 1)
        self.assertIn("backup_destination_root_identity_changed", report["issue_codes"])
        self.assertEqual(original["journal_file"], report["journal_file"])
        self.assertEqual(self.server.posts, [])

    def test_status_checks_historical_identities_without_changing_journal(self):
        report, _, _, _, _, _ = self.run_engine("execute")
        full_path = self.output / report["journal_file"]
        site_path = self.output / report["module_reports"]["organization-tree"]
        site_report = json.loads(site_path.read_text())
        journal_path = self.output / site_report["journal_file"]
        original = journal_path.read_bytes()
        full_original = full_path.read_bytes()
        report, status, _, _, _, _ = self.run_engine("status")
        self.assertEqual(status, 0)
        self.assertEqual(report["counts"]["created"], report["counts"]["total"])
        self.assertEqual(journal_path.read_bytes(), original)
        self.assertEqual(full_path.read_bytes(), full_original)

    def test_root_only_devices_and_noncanonical_detail_files_stay_read_only(self):
        from test_device_migration import DeviceServer

        root = self.source["tree"]
        root["children"] = []
        models = ("DefensePro", "Alteon")
        for index, model in enumerate(models):
            root["children"].append({
                "meIdentifier": {"managedElementClass": "com.radware.insite.model.device.Device",
                                 "managedElementID": f"private-tree-device-{index}"},
                "name": f"private-device-{index}", "type": model,
                "managementIp": f"192.0.2.{index + 10}", "children": [],
            })
        self.source_path.write_text(json.dumps(self.source))
        lookup_ips = ("192.0.2.10", "192.0.2.253")
        for index, ip in enumerate(lookup_ips):
            detail = {"ormID": f"private-api-device-{index}",
                      "name": "private-device-0" if index == 0 else "private-orphan",
                      "type": models[0], "deviceSetup": {"deviceAccess": {"managementIp": ip}}}
            payload = envelope("vision-controller-object-lookup", "objects", [detail])
            payload["request"]["target"] = ip
            (self.backup / f"noncanonical-lookup-{index}.json").write_text(json.dumps(payload))
            if index == 0:
                access = envelope("vision-device-access", "objects", [{
                    "ormID": detail["ormID"], "deviceAccess": detail["deviceSetup"]["deviceAccess"],
                }])
                access["request"]["target"] = ip
                (self.backup / "custom-access.json").write_text(json.dumps(access))
        self.server = DeviceServer()
        report, status, approve, _, out, _ = self.run_engine("execute")
        self.assertEqual(status, 1)
        self.assertEqual(report["migration_status"], "BLOCKED")
        self.assertEqual(report["device_inventory"]["organization_devices"], len(models))
        self.assertEqual(report["device_inventory"]["controller_object_records"], len(lookup_ips))
        self.assertEqual(report["device_inventory"]["device_access_records"],
                         len(tuple(self.backup.glob("custom-access.json"))))
        self.assertEqual(len(report["device_inventory"]["unmatched_controller_records"]), len(lookup_ips) - 1)
        self.assertEqual(self.server.posts, [])
        approve.assert_not_called()
        self.assertNotIn("private-api-device", out)

    def protected_history(self):
        return {path: path.read_bytes() for path in self.output.iterdir()
                if path.name.endswith(".journal.json") or path.name.startswith(".ccv-site-attempt-")}

    def test_recovery_existing_attempts_are_qualified_without_changing_history(self):
        report, _, _, _, _, _ = self.run_engine("execute")
        history = self.protected_history()
        posts = len(self.server.posts)
        self.server.calls.clear()
        recovered, status, approval, root, out, _ = self.run_engine("recovery-assess")
        self.assertEqual(status, 1)
        self.assertEqual(recovered["counts"]["attempted"], report["counts"]["total"])
        self.assertEqual(recovered["counts"]["confirmed_existing"], report["counts"]["total"])
        self.assertEqual(recovered["counts"]["confirmed_absent"], 0)
        self.assertFalse(recovered["reset_eligible"])
        self.assertEqual(history, self.protected_history())
        self.assertEqual(posts, len(self.server.posts))
        self.assertTrue(all(method == "GET" or path == "/mgmt/system/user/login"
                            for method, path in self.server.calls))
        self.assertEqual(recovered["bindings"]["backup"], "FULL_BACKUP_MATCHED")
        self.assertNotIn("private-", out)
        self.assertNotIn("ormID", out)
        self.assertNotIn("objects", out)
        saved = (self.output / recovered["report_file"]).read_text()
        self.assertNotIn("private-", saved)
        self.assertNotIn("destination-site-", saved)
        self.assertIn("required_evidence", saved)
        approval.assert_not_called()
        root.assert_not_called()

    def test_recovery_empty_tree_and_http_misses_are_not_confirmed_absence(self):
        original, _, _, _, _, _ = self.run_engine("execute")
        count = original["counts"]["total"]
        history = self.protected_history()
        self.server.sites = {self.server.root_name: self.server.sites[self.server.root_name]}
        self.server.calls.clear()
        report, status, _, _, _, _ = self.run_engine("recovery-assess")
        self.assertEqual(status, 1)
        self.assertEqual(report["counts"]["unresolved"], count)
        self.assertEqual(report["counts"]["confirmed_absent"], 0)
        self.assertEqual(report["organization_tree"]["observed_sites"], 0)
        self.assertEqual(report["organization_tree"]["completeness"], "UNQUALIFIED")
        self.assertEqual(sum("/site/byid/" in path for _, path in self.server.calls), count)
        for row in report["objects"]:
            self.assertTrue(row["absence_candidate"])
            self.assertEqual(row["by_name"]["http_status"], 400)
            self.assertEqual(row["by_id_checks"][0]["http_status"], 404)
        self.assertIn("organization_enumeration_completeness_unqualified", report["issue_codes"])
        self.assertIn("site_by_id_absence_contract_unqualified", report["issue_codes"])
        self.assertIn("prior_operation_settlement_contract_unqualified", report["issue_codes"])
        self.assertEqual(history, self.protected_history())
        fresh, _, _, _, _, _ = self.run_engine()
        self.assertIn("prior_attempt_requires_manual_reconciliation", fresh["issue_codes"])
        self.assertEqual(len(self.server.posts), count)

    def test_recovery_unknown_identity_and_unsettled_post_remain_indeterminate(self):
        self.server.fault_at = 2
        self.server.fault = TimeoutError("private-error")
        self.run_engine("execute")
        self.server.fault_at = None
        self.server.sites = {self.server.root_name: self.server.sites[self.server.root_name]}
        history = self.protected_history()
        report, _, _, _, _, _ = self.run_engine("recovery-assess")
        self.assertEqual(report["counts"]["attempted"], len(self.server.posts))
        self.assertEqual(report["counts"]["indeterminate"], 1)
        self.assertIn("historical_destination_identity_unknown", report["issue_codes"])
        self.assertIn("historical_operation_indeterminate", report["issue_codes"])
        self.assertFalse(report["reset_eligible"])
        self.assertEqual(history, self.protected_history())

    def test_recovery_mismatched_root_and_malformed_tree_block_without_rewrites(self):
        self.run_engine("execute")
        history = self.protected_history()
        self.server.sites[self.server.root_name]["ormID"] = "replacement-root"
        report, _, _, _, _, _ = self.run_engine("recovery-assess")
        self.assertIn("recovery_destination_root_identity_changed", report["issue_codes"])
        self.server.sites[self.server.root_name]["ormID"] = self.server.root_id
        with patch.object(self.server, "tree", return_value={
            "meIdentifier": {"managedElementClass": "com.radware.insite.model.device.Site",
                             "managedElementID": self.server.root_id}, "name": self.server.root_name,
        }):
            report, _, _, _, _, _ = self.run_engine("recovery-assess")
        self.assertIn("tree_identity_missing", report["issue_codes"])
        self.assertEqual(report["preflight_status"], "BLOCKED")
        self.assertEqual(history, self.protected_history())

    def test_recovery_unexpected_children_and_devices_are_reported(self):
        self.run_engine("execute")
        self.server.seed("unrelated-site", self.server.root_id)
        tree = self.server.tree()
        tree["children"].append({
            "name": "private-device", "meIdentifier": {
                "managedElementClass": "com.radware.insite.model.device.Device",
                "managedElementID": "private-device-id",
            }, "children": [],
        })
        with patch.object(self.server, "tree", return_value=tree):
            report, _, _, _, _, _ = self.run_engine("recovery-assess")
        self.assertEqual(report["organization_tree"]["observed_devices"], 1)
        self.assertEqual(report["organization_tree"]["unexpected_children"], 2)
        self.assertIn("recovery_unexpected_children_or_devices", report["issue_codes"])

    def test_recovery_guard_binding_mismatch_and_missing_reports_fail_closed(self):
        self.run_engine("execute")
        guard = next(self.output.glob(".ccv-site-attempt-*.json"))
        value = json.loads(guard.read_bytes())
        evidence_path = self.output / value["report_file"]
        evidence = json.loads(evidence_path.read_bytes())
        evidence["plan_sha256"] = "another-plan"
        evidence_path.write_text(json.dumps(evidence))
        report, _, _, _, _, _ = self.run_engine("recovery-assess")
        self.assertIn("recovery_guard_original_plan_binding_mismatch", report["issue_codes"])
        value["report_file"] = "../private-escape.json"
        guard.write_text(json.dumps(value))
        history = self.protected_history()
        report, _, _, _, _, _ = self.run_engine("recovery-assess")
        self.assertIn("recovery_guard_report_path_invalid", report["issue_codes"])
        self.assertEqual(history, self.protected_history())
        value["report_file"] = "missing-report.json"
        guard.write_text(json.dumps(value))
        report, _, _, _, _, _ = self.run_engine("recovery-assess")
        self.assertIn("recovery_guard_evidence_io_failure", report["issue_codes"])

    def test_recovery_missing_original_state_does_not_initialize_or_scan_other_backups(self):
        self.server.fault_at = 1
        self.server.fault = TimeoutError("private-error")
        self.run_engine("execute")
        self.server.fault_at = None
        history = self.protected_history()
        self.source["tree"]["name"] = "another-source-root"
        for branch in self.source["tree"]["children"]:
            branch["name"] = "another-" + branch["name"]
            for child in branch["children"]:
                child["name"] = "another-" + child["name"]
        self.source_path.write_text(json.dumps(self.source))
        report, _, _, _, _, factory = self.run_engine("recovery-assess")
        self.assertIn("recovery_original_plan_missing_supply_bound_inputs", report["issue_codes"])
        self.assertEqual(history, self.protected_history())
        factory.assert_not_called()
        fresh, _, _, _, _, _ = self.run_engine()
        self.assertEqual(fresh["plan_status"], "READY")
        for path, value in history.items():
            self.assertEqual(path.read_bytes(), value)

    def test_recovery_compact_cli_uses_protected_bound_state(self):
        self.run_engine("execute")
        history = self.protected_history()
        report, status, _, _, out, _ = self.run_engine("recovery-assess", cli=True)
        self.assertEqual(status, 1)
        self.assertEqual(json.loads(out)["operation"], "migration-recovery-assess")
        self.assertNotIn("objects", out)
        self.assertNotIn("private-", out)
        self.assertEqual(report["preflight_status"], "ASSESSED_RESET_BLOCKED")
        self.assertEqual(history, self.protected_history())

    def test_recovery_explicit_original_plan_handles_legacy_source_only_binding(self):
        report, _, _, _, _, _ = self.run_engine("execute")
        state_path = self.output / report["journal_file"]
        state = json.loads(state_path.read_bytes())
        inputs = (self.source_path, self.output / state["comparison_file"], self.output / state["snapshot_file"])
        archived = state_path.with_name("retained-original-backup-state.json")
        state_path.rename(archived)
        history = self.protected_history()
        report, _, _, _, _, _ = self.run_engine("recovery-assess", cli=True, original_inputs=inputs)
        self.assertEqual(report["bindings"]["backup"], "ORGANIZATION_SOURCE_ONLY")
        self.assertIn("historical_full_backup_binding_unrecorded", report["issue_codes"])
        self.assertEqual(report["counts"]["confirmed_existing"], len(self.server.posts))
        self.assertEqual(history, self.protected_history())
        self.assertFalse(state_path.exists())
        self.assertEqual(json.loads(archived.read_bytes()), state)

    def test_recovery_explicit_inputs_cannot_bind_another_backup_or_origin(self):
        original, _, _, _, _, _ = self.run_engine("execute")
        state = json.loads((self.output / original["journal_file"]).read_bytes())
        original_source = self.directory / "retained-original-source.json"
        original_source.write_bytes(self.source_path.read_bytes())
        inputs = (original_source, self.output / state["comparison_file"], self.output / state["snapshot_file"])
        self.source["tree"]["children"].pop()
        self.source_path.write_text(json.dumps(self.source))
        report, _, _, _, _, factory = self.run_engine("recovery-assess", original_inputs=inputs)
        self.assertIn("recovery_original_backup_binding_mismatch", report["issue_codes"])
        factory.assert_not_called()
        self.source_path.write_bytes(original_source.read_bytes())
        profile = json.loads(self.profile.read_bytes())
        profile["destination"]["base_url"] = "https://another-controller.invalid"
        self.profile.write_text(json.dumps(profile))
        report, _, _, _, _, factory = self.run_engine("recovery-assess", original_inputs=inputs)
        self.assertIn("recovery_original_site_journal_missing", report["issue_codes"])
        factory.assert_not_called()

    def test_recovery_wrong_parent_and_disagreeing_by_id_are_unresolved(self):
        original, _, _, _, _, _ = self.run_engine("execute")
        history = self.protected_history()
        self.server.wrong_readback_parent = True
        report, _, _, _, _, _ = self.run_engine("recovery-assess")
        self.assertEqual(report["counts"]["unresolved"], original["counts"]["total"])
        self.assertIn("recovery_parent_identity_mismatch", report["issue_codes"])
        self.server.wrong_readback_parent = False
        original_response = self.server.respond

        def respond(request):
            response = original_response(request)
            if "/site/byid/" in request[1]:
                from test_http_backend import MemoryResponse

                return MemoryResponse(200, json.dumps({
                    "name": "unrelated-object", "type": "Site", "ormID": "unrelated-id",
                }).encode(), [("Content-Type", "application/json")])
            return response

        with patch.object(self.server, "respond", side_effect=respond):
            report, _, _, _, _, _ = self.run_engine("recovery-assess")
        self.assertEqual(report["counts"]["confirmed_existing"], 0)
        self.assertIn("site_identity_missing_or_ambiguous", report["issue_codes"])
        self.assertEqual(history, self.protected_history())

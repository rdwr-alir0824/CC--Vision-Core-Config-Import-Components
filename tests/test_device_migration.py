import copy
import importlib
import io
import json
import os
from contextlib import redirect_stderr, redirect_stdout
from urllib.parse import unquote
from unittest.mock import Mock, patch

import test_site_migration
from offline_support import OfflineTestCase
from test_http_backend import MemoryResponse


class DeviceServer(test_site_migration.SiteServer):
    def __init__(self):
        super().__init__()
        self.devices = {}
        self.lookup_fault = None
        self.omit_device_tree = False

    def tree(self):
        root = super().tree()
        rows = importlib.import_module("cc_vision_import.vision_tree_preview")._tree_rows(root)
        for item in self.devices.values():
            if self.omit_device_tree:
                continue
            parents = [row for row in rows if row["meIdentifier"]["managedElementID"] == item["parentOrmID"]]
            if parents:
                parents[0]["children"].append({
                    "meIdentifier": {"managedElementID": item["ormID"],
                                     "managedElementClass": "com.radware.insite.model.device.Device"},
                    "name": item["name"], "type": item["type"],
                    "managementIp": item["deviceSetup"]["deviceAccess"]["managementIp"],
                    "parentOrmID": item["parentOrmID"], "children": [],
                })
        return root

    def respond(self, request):
        method, path, _, _ = request
        if method == "GET" and "/device/byip/" in path:
            self.calls.append((method, path))
            if isinstance(self.lookup_fault, BaseException):
                raise self.lookup_fault
            if self.lookup_fault is not None:
                status, payload = self.lookup_fault
            else:
                payload = self.devices.get(unquote(path.rsplit("/", 1)[-1]))
                status, payload = (404, {"status": "error"}) if payload is None else (200, payload)
            return MemoryResponse(status, json.dumps(payload).encode(), [("Content-Type", "application/json")])
        return super().respond(request)


class DeviceMigrationTests(OfflineTestCase):
    def setUp(self):
        super().setUp()
        self.fixture = test_site_migration.SiteMigrationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        f = self.fixture
        self.module = importlib.import_module("cc_vision_import.device_migration")
        self.backup = f.directory / "backup"
        (self.backup / "organization-tree").mkdir(parents=True)
        f.source_path = self.backup / "organization-tree" / "tree.json"
        for folder in ("controller-objects", "device-access"):
            (self.backup / folder).mkdir()
        sites = importlib.import_module("cc_vision_import.vision_tree_preview")._tree_rows(f.source["tree"])[1:]
        self.devices = []
        for index in range(35):
            parent = sites[index % len(sites)]
            device = {
                "meIdentifier": {"managedElementID": f"private-tree-device-{index}",
                                 "managedElementClass": "com.radware.insite.model.device.Device"},
                "name": f"private-device-{index}", "type": "Alteon", "managementIp": f"192.0.2.{index + 1}",
                "parentOrmID": parent["meIdentifier"]["managedElementID"], "children": [],
            }
            parent["children"].append(device)
            self.devices.append((device, parent))
        for index in range(36):
            address, name = f"192.0.2.{index + 1}", f"private-device-{index}"
            access = {"managementIp": address, "snmpReadCommunity": "private-device-secret"}
            envelope = {
                "schema_version": 1, "domain": "vision-controller-object-lookup",
                "source": copy.deepcopy(f.source["source"]),
                "request": {"method": "GET", "path_template": "/mgmt/system/config/tree/device/byip/{ip}",
                            "target": address},
                "objects": [{"ormID": f"private-detail-device-{index}", "name": name, "type": "Alteon",
                             "deviceSetup": {"deviceAccess": access}}],
            }
            filename = f"device-by-ip-{index + 1:03}.json"
            (self.backup / "controller-objects" / filename).write_text(json.dumps(envelope))
            envelope.update(domain="vision-device-access", objects=[{
                "ormID": f"private-detail-device-{index}", "deviceAccess": access,
            }])
            (self.backup / "device-access" / filename).write_text(json.dumps(envelope))
        f.save_inputs()
        f.plan = f.module.load_plan(str(f.source_path), str(f.comparison_path), str(f.snapshot_path))
        self.server = DeviceServer()

    def seed_sites(self):
        status, _, _ = self.fixture.run_batch(self.server, mode="execute")
        self.assertEqual(status, 0)
        self.server.calls.clear()
        self.addCleanup(self.assertEqual, len(self.server.posts), 30)

    def seed_device(self, index=None):
        if index is None:
            plan = self.module.load_device_plan(str(self.fixture.source_path), str(self.fixture.comparison_path),
                                                str(self.fixture.snapshot_path))
            index = next(index for index, (device, _) in enumerate(self.devices)
                         if device["managementIp"] == plan.devices[0].address)
        device, parent = self.devices[index]
        found = {
            "ormID": f"private-destination-device-{index}", "name": device["name"], "type": device["type"],
            "parentOrmID": self.server.sites[parent["name"]]["ormID"],
            "deviceSetup": {"deviceAccess": {"managementIp": device["managementIp"], "password": "private-remote-secret"}},
        }
        self.server.devices[device["managementIp"]] = found
        return found

    def run_devices(self, mode="dry-run", *, cli=False, machine=False):
        f = self.fixture
        immutable = [*self.backup.rglob("*.json"), f.snapshot_path, f.comparison_path]
        before = {path: path.read_bytes() for path in immutable}
        site_journals = {path: path.read_bytes() for path in f.output.glob("ccv-sites-*.journal.json")}
        out, err = io.StringIO(), io.StringIO()
        with (
            patch.object(f.http.http.client, "HTTPSConnection", side_effect=lambda *a, **k: test_site_migration.ServerConnection(self.server)),
            patch.object(f.discovery, "_read_credentials", return_value={"username": "private-user", "password": "private-password"}),
            patch.object(f.transport.TransportConfig, "tls_context", return_value=f.context),
            patch.object(f.module, "_approval") as approval,
            redirect_stdout(out), redirect_stderr(err),
        ):
            arguments = [
                "--operation", "migration-dry-run" if mode == "preview" else "migration-status" if mode == "status"
                else "device-batch-" + mode,
                "--discovery-profile", str(f.profile_path), "--credentials-file", str(f.credentials),
                "--input", str(f.source_path), "--comparison", str(f.comparison_path),
                "--destination-snapshot", str(f.snapshot_path),
            ]
            if cli:
                status = f.cli.main([*arguments, *(["--report-format", "json"] if machine else [])])
                if machine:
                    envelope = json.loads(out.getvalue())
                    self.assertNotIn("devices", envelope)
                    self.assertNotIn("input_bindings", envelope)
                    report = json.loads((f.output / envelope["report_file"]).read_text())
                else:
                    report = json.loads(max(f.output.glob("ccv-devices-report-*.json"),
                                            key=lambda path: path.stat().st_mtime_ns).read_text())
            else:
                report, status = self.module.run_device_migration(
                    str(f.profile_path), str(f.credentials), str(f.source_path),
                    str(f.comparison_path), str(f.snapshot_path), mode=mode,
                )
            approval.assert_not_called()
        self.assertEqual(before, {path: path.read_bytes() for path in immutable})
        self.assertEqual(site_journals, {path: path.read_bytes() for path in site_journals})
        self.assertEqual(report, json.loads((f.output / report["report_file"]).read_text()))
        for marker in ("private-", "192.0.2.", "destination-site-", "destination-root-id"):
            self.assertNotIn(marker, json.dumps(report) + out.getvalue() + err.getvalue())
        self.assertFalse(report["configuration_writes_authorized"])
        self.assertFalse(report["execution_authorized"])
        self.assertEqual(report["create_attempts"], 0)
        self.assertFalse(any(method != "GET" and path != "/mgmt/system/user/login"
                             for method, path in self.server.calls))
        self.console = out.getvalue()
        return int(status), report

    def test_all_35_devices_keep_separate_36_record_inventories_and_destination_parents(self):
        self.seed_sites()
        status, report = self.run_devices(cli=True)
        self.assertEqual(status, 1)
        self.assertEqual(report["counts"]["total"], 35)
        self.assertEqual(report["counts"]["blocked"], 35)
        inventory = report["inventory"]
        self.assertEqual(inventory["controller_object_records"], 36)
        self.assertEqual(inventory["device_access_records"], 36)
        self.assertEqual(inventory["controller_minus_organization_record_count"], 1)
        self.assertEqual(len(inventory["unmatched_controller_records"]), 1)
        self.assertEqual(len(inventory["unmatched_access_records"]), 1)
        self.assertEqual(report["sites"]["verified"], 30)
        for row in report["devices"]:
            self.assertIsNotNone(row["controller_association"])
            self.assertIsNotNone(row["access_association"])
            self.assertGreater(row["unsupported_access_fields"], 0)
            self.assertEqual(row["issue_codes"], [self.module._CONTRACT_BLOCK])
        self.assertEqual(sum("/device/byip/" in path for _, path in self.server.calls), 35)
        self.assertNotIn("input_bindings", self.console)
        self.assertNotIn('"schema_version"', self.console)
        self.assertTrue(self.console.rstrip().endswith(str(self.fixture.output / report["report_file"])))
        self.assertEqual(list(self.fixture.output.glob("ccv-devices-*.journal.json")), [])

    def test_missing_site_journal_blocks_every_device_without_root_fallback(self):
        _, report = self.run_devices()
        self.assertEqual(report["counts"]["blocked"], 35)
        self.assertEqual(report["sites"]["verified"], 0)
        self.assertTrue(all("device_destination_parent_dependency_unresolved" in row["issue_codes"]
                            for row in report["devices"]))
        self.assertFalse(any("/device/" in path for _, path in self.server.calls))

    def test_verified_existing_device_is_not_fully_configured_or_updated(self):
        self.seed_sites()
        for index in range(35):
            self.seed_device(index)
        _, report = self.run_devices(mode="execute")
        self.assertEqual(report["counts"]["already_existing"], 35)
        self.assertEqual(report["fully_configured_devices"], 0)
        journal_path = self.fixture.output / report["journal_file"]
        journal = json.loads(journal_path.read_text())
        self.assertEqual(sum(entry["verified"] for entry in journal["devices"].values()), 35)
        self.assertTrue(all(entry["destination_identity"].startswith("private-destination-device-")
                            and entry["parent_identity"].startswith("destination-site-")
                            and entry["create_attempts"] == 0 for entry in journal["devices"].values()))
        if os.name == "posix":
            self.assertEqual(journal_path.stat().st_mode & 0o777, 0o600)
        _, resumed = self.run_devices(mode="resume")
        self.assertEqual(resumed["counts"]["already_existing"], 35)
        before_status = journal_path.read_bytes()
        _, report = self.run_devices(mode="status")
        self.assertEqual(report["counts"]["already_existing"], 35)
        self.assertEqual(journal_path.read_bytes(), before_status)

    def test_ip_alone_wrong_parent_type_or_tree_readback_never_qualifies(self):
        self.seed_sites()
        for fault in ("wrong_name", "wrong_type", "wrong_parent", "missing_identity", "tree_missing"):
            with self.subTest(fault=fault):
                found = self.seed_device()
                self.server.omit_device_tree = fault == "tree_missing"
                if fault == "wrong_name":
                    found["name"] = "private-wrong-name"
                elif fault == "wrong_type":
                    found["type"] = "private-wrong-type"
                elif fault == "wrong_parent":
                    found["parentOrmID"] = self.server.root_id
                elif fault == "missing_identity":
                    self.server.lookup_fault = (200, {key: value for key, value in found.items() if key != "ormID"})
                status, report = self.run_devices()
                self.assertEqual(status, 1)
                self.assertEqual(report["counts"]["verified"], 0)
                self.assertEqual(report["counts"]["failed"], 1)
                self.assertEqual(report["counts"]["pending"], 34)
                self.server.lookup_fault = None
                self.server.omit_device_tree = False

    def test_400_even_site_absence_wording_is_not_device_absence(self):
        self.seed_sites()
        self.server.lookup_fault = (400, {
            "status": "error", "message": "M_00734: There is no device with name private-device-0 configured in Cyber Controller.",
        })
        _, report = self.run_devices()
        self.assertEqual(report["http_status"], 400)
        self.assertEqual(report["counts"]["failed"], 1)
        self.assertEqual(report["counts"]["pending"], 34)

    def test_duplicate_source_ip_and_unmatched_associations_remain_classified(self):
        self.devices[1][0]["managementIp"] = self.devices[0][0]["managementIp"]
        self.fixture.save_inputs()
        _, report = self.run_devices()
        duplicates = [row for row in report["devices"] if "duplicate_source_device_ip" in row["issue_codes"]]
        self.assertEqual(len(duplicates), 2)
        self.assertFalse(report["inventory"]["cross_namespace_identity_bridge_verified"])
        self.assertGreater(len(report["inventory"]["unmatched_controller_records"]), 1)

    def test_duplicate_source_identity_and_access_association_are_not_guessed(self):
        self.devices[1][0]["meIdentifier"]["managedElementID"] = self.devices[0][0]["meIdentifier"]["managedElementID"]
        path = self.backup / "device-access" / "device-by-ip-001.json"
        (path.parent / "device-by-ip-999.json").write_bytes(path.read_bytes())
        self.fixture.save_inputs()
        _, report = self.run_devices()
        self.assertEqual(sum("duplicate_identity" in row["issue_codes"] for row in report["devices"]), 2)
        self.assertTrue(any("device_access_association_missing_or_ambiguous" in row["issue_codes"]
                            for row in report["devices"]))
        self.assertEqual(report["inventory"]["device_access_records"], 37)

    def test_interruption_persists_zero_attempts_and_resume_freshly_reconciles(self):
        self.seed_sites()
        self.server.lookup_fault = KeyboardInterrupt()
        _, report = self.run_devices("execute")
        self.assertIn("device_batch_interrupted", report["issue_codes"])
        self.assertEqual(report["counts"]["pending"], 34)
        self.server.lookup_fault = None
        self.seed_device()
        _, resumed = self.run_devices("resume")
        self.assertEqual(resumed["counts"]["already_existing"], 1)
        self.assertEqual(resumed["counts"]["blocked"], 34)
        self.assertEqual(resumed["counts"]["pending"], 0)

    def test_journal_rebinding_or_uncertain_attempt_cannot_be_bypassed(self):
        self.seed_sites()
        _, report = self.run_devices("execute")
        path = self.fixture.output / report["journal_file"]
        original = path.read_bytes()
        for mutation in ("binding", "attempt", "uncertain"):
            data = json.loads(original)
            if mutation == "binding":
                data["binding"]["origin"][1] = "private-other-origin"
            elif mutation == "attempt":
                next(iter(data["devices"].values()))["create_attempts"] = 1
            else:
                data["incomplete_operation"] = {"reference": "source:node-2"}
            path.write_text(json.dumps(data))
            modified = path.read_bytes()
            self.server.calls.clear()
            _, report = self.run_devices("resume")
            self.assertFalse(report["authenticated"])
            self.assertEqual(path.read_bytes(), modified)
            self.assertEqual(self.server.calls, [])
        path.write_bytes(original)

    def test_shared_origin_lock_blocks_devices_before_authentication(self):
        plan = self.module.load_device_plan(str(self.fixture.source_path), str(self.fixture.comparison_path),
                                            str(self.fixture.snapshot_path))
        profile = self.fixture.discovery.DiscoveryProfile.read(str(self.fixture.profile_path))
        _, _, lock = self.fixture.module._journal_context(profile, plan.sites)
        with self.fixture.module._origin_lock(lock):
            _, report = self.run_devices("execute")
        self.assertIn("batch_operation_already_running", report["issue_codes"])
        self.assertEqual(self.server.calls, [])
        self.assertEqual(list(self.fixture.output.glob("ccv-devices-*.journal.json")), [])

    def test_parent_dependency_can_be_resolved_by_site_resume_without_rebinding_device_inputs(self):
        self.server.fault_at, self.server.fault = 2, TimeoutError("private-timeout")
        status, _, _ = self.fixture.run_batch(self.server, mode="execute")
        self.assertEqual(status, 1)
        self.server.calls.clear()
        _, report = self.run_devices("execute")
        missing = sum("device_destination_parent_dependency_unresolved" in row["issue_codes"] for row in report["devices"])
        self.assertGreater(missing, 0)
        self.assertLess(missing, 35)
        device_journal = self.fixture.output / report["journal_file"]
        binding = json.loads(device_journal.read_text())["binding"]
        status, _, _ = self.fixture.run_batch(self.server, mode="resume")
        self.assertEqual(status, 0)
        self.server.calls.clear()
        _, report = self.run_devices("resume")
        self.assertFalse(any("device_destination_parent_dependency_unresolved" in row["issue_codes"]
                             for row in report["devices"]))
        self.assertEqual(json.loads(device_journal.read_text())["binding"], binding)
        self.assertEqual(len(self.server.posts), 30)

    def test_device_timeout_stops_without_a_retry_or_later_lookup(self):
        self.seed_sites()
        self.server.lookup_fault = TimeoutError("private-timeout")
        _, report = self.run_devices("execute")
        self.assertEqual(report["counts"]["failed"], 1)
        self.assertEqual(report["counts"]["pending"], 34)
        self.assertEqual(sum("/device/byip/" in path for _, path in self.server.calls), 1)

    def test_returned_source_native_identity_is_not_reused_as_destination_mapping(self):
        self.seed_sites()
        found = self.seed_device()
        found["ormID"] = "private-detail-device-0"
        _, report = self.run_devices("execute")
        self.assertIn("device_destination_identity_reused", report["issue_codes"])
        self.assertEqual(report["counts"]["verified"], 0)

    def test_failed_authentication_does_not_create_a_device_journal(self):
        original = self.server.respond

        def unauthenticated(request):
            if request[1] == "/mgmt/system/user/login":
                self.server.calls.append((request[0], request[1]))
                return MemoryResponse(401, b'{"status":"error"}', [("Content-Type", "application/json")])
            return original(request)

        with patch.object(self.server, "respond", side_effect=unauthenticated):
            _, report = self.run_devices("execute")
        self.assertFalse(report["authenticated"])
        self.assertEqual(self.server.calls, [("POST", "/mgmt/system/user/login")])
        self.assertEqual(list(self.fixture.output.glob("ccv-devices-*.journal.json")), [])

    def test_origin_bound_lab_tls_consent_works_without_broadening_single_site_scope(self):
        self.seed_sites()
        policy = importlib.import_module("cc_vision_import.tls_policy")
        profile = json.loads(self.fixture.profile_path.read_text())
        profile["tls"] = {"verify": False, "lab_authorized": True, "authorized_origin": "https://destination.invalid"}
        self.fixture.profile_path.write_text(json.dumps(profile))
        exception = self.fixture.credentials.parent / "tls-exception.json"
        exception.write_text(json.dumps(profile["tls"]))
        with patch.object(policy, "_private_file"), patch.dict(os.environ, {"CCV_ALLOW_INSECURE_TLS_EXCEPTION": "true"}):
            _, report = self.run_devices(cli=True)
        self.assertFalse(report["tls"]["verify"])
        self.assertEqual(report["counts"]["blocked"], 35)
        self.assertEqual(sum("/device/byip/" in path for _, path in self.server.calls), 35)
        exception.write_text(json.dumps({**profile["tls"], "authorized_origin": "https://other.invalid"}))
        self.server.calls.clear()
        with patch.object(policy, "_private_file"), patch.dict(os.environ, {"CCV_ALLOW_INSECURE_TLS_EXCEPTION": "true"}):
            with self.assertRaises(policy.TLSPolicyError):
                self.module.run_device_migration(
                    str(self.fixture.profile_path), str(self.fixture.credentials), str(self.fixture.source_path),
                    str(self.fixture.comparison_path), str(self.fixture.snapshot_path),
                )
        self.assertEqual(self.server.calls, [])

    def test_unsupported_execution_never_prompts_or_infers_noninteractive_approval(self):
        self.seed_sites()
        with patch("builtins.input", side_effect=EOFError) as approval:
            _, report = self.run_devices("execute", cli=True)
        approval.assert_not_called()
        self.assertIn(self.module._CONTRACT_BLOCK, report["issue_codes"])

    def test_combined_preview_and_status_use_same_inputs_compact_reports_and_no_writes(self):
        for mode in ("preview", "status"):
            _, report = self.run_devices(mode, cli=True, machine=True)
            self.assertEqual(report["counts"]["total"], 35)
            self.assertEqual(report["sites"]["total"], 30)
            if mode == "preview":
                self.assertEqual(report["site_preflight"], "passed")
                self.assertEqual(sum("/site/byname/private-site-" in path for _, path in self.server.calls), 30)

    def test_device_backend_cannot_arm_site_or_device_writes_or_broaden_scope(self):
        plan = self.module.load_device_plan(str(self.fixture.source_path), str(self.fixture.comparison_path),
                                            str(self.fixture.snapshot_path))
        profile = self.fixture.discovery.DiscoveryProfile.read(str(self.fixture.profile_path))
        backend = self.module.DeviceReadBackend(profile, plan.sites.sites[0].selection)
        with self.assertRaisesRegex(self.module.SiteBlocked, "device_configuration_write_forbidden"):
            backend.arm_create()
        before = backend._authorization
        with self.assertRaisesRegex(self.module.SiteBlocked, "device_configuration_write_forbidden"):
            backend.authorize_get_targets(("/unrestricted/private-path",))
        self.assertIs(backend._authorization, before)
        for method in (self.module.HttpMethod.POST, self.module.HttpMethod.PUT, self.module.HttpMethod.DELETE):
            with self.assertRaises(ValueError):
                self.module.DestinationReadAuthorization("https://destination.invalid", (
                    (method, "/mgmt/system/config/tree/device"),
                ))
        backend.close()

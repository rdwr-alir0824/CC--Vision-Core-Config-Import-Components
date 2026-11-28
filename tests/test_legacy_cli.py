import copy
import io
import json
import warnings
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import replace
from getpass import GetPassWarning
from unittest.mock import Mock, patch

from offline_support import OfflineTestCase
from test_http_backend import MemoryConnection, MemoryResponse
from test_legacy_object_exports import TREE, device, site

from cc_vision_import.ccv import MENU, main
from cc_vision_import.client import ApiClient, ClientError
from cc_vision_import.config import ControllerConfig
from cc_vision_import.files import load_json, save_json
from cc_vision_import.objects import (
    ExportResult, ImportResult, ObjectImportResult, import_objects, inspect_import,
)
from cc_vision_import.transport import HttpMethod


SECRET = "synthetic-cli-controller-secret"
DEVICE_SECRET = "synthetic-cli-device-secret"


class LegacyCliTests(OfflineTestCase):
    def setUp(self):
        super().setUp()
        self.input_path = self.directory / "portable-menu.json"
        self.output_path = self.directory / "physical-menu.json"
        self.other_output = self.directory / "organization-menu.json"
        self.data = {
            "source_root": {"id": "portable-root-81", "name": "Mist Canopy"},
            "sites": [{
                "id": "portable-site-82", "name": "Mist Branch",
                "parentOrmID": "portable-root-81", "parent_site_name": "Mist Canopy",
            }],
            "devices": [{
                "id": "portable-device-83", "name": "Mist Device", "type": "synthetic-menu-model",
                "managementIp": "198.51.100.81", "parentOrmID": "portable-site-82",
                "deviceAccess": {"cliPassword": DEVICE_SECRET, "snmpV3PrivacyPassword": DEVICE_SECRET},
            }],
        }
        save_json(self.input_path, self.data)
        self.exporter = Mock(side_effect=lambda _config, outputs, **_kwargs: {
            tree: ExportResult("SUCCESS", path, 1, 1) for tree, path in outputs.items()
        })
        self.import_result = ImportResult((
            ObjectImportResult("Site", "portable-site-82", "SKIPPED", "identity_and_placement_agree"),
            ObjectImportResult("Device", "portable-device-83", "SUCCESS", "creation_confirmed"),
        ))
        self.importer = Mock(side_effect=self.mock_import)
        self.reader = Mock()
        self.password = Mock(return_value=SECRET)

    def mock_import(self, _config, path, _tree, *, source_root, confirm_destination, **_kwargs):
        summary = inspect_import(path, source_root=source_root)
        actual = replace(
            summary, destination_root_id="discovered-root-901",
            destination_root_name="Discovered Canopy",
        )
        if confirm_destination(actual) is not True:
            return ImportResult((), "import_cancelled", "destination_confirmation")
        return self.import_result

    def run_menu(self, inputs, *, real_import=False, real_export=False, factory=None,
                 hidden=False, argv=None, input_handler=None):
        self.reader.side_effect = [*inputs, "8"] if input_handler is None else input_handler
        self.stdout = io.StringIO()
        self.stderr = io.StringIO()
        importer = Mock(wraps=import_objects) if real_import else self.importer
        if real_export:
            from cc_vision_import.objects import export_objects
            exporter = Mock(wraps=export_objects)
        else:
            exporter = self.exporter
        with (
            patch("cc_vision_import.ccv.export_objects", exporter),
            patch("cc_vision_import.ccv.import_objects", importer),
            redirect_stdout(self.stdout), redirect_stderr(self.stderr),
            warnings.catch_warnings(),
        ):
            warnings.simplefilter("always")
            code = main(
                [] if argv is None else argv, input_fn=self.reader,
                password_fn=None if hidden else self.password, connection_factory=factory,
            )
        self.assertEqual(code, 0)
        output = self.stdout.getvalue() + self.stderr.getvalue()
        self.assertNotIn(SECRET, output)
        self.assertNotIn(DEVICE_SECRET, output)
        return output

    def export_inputs(self, tree="1", *, verify="", authorize=None, product="1"):
        values = ["1", product, "source.example.invalid", "synthetic-operator", verify]
        if authorize is not None:
            values.append(authorize)
        values.append(tree)
        values.append(str(self.other_output if tree == "2" else self.output_path))
        if tree == "3":
            values.append(str(self.other_output))
        return values

    def import_inputs(self, tree="1", *, initial="yes", final="yes", verify="",
                      authorize=None, legacy=False):
        values = ["2", str(self.input_path)]
        if legacy:
            values.extend(["portable-root-81", "Mist Canopy"])
        values.extend(["destination.example.invalid", "synthetic-operator", verify])
        if authorize is not None:
            values.append(authorize)
        values.extend([tree, initial, final])
        return values

    def test_exact_main_menu_and_exit(self):
        expected = (
            "CC-Vision Core Config Import Components\n\n"
            "1. Export Sites and Devices\n2. Import Sites and Devices\n"
            "3. Modify exported credentials (Not implemented)\n"
            "4. Export LDAP configuration (Not implemented)\n"
            "5. Import LDAP configuration (Not implemented)\n"
            "6. Export Scheduler configuration (Not implemented)\n"
            "7. Import Scheduler configuration (Not implemented)\n8. Exit"
        )
        self.assertEqual(MENU, expected)
        output = self.run_menu(["8"])
        self.assertIn(expected, output)
        self.assertIn("Goodbye.", output)
        self.exporter.assert_not_called()
        self.importer.assert_not_called()

    def test_export_physical_dispatch_runtime_config_and_hidden_password(self):
        output = self.run_menu(self.export_inputs())
        config, paths = self.exporter.call_args.args
        self.assertEqual(config.address, "source.example.invalid")
        self.assertEqual(config.username, "synthetic-operator")
        self.assertEqual(config.password, SECRET)
        self.assertEqual(config.product, "vision")
        self.assertTrue(config.verify_tls)
        self.assertEqual(paths, {"Physical": self.output_path})
        self.password.assert_called_once_with("Password: ")
        self.assertFalse(any(call.args[0] == "Password: " for call in self.reader.call_args_list))
        self.assertFalse(self.exporter.call_args.kwargs["tls_exception_authorized"])
        self.assertFalse(self.exporter.call_args.kwargs["allow_live"])
        self.assertIn("Physical: SUCCESS", output)
        self.assertIn(str(self.output_path), output)
        self.assertIn("Sites=1, Devices=1", output)

    def test_export_organization_and_cyber_controller_product(self):
        output = self.run_menu(self.export_inputs("2", product="2"))
        self.assertEqual(self.exporter.call_args.args[0].product, "cyber-controller")
        self.assertEqual(self.exporter.call_args.args[1], {"Organization": self.other_output})
        self.assertIn("Organization: SUCCESS", output)

    def test_export_both_trees_single_dispatch(self):
        output = self.run_menu(self.export_inputs("3"))
        self.exporter.assert_called_once()
        self.assertEqual(self.exporter.call_args.args[1], {
            "Physical": self.output_path, "Organization": self.other_output,
        })
        self.assertIn("Physical: SUCCESS", output)
        self.assertIn("Organization: SUCCESS", output)

    def test_export_filename_default_and_sensitive_warning(self):
        inputs = self.export_inputs()
        inputs[-1] = ""
        with patch("cc_vision_import.ccv.Path.exists", return_value=False):
            output = self.run_menu(inputs)
        self.assertEqual(self.exporter.call_args.args[1]["Physical"].name, "physical.json")
        self.assertIn("sensitive Device credentials", output)

    def test_existing_output_requires_explicit_confirmation(self):
        save_json(self.output_path, {"previous": True})
        for reply in ("", "n", "invalid"):
            with self.subTest(reply=reply):
                self.exporter.reset_mock()
                output = self.run_menu([*self.export_inputs(), reply])
                self.exporter.assert_not_called()
                self.assertEqual(load_json(self.output_path), {"previous": True})
                self.assertIn("cancelled", output)
        self.run_menu([*self.export_inputs(), "yes"])
        self.exporter.assert_called_once()
        self.assertTrue(any("Replace existing export" in call.args[0]
                            for call in self.reader.call_args_list))

    def test_both_export_cancellation_prevents_any_dispatch(self):
        save_json(self.other_output, {"previous": True})
        self.run_menu([*self.export_inputs("3"), "no"])
        self.exporter.assert_not_called()
        self.assertFalse(self.output_path.exists())

    def test_unverified_tls_requires_operation_scoped_explicit_authorization(self):
        output = self.run_menu(self.export_inputs(verify="no", authorize="yes"))
        self.assertFalse(self.exporter.call_args.args[0].verify_tls)
        self.assertTrue(self.exporter.call_args.kwargs["tls_exception_authorized"])
        self.assertIn("NOT VERIFIED", output)
        self.exporter.reset_mock()
        self.run_menu(self.export_inputs())
        self.assertTrue(self.exporter.call_args.args[0].verify_tls)
        self.assertFalse(self.exporter.call_args.kwargs["tls_exception_authorized"])

    def test_declined_tls_exception_has_no_dispatch(self):
        output = self.run_menu(self.export_inputs(verify="n", authorize=""))
        self.exporter.assert_not_called()
        self.assertIn("cancelled", output)

    def test_invalid_tls_selection_has_no_dispatch(self):
        output = self.run_menu(self.export_inputs(verify="maybe"))
        self.exporter.assert_not_called()
        self.assertIn("Invalid TLS verification selection", output)

    def test_invalid_menu_choices_return_to_menu(self):
        output = self.run_menu(["", "bad", "9"])
        self.assertEqual(output.count("Invalid menu choice"), 3)
        self.exporter.assert_not_called()
        self.importer.assert_not_called()

    def test_unimplemented_options_have_no_operations_or_file_changes(self):
        before = self.input_path.read_bytes()
        with patch("cc_vision_import.ccv.prompt_config") as config:
            output = self.run_menu(["3", "4", "5", "6", "7"])
        config.assert_not_called()
        self.exporter.assert_not_called()
        self.importer.assert_not_called()
        self.assertEqual(self.input_path.read_bytes(), before)
        self.assertEqual(list(self.directory.iterdir()), [self.input_path])
        self.assertEqual(output.count("No network requests or file changes performed"), 5)

    def test_import_dispatch_and_actual_destination_confirmation_summary(self):
        output = self.run_menu(self.import_inputs())
        self.importer.assert_called_once()
        config, path, tree = self.importer.call_args.args
        self.assertEqual((config.address, path, tree),
                         ("destination.example.invalid", self.input_path, "Physical"))
        self.assertTrue(config.verify_tls)
        self.assertIn("Mist Canopy", output)
        self.assertIn("portable-root-81", output)
        self.assertIn("discovered-root-901", output)
        self.assertIn("Discovered Canopy", output)
        self.assertIn("Sites=1, Devices=1", output)
        self.assertIn("Import creates objects", output)
        self.assertIn("not be automatically updated, moved or deleted", output)
        self.assertIn("Automatic rollback is not supported", output)
        self.assertIn("Sites: SUCCESS=0, SKIPPED=1, FAILED=0", output)
        self.assertIn("Devices: SUCCESS=1, SKIPPED=0, FAILED=0", output)

    def test_import_organization_and_explicit_unverified_tls(self):
        output = self.run_menu(self.import_inputs("2", verify="n", authorize="yes"))
        self.assertEqual(self.importer.call_args.args[2], "Organization")
        self.assertFalse(self.importer.call_args.args[0].verify_tls)
        self.assertTrue(self.importer.call_args.kwargs["tls_exception_authorized"])
        self.assertIn("Destination tree: Organization", output)

    def test_initial_import_confirmation_defaults_to_cancel(self):
        for reply in ("", "invalid", "no"):
            with self.subTest(reply=reply):
                self.importer.reset_mock()
                output = self.run_menu(self.import_inputs(initial=reply, final="8"))
                self.importer.assert_not_called()
                self.assertIn("cancelled", output)

    def test_actual_destination_root_confirmation_defaults_to_cancel(self):
        output = self.run_menu(self.import_inputs(final=""))
        self.assertIn("Import cancelled before object writes", output)
        self.assertIn("Sites: SUCCESS=0, SKIPPED=0, FAILED=0", output)

    def test_legacy_source_root_identification_delegates_validation(self):
        self.data.pop("source_root")
        save_json(self.input_path, self.data)
        output = self.run_menu(self.import_inputs(legacy=True))
        self.assertEqual(self.importer.call_args.kwargs["source_root"], {
            "id": "portable-root-81", "name": "Mist Canopy",
        })
        self.assertIn("older file requires explicit source-root identification", output)

    def test_missing_and_malformed_json_before_credentials_or_dispatch(self):
        for text in (None, "{", '{"sites":[],"sites":[]}', '{"value":NaN}'):
            with self.subTest(text=text):
                self.password.reset_mock()
                if text is None:
                    self.input_path.unlink()
                else:
                    self.input_path.write_text(text, encoding="utf-8")
                output = self.run_menu(["2", str(self.input_path)])
                self.password.assert_not_called()
                self.importer.assert_not_called()
                self.assertIn("invalid_json_file", output)

    def test_invalid_import_structure_before_login(self):
        self.data["devices"][0]["parentOrmID"] = "missing-parent"
        save_json(self.input_path, self.data)
        output = self.run_menu(["2", str(self.input_path)])
        self.importer.assert_not_called()
        self.assertIn("missing_source_parent", output)

    def test_invalid_controller_empty_input_and_tree_selection(self):
        for inputs in (
            ["2", ""],
            ["1", "invalid-product"],
            ["1", "1", "http://invalid.example.invalid", "operator"],
            [*self.export_inputs()[:-2], "invalid-tree"],
        ):
            with self.subTest(inputs=inputs):
                output = self.run_menu(inputs)
                self.exporter.assert_not_called()
                self.importer.assert_not_called()
                self.assertTrue("Invalid" in output or "invalid" in output)

    def test_export_failures_and_independent_tree_results(self):
        self.exporter.side_effect = lambda _config, outputs, **_kwargs: {
            "Physical": ExportResult("FAILED", error_code="http_error", failed_step="device_access[0]"),
            "Organization": ExportResult("SUCCESS", outputs["Organization"], 1, 1),
        }
        output = self.run_menu(self.export_inputs("3"))
        self.assertIn("Physical: FAILED", output)
        self.assertIn("Incomplete export: http_error at device_access[0]", output)
        self.assertIn("Organization: SUCCESS", output)

    def test_import_failures_uncertain_outcomes_and_aggregate_counts(self):
        self.import_result = ImportResult((
            ObjectImportResult("Site", "portable-site-82", "SKIPPED", "identity_and_placement_agree"),
            ObjectImportResult("Device", "portable-device-83", "FAILED",
                               "destination_outcome_uncertain:creation_unconfirmed"),
        ))
        output = self.run_menu(self.import_inputs())
        self.assertIn("Import: FAILED", output)
        self.assertIn("Devices: SUCCESS=0, SKIPPED=0, FAILED=1", output)
        self.assertIn("portable-device-83", output)
        self.assertIn("destination_outcome_uncertain:creation_unconfirmed", output)

    def test_global_import_and_cleanup_errors_are_reported(self):
        self.import_result = ImportResult((), "local_cleanup_failed", "session_cleanup", True)
        output = self.run_menu(self.import_inputs())
        self.assertIn("Import: FAILED", output)
        self.assertIn("Local API session cleanup failed", output)

    def test_hidden_password_fallback_is_refused_without_echoing(self):
        with patch("cc_vision_import.ccv.getpass", side_effect=GetPassWarning(SECRET)):
            output = self.run_menu(["1", "1", "source.example.invalid", "operator"], hidden=True)
        self.assertIn("Hidden password input unavailable", output)
        self.exporter.assert_not_called()

    def test_hidden_password_uses_getpass_when_available(self):
        with patch("cc_vision_import.ccv.getpass", return_value=SECRET) as hidden:
            self.run_menu(self.export_inputs(), hidden=True)
        hidden.assert_called_once_with("Password: ")

    def test_ctrl_c_and_eof_at_menu_exit_gracefully(self):
        for error in (KeyboardInterrupt(), EOFError()):
            with self.subTest(error=type(error)):
                output = self.run_menu([error])
                self.assertIn("Cancelled; exiting", output)
                self.exporter.assert_not_called()
                self.importer.assert_not_called()

    def test_ctrl_c_during_input_has_no_dispatch(self):
        output = self.run_menu(["1", KeyboardInterrupt()])
        self.assertIn("Cancelled; exiting", output)
        self.exporter.assert_not_called()

    def test_live_dispatch_is_disabled_by_default_and_explicit_flag_is_forwarded(self):
        output = self.run_menu(["8"])
        self.assertIn("Live API dispatch disabled", output)
        self.run_menu(self.export_inputs(), argv=["--allow-live"])
        self.assertTrue(self.exporter.call_args.kwargs["allow_live"])

    def memory_factory(self, responses, *, interrupt_login=False):
        connections = []
        def factory(host, port, *, timeout, context):
            connection = MemoryConnection(responses.pop(0))
            if interrupt_login:
                connection.failure = ("getresponse", KeyboardInterrupt(SECRET))
            connections.append(connection)
            return connection
        return factory, connections

    def test_actual_destination_cancellation_closes_session_without_object_posts(self):
        for reply in ("no", "", "invalid"):
            with self.subTest(reply=reply):
                factory, connections = self.memory_factory([
                    MemoryResponse(body=b'{"status":"ok"}'),
                    MemoryResponse(body=json.dumps(site("actual-root-901", "Actual Canopy")).encode()),
                ])
                output = self.run_menu(self.import_inputs(final=reply), real_import=True, factory=factory)
                self.assertIn("actual-root-901", output)
                self.assertIn("Import cancelled before object writes", output)
                requests = [request for connection in connections for request in connection.requests]
                self.assertEqual([request[1] for request in requests], [
                    "/mgmt/system/user/login", "/mgmt/system/config/tree/Physical",
                ])
                self.assertTrue(all(connection.close_calls == 1 for connection in connections))

    def test_actual_import_creation_follows_root_confirmation_and_cleans_session(self):
        self.data["sites"] = []
        self.data["devices"][0]["parentOrmID"] = "portable-root-81"
        save_json(self.input_path, self.data)
        after = site("actual-root-901", "Actual Canopy",
                     device("actual-device-903", "Mist Device", "198.51.100.81"))
        after["children"][0]["type"] = "synthetic-menu-model"
        factory, connections = self.memory_factory([
            MemoryResponse(body=b'{"status":"ok"}'),
            MemoryResponse(body=json.dumps(site("actual-root-901", "Actual Canopy")).encode()),
            MemoryResponse(status=202, body=b""),
            MemoryResponse(body=json.dumps(after).encode()),
        ])
        def confirm_input(prompt):
            if "Create objects under" in prompt:
                self.assertEqual(len(connections), 2)
            return next(values, "8")
        values = iter(self.import_inputs())
        output = self.run_menu(
            self.import_inputs(), real_import=True, factory=factory, input_handler=confirm_input,
        )
        self.assertIn("Devices: SUCCESS=1, SKIPPED=0, FAILED=0", output)
        self.assertTrue(any("Create objects under" in call.args[0] for call in self.reader.call_args_list))
        self.assertEqual(len(connections), 4)
        self.assertTrue(all(connection.close_calls == 1 for connection in connections))

    def test_interrupt_during_discovered_root_confirmation_closes_actual_session(self):
        for error in (KeyboardInterrupt(SECRET), EOFError(SECRET)):
            with self.subTest(error=type(error)):
                factory, connections = self.memory_factory([
                    MemoryResponse(body=b'{"status":"ok"}'),
                    MemoryResponse(body=json.dumps(site("actual-root-901", "Actual Canopy")).encode()),
                ])
                output = self.run_menu(
                    self.import_inputs(final=error), real_import=True, factory=factory,
                )
                self.assertIn("Import interrupted", output)
                self.assertEqual(len(connections), 2)
                self.assertTrue(all(connection.close_calls == 1 for connection in connections))

    def test_ctrl_c_during_actual_login_clears_legacy_first_session(self):
        factory, connections = self.memory_factory([
            MemoryResponse(body=b'{"status":"ok"}'),
        ], interrupt_login=True)
        config = ControllerConfig("source.example.invalid", "synthetic-operator", SECRET, "vision")
        client = ApiClient(
            config, operations=((HttpMethod.GET, (*TREE, "Physical")),),
            connection_factory=factory,
        )
        with patch("cc_vision_import.objects.ApiClient", return_value=client):
            with patch.object(client, "close", wraps=client.close) as close:
                output = self.run_menu(self.export_inputs(), real_export=True, factory=factory)
                close.assert_called_once()
        self.assertIn("Cancelled; exiting", output)
        self.assertIn("Export interrupted", output)
        self.assertEqual(len(connections), 1)
        self.assertEqual(connections[0].close_calls, 1)
        self.assertFalse(self.output_path.exists())

    def test_secret_free_actual_authentication_error(self):
        factory, connections = self.memory_factory([
            MemoryResponse(body=json.dumps({"status": "error", "message": DEVICE_SECRET}).encode()),
        ])
        output = self.run_menu(self.import_inputs(), real_import=True, factory=factory)
        self.assertIn("authentication_rejected", output)
        self.assertEqual(len(connections), 1)
        self.assertEqual(connections[0].close_calls, 1)

    def test_preview_contains_no_access_values(self):
        summary = inspect_import(self.input_path)
        self.assertEqual((summary.source_root_id, summary.site_count, summary.device_count),
                         ("portable-root-81", 1, 1))
        self.assertNotIn(DEVICE_SECRET, repr(summary))

    def test_destination_confirmation_uses_actual_loaded_input(self):
        changed = copy.deepcopy(self.data)
        changed["source_root"]["name"] = "Changed Canopy"
        changed["sites"][0]["parent_site_name"] = "Changed Canopy"
        changed["devices"] = []
        save_json(self.input_path, changed)
        factory, connections = self.memory_factory([
            MemoryResponse(body=b'{"status":"ok"}'),
            MemoryResponse(body=json.dumps(site("actual-root-901", "Actual Canopy")).encode()),
        ])
        summaries = []
        def cancel(summary):
            summaries.append(summary)
            return False
        config = ControllerConfig("destination.example.invalid", "operator", SECRET, "cyber-controller")
        result = import_objects(
            config, self.input_path, "Physical", connection_factory=factory,
            confirm_destination=cancel,
        )
        self.assertEqual(result.error_code, "import_cancelled")
        self.assertEqual(summaries[0].source_root_name, "Changed Canopy")
        self.assertEqual(summaries[0].device_count, 0)
        self.assertEqual(summaries[0].destination_root_id, "actual-root-901")
        self.assertEqual(len(connections), 2)

    def test_login_eof_also_closes_session_and_preserves_cleanup_notes(self):
        client = ApiClient(
            ControllerConfig("source.example.invalid", "operator", SECRET, "vision"),
            connection_factory=Mock(),
        )
        with patch.object(client, "_send", side_effect=EOFError):
            with patch.object(client, "close", side_effect=ClientError("local_cleanup_failed")):
                with self.assertRaises(EOFError) as caught:
                    client.login()
        self.assertIn("Local API session cleanup failed.", caught.exception.__notes__)
        client.close()

    def test_cancellation_cleanup_failure_note_is_reported_without_exception_contents(self):
        error = KeyboardInterrupt(SECRET)
        error.add_note("Local API session cleanup failed.")
        output = self.run_menu([error])
        self.assertIn("Local API session cleanup failed", output)

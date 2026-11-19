import copy
import importlib
import io
import json
import traceback
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import asdict

from offline_support import OfflineTestCase


DOCUMENTS = (
    ("vision", "5.4.9", "DOC-V549"),
    ("cyber-controller", "10.10.7", "DOC-CC10107"),
)
ACCESS_FIELDS = {
    "int32": (
        "cliPort", "httpsSocketTimeout", "httpsPort", "httpSocketTimout", "ormVersion",
        "httpPort", "httpsConnectionTimeout", "httpConnectionTimeout",
    ),
    "boolean": (
        "useHttpsAuthentication", "useSnmpV3Authentication", "isSsh", "verifyHttpCredentials",
        "useSnmpV3Privacy", "exclusivelyReceiveDeviceEvents", "useHttpAuthentication",
        "verifyHttpsCredentials", "registerDeviceEvents",
    ),
    "string": (
        "description", "cliUsername", "ormID", "snmpV3PrivacyPassword", "httpsUsername",
        "snmpV3AuthenticationPassword", "snmpV2WriteCommunity", "snmpV3Username",
        "httpPassword", "managementIp", "httpsPassword", "name", "httpUsername",
        "cliPassword", "snmpV2ReadCommunity", "snmpV1WriteCommunity", "mgt2Ip",
        "snmpV1ReadCommunity", "mgt1Ip",
    ),
    "enum": ("snmpV3PrivacyProtocol", "snmpV3AuthenticationProtocol", "visionMgtPort", "snmpVersion"),
}


class SchemaQualificationTests(OfflineTestCase):
    guarded_cases = 0
    guarded_entrypoint_observations = 0
    guarded_attempts = 0

    def setUp(self) -> None:
        super().setUp()
        self.q = importlib.import_module("cc_vision_import.schema_qualification")
        self.c = importlib.import_module("cc_vision_import.contracts")
        self.o = importlib.import_module("cc_vision_import.controller_objects")
        self.t = importlib.import_module("cc_vision_import.transport")

    def tearDown(self) -> None:
        attempts = sum(guard.call_count for guard in self.network_guards)
        type(self).guarded_cases += 1
        type(self).guarded_entrypoint_observations += len(self.network_guards)
        type(self).guarded_attempts += attempts
        self.assertEqual(attempts, 0)
        super().tearDown()

    @classmethod
    def tearDownClass(cls) -> None:
        print(
            f"\nSCHEMA_NETWORK_GUARDS cases={cls.guarded_cases} "
            f"entrypoint_observations={cls.guarded_entrypoint_observations} "
            f"attempts={cls.guarded_attempts}"
        )
        super().tearDownClass()

    def artifact(self, data, *, product="vision", version="5.4.9", exporter="synthetic-source"):
        return {
            "schema_version": 1, "domain": "api-schema-evidence",
            "source": {"product": product, "version": version},
            "metadata": {"exported_at": "2026-11-18T00:00:00Z", "exporter": exporter},
            "objects": [copy.deepcopy(data)],
            "validation": {"scope": "offline-contract", "status": "not_validated", "issue_codes": []},
        }

    def qualify(self, data, subset=None, *, document=DOCUMENTS[0]):
        product, version, reference = document
        return self.q.qualify_schema(
            self.artifact(data, product=product, version=version),
            self.q.SchemaSubset.SITE if subset is None else subset,
            evidence_reference=reference,
        )

    def response(self, status, body=None, headers=None):
        return self.t.HttpResponse(
            status, b"" if body is None else json.dumps(body).encode("utf-8"),
            {} if headers is None else headers,
        )

    def login(self, response, *, document=DOCUMENTS[0]):
        return self.q.qualify_login_response(
            response, product=document[0], version=document[1], evidence_reference=document[2],
        )

    def trace(self, *responses, document=DOCUMENTS[0], origin="https://synthetic.invalid"):
        return self.q.qualify_async_trace(
            responses, origin=origin,
            product=document[0], version=document[1], evidence_reference=document[2],
        )

    def sequence(self):
        return (
            self.response(202, headers={"Location": "https://synthetic.invalid/mgmt/asyncoperations/status/synthetic-1"}),
            self.response(200, {"status": "ok"}),
            self.response(303, headers={"Location": "https://synthetic.invalid/mgmt/asyncoperations/result/synthetic-1"}),
        )

    def error(self, function, *args, **kwargs):
        with self.assertRaises(self.c.ContractValidationError) as caught:
            function(*args, **kwargs)
        self.assertEqual(caught.exception.result.status, "invalid")
        self.assertTrue(caught.exception.result.issues)
        return caught.exception

    def test_exact_document_bindings_reject_other_versions_and_cross_references(self) -> None:
        for product, version, reference in DOCUMENTS:
            result = self.q.require_document(product, version, reference)
            self.assertEqual(result.version, version)
            for other in ("0.0-test", "5.4.8", "5.4.10", "5.4.x", "10.10.6", "10.10.8", "10.10.x"):
                with self.subTest(product=product, version=other):
                    self.error(self.q.require_document, product, other, reference)
            self.error(self.q.require_document, product, version, "unapproved-reference")
        self.error(self.q.require_document, "unapproved-product", "5.4.9", "DOC-V549")
        self.error(self.q.require_document, "vision", "5.4.9", "DOC-CC10107")

    def test_document_provenance_discrepancy_is_retained_in_qualifications(self) -> None:
        data = {"ormID": "synthetic-site", "name": "Synthetic", "type": "Site"}
        vision = self.qualify(data)
        controller = self.qualify(data, document=DOCUMENTS[1])
        self.assertEqual(vision.status, "documented-subset")
        self.assertEqual(controller.status, "unqualified")
        self.assertEqual(controller.document.metadata_version, "10.10.6")
        self.assertEqual(controller.document.version, "10.10.7")
        self.assertIn("document_version_conflict", [issue.code for issue in controller.unqualified])
        self.assertEqual(controller.pdf_pages, (255,))

    def test_all_twelve_exact_method_paths_have_reviewed_classifications(self) -> None:
        pairs = (
            ("POST", "/mgmt/system/user/login", True),
            ("GET", "/mgmt/system/config/tree/Physical", False),
            ("GET", "/mgmt/system/config/tree/Organization", False),
            ("GET", "/mgmt/system/config/tree/site/byname/{name}", True),
            ("GET", "/mgmt/system/config/tree/site/byid/{id}", True),
            ("GET", "/mgmt/system/config/tree/device/byip/{ip}", True),
            ("POST", "/mgmt/system/config/tree/site", False),
            ("POST", "/mgmt/system/config/tree/device", True),
            ("PUT", "/mgmt/system/config/tree/device", False),
            ("GET", "/mgmt/system/config/itemlist/ldapobjectpermission", False),
            ("POST", "/mgmt/system/config/itemlist/ldapobjectpermission", False),
            ("PUT", "/{index}/_doc/{document_id}", False),
        )
        for document in DOCUMENTS:
            for index, (method, path, documented) in enumerate(pairs, 1):
                with self.subTest(product=document[0], operation=index):
                    result = self.q.operation_evidence(*document, f"API-{index:02}")
                    self.assertEqual((result.method, result.path), (method, path))
                    self.assertEqual(result.classification, "documented" if documented else "not-found")
                    self.assertEqual(bool(result.pdf_pages), documented)
            self.error(self.q.operation_evidence, *document, "unreviewed-operation")
        self.assertEqual(self.q.operation_evidence(*DOCUMENTS[0], "API-04").pdf_pages, (141,))
        self.assertEqual(self.q.operation_evidence(*DOCUMENTS[1], "API-04").pdf_pages, (152,))
        self.q.operation_evidence(*DOCUMENTS[0], "API-01-V")
        self.q.operation_evidence(*DOCUMENTS[1], "API-01-C")
        self.error(self.q.operation_evidence, *DOCUMENTS[0], "API-01-C")

    def test_scheduler_bindings_stay_unresolved_with_candidates_only(self) -> None:
        for document in DOCUMENTS:
            for index in range(1, 5):
                result = self.q.operation_evidence(*document, f"CFG-{index:02}")
                self.assertEqual(result.classification, "unresolved-binding")
                self.assertIsNone(result.path)
                self.assertEqual(result.pdf_pages, ())
                self.assertEqual(result.method, "GET" if index == 3 else "POST")
                self.assertEqual(result.candidate_path, {
                    1: "/mgmt/system/user/login", 2: "/mgmt/system/user/logout",
                }.get(index))

    def test_document_evidence_never_grants_production_or_real_version_capabilities(self) -> None:
        capabilities = importlib.import_module("cc_vision_import.capabilities")
        plans = importlib.import_module("cc_vision_import.plans")
        for document in DOCUMENTS:
            self.q.require_document(*document)
            for mock_only in (False, True):
                with self.subTest(product=document[0], mock_only=mock_only):
                    with self.assertRaises(capabilities.ProductClientError):
                        capabilities.capabilities_for(document[0], document[1], mock_only=mock_only)
            with self.assertRaises(capabilities.ProductClientError):
                capabilities.capabilities_for(document[0], "0.0-test")
            self.assertTrue(capabilities.capabilities_for(document[0], "0.0-test", mock_only=True))
            payload = self.artifact({}, product=document[0], version=document[1])
            payload["objects"] = []
            qualified = self.q.qualify_schema(payload, self.q.SchemaSubset.DEVICE, evidence_reference=document[2])
            request = {
                "destination": {
                    "controller_id": "synthetic-destination", "product": "cyber-controller",
                    "version": "10.10.7", "base_url": "https://destination.invalid",
                },
                "mappings": [], "actions": [],
            }
            error = self.error(plans.create_plan, qualified.artifact.to_json().encode(), request)
            self.assertEqual(error.result.issues[0].code, "evidence_only_artifact")
            payload["domain"] = "synthetic-domain"
            generic = plans.create_plan(json.dumps(payload).encode(), request).to_dict()
            generic["domain"] = "api-schema-evidence"
            error = self.error(plans.parse_plan, generic)
            self.assertEqual(error.result.issues[0].code, "evidence_only_artifact")

    def test_login_success_and_rejection_examples_for_both_documents(self) -> None:
        for document in DOCUMENTS:
            success = self.login(self.response(200, {"status": "ok", "jsessionid": "synthetic-session"}), document=document)
            rejection = self.login(self.response(401, {"status": "error", "message": "Synthetic rejection"}), document=document)
            self.assertEqual(success.outcome, "reported-login")
            self.assertEqual(rejection.outcome, "reported-rejection")
            self.assertEqual(success.pdf_pages, (156, 157, 158))

    def test_login_missing_status_wrong_types_and_http_status_mismatches(self) -> None:
        for body in ({}, {"status": None}, {"status": True}, {"status": 1}, {"status": []}, {"status": {"secret_ref": "synthetic/ref"}}):
            with self.subTest(kind=type(body.get("status")).__name__):
                self.error(self.login, self.response(200, body))
        for status, body in (
            (200, {"status": "error", "message": "Synthetic"}),
            (401, {"status": "ok", "jsessionid": "synthetic"}),
            (201, {"status": "ok", "jsessionid": "synthetic"}),
            (401, {"status": "error"}), (401, {"status": "error", "message": False}),
        ):
            self.error(self.login, self.response(status, body))

    def test_login_missing_null_or_wrong_session_information_is_not_qualified(self) -> None:
        self.error(self.login, self.response(200, {"status": "ok"}))
        for value in (None, False, 1, [], {}, "", " ", "synthetic\nsession"):
            with self.subTest(kind=type(value).__name__):
                self.error(self.login, self.response(200, {"status": "ok", "jsessionid": value}))

    def test_login_malformed_json_duplicate_keys_and_invalid_response_types(self) -> None:
        for body in (
            b"", b"synthetic-not-json", b"\xff", b"[]", b"null",
            b'{"status":"ok","status":"error"}', b'{"status":NaN}', b'{"status":Infinity}',
        ):
            with self.subTest(body=body):
                self.error(self.login, self.t.HttpResponse(200, body))
        for response in (
            self.t.HttpResponse(True), self.t.HttpResponse(600),
            self.t.HttpResponse(200, "synthetic"), self.t.HttpResponse(200, b"{}", []),
        ):
            self.error(self.login, response)

    def test_login_never_returns_or_discloses_session_credentials_or_rejection_text(self) -> None:
        marker = "synthetic-confidential-marker"
        output = io.StringIO()
        with redirect_stdout(output), redirect_stderr(output):
            for response in (
                self.response(200, {"status": "ok", "jsessionid": marker, "password": marker}),
                self.response(401, {"status": "error", "message": marker}),
            ):
                result = self.login(response)
                self.assertNotIn(marker, repr(result) + json.dumps(asdict(result)))
            for response in (
                self.response(200, {"status": marker}),
                self.t.HttpResponse(200, ('{"status":"' + marker).encode()),
                self.t.HttpResponse(200, marker.encode() + b"\xff"),
            ):
                try:
                    self.login(response)
                except self.c.ContractValidationError as exc:
                    rendered = "".join(traceback.format_exception(exc))
                    self.assertNotIn(marker, rendered + repr(exc.result))
                else:
                    self.fail("An unqualified login response was accepted.")
        self.assertEqual(output.getvalue(), "")

    def test_offline_login_qualification_does_not_change_controller_authentication_policy(self) -> None:
        authentication = importlib.import_module("cc_vision_import.authentication")
        response = self.response(200, {"status": "not-ok"})
        strategy = authentication.CyberControllerAuthenticationStrategy()
        outcome = strategy.interpret(response)
        self.assertEqual(outcome.evidence, authentication.LoginEvidence.HTTP_200_ONLY)
        self.error(self.login, response, document=DOCUMENTS[1])

    def test_site_subset_preserves_native_identity_and_does_not_infer_defaults(self) -> None:
        data = {"ormID": "synthetic-native-id", "name": "", "type": "Site"}
        result = self.qualify(data)
        self.assertEqual(result.status, "documented-subset")
        self.assertEqual(result.artifact.objects[0], data)
        self.assertNotIn("description", result.artifact.objects[0])
        self.assertNotIn("parentOrmID", result.artifact.objects[0])
        self.assertEqual(result.artifact.validation.status, "not_validated")

    def test_site_required_fields_and_incorrect_json_types(self) -> None:
        valid = {"ormID": "synthetic-site", "name": "Synthetic", "type": "Site"}
        for name in valid:
            data = dict(valid)
            del data[name]
            self.error(self.qualify, data)
        for name in ("ormID", "name", "type", "description", "parentOrmID"):
            for value in (True, 1, 1.5, [], {}):
                with self.subTest(field=name, kind=type(value).__name__):
                    self.error(self.qualify, valid | {name: value})

    def test_site_missing_and_null_are_distinct_and_nullability_is_unqualified(self) -> None:
        valid = {"ormID": "synthetic-site", "name": "Synthetic", "type": "Site"}
        for name in ("ormID", "name", "type", "description", "parentOrmID"):
            with self.subTest(field=name):
                result = self.qualify(valid | {name: None})
                self.assertEqual(result.status, "unqualified")
                self.assertIsNone(result.artifact.objects[0][name])
                self.assertIn("unverified_nullability", [issue.code for issue in result.unqualified])
        self.assertNotIn("description", self.qualify(valid).artifact.objects[0])

    def test_unknown_fields_json_types_dictionary_and_array_order_survive_roundtrip(self) -> None:
        data = {
            "zUnknown": {"z": [True, 1, 1.25, None, "1", {"z": 2, "a": 1}], "a": False},
            "ormID": "synthetic-site", "name": "Synthetic", "type": "Site",
            "aUnknown": {"second": None, "first": []},
        }
        source = self.artifact(data)
        original = copy.deepcopy(source)
        result = self.q.qualify_schema(source, self.q.SchemaSubset.SITE, evidence_reference="DOC-V549")
        restored = json.loads(result.artifact.to_json())
        self.assertEqual(restored, original)
        self.assertEqual(list(restored["objects"][0]), list(data))
        self.assertEqual(list(restored["objects"][0]["zUnknown"]), ["z", "a"])
        self.assertEqual(list(restored["objects"][0]["zUnknown"]["z"][-1]), ["z", "a"])
        for actual, expected in zip(restored["objects"][0]["zUnknown"]["z"], data["zUnknown"]["z"], strict=True):
            self.assertIs(type(actual), type(expected))
        source["objects"][0]["ormID"] = "synthetic-mutated-input"
        self.assertEqual(result.artifact.objects[0]["ormID"], "synthetic-site")

    def test_both_migration_directions_keep_independent_controller_identities(self) -> None:
        for source_document in DOCUMENTS:
            source = self.qualify(
                {"ormID": "synthetic-shared-id", "name": "Source", "type": "Site"},
                document=source_document,
            )
            destination = self.qualify(
                {"ormID": "synthetic-shared-id", "name": "Destination", "type": "Site"},
                document=DOCUMENTS[1],
            )
            refs = [
                self.o.SourceObjectReference(
                    controller, self.o.TreeName.PHYSICAL, self.o.ControllerObjectKind.SITE,
                    result.artifact.objects[0]["ormID"],
                ).as_identity()
                for controller, result in (("synthetic-source", source), ("synthetic-destination", destination))
            ]
            self.assertNotEqual(refs[0], refs[1])
            self.assertEqual(source.artifact.objects[0]["ormID"], destination.artifact.objects[0]["ormID"])
            self.assertNotIn("destination", source.artifact.to_dict())
            self.assertNotIn("destination_id", source.artifact.objects[0])

    def test_device_lookup_subset_nested_configuration_and_unknowns_are_preserved(self) -> None:
        data = {
            "ormID": "synthetic-device", "ormVersion": 3, "name": "Synthetic", "type": "Alteon",
            "physicalParentId": "synthetic-site", "deviceStatus": {"future": [False, None]},
            "deviceSetup": {
                "ormID": "synthetic-setup", "ormVersion": 2, "name": "Synthetic",
                "license": {"future": "synthetic"},
                "deviceAccess": {"cliPort": 22, "isSsh": True, "managementIp": "192.0.2.1"},
                "unknown": {"z": "1", "a": [1, False, None]},
            },
            "opaque": {"z": 1, "a": False},
        }
        result = self.qualify(data, self.q.SchemaSubset.DEVICE)
        restored = json.loads(result.artifact.to_json())["objects"][0]
        self.assertEqual(restored, data)
        self.assertEqual(list(restored["deviceSetup"]["unknown"]), ["z", "a"])
        self.assertEqual(result.pdf_pages, (219, 220, 224))

    def test_device_model_optional_fields_do_not_become_creation_requirements(self) -> None:
        self.assertEqual(self.qualify({}, self.q.SchemaSubset.DEVICE).status, "documented-subset")
        for data in (
            {"ormVersion": True}, {"ormVersion": 1.0}, {"ormVersion": 2 ** 31},
            {"ormID": 3}, {"deviceSetup": []}, {"deviceSetup": {"deviceAccess": []}},
            {"deviceSetup": {"license": "synthetic"}}, {"deviceSetup": {"ormVersion": "1"}},
        ):
            self.error(self.qualify, data, self.q.SchemaSubset.DEVICE)
        for subset in ("device-create", "site-create", "DevicePojo", "UserPojo"):
            self.error(self.qualify, {}, subset)

    def test_device_missing_null_and_nested_nullability_remain_distinct(self) -> None:
        absent = self.qualify({}, self.q.SchemaSubset.DEVICE)
        explicit = self.qualify({"ormID": None, "deviceSetup": {"deviceAccess": None}}, self.q.SchemaSubset.DEVICE)
        self.assertEqual(absent.artifact.objects[0], {})
        self.assertEqual(explicit.status, "unqualified")
        self.assertIsNone(explicit.artifact.objects[0]["ormID"])
        self.assertIsNone(explicit.artifact.objects[0]["deviceSetup"]["deviceAccess"])
        self.assertEqual(len(explicit.unqualified), 2)

    def test_all_forty_device_access_fields_absent_and_null_have_distinct_results(self) -> None:
        self.assertEqual(sum(map(len, ACCESS_FIELDS.values())), 40)
        absent = self.qualify({}, self.q.SchemaSubset.DEVICE_ACCESS)
        self.assertEqual(absent.status, "documented-subset")
        for fields in ACCESS_FIELDS.values():
            for name in fields:
                with self.subTest(field=name):
                    result = self.qualify({name: None}, self.q.SchemaSubset.DEVICE_ACCESS)
                    self.assertIsNone(result.artifact.objects[0][name])
                    self.assertEqual(result.status, "unqualified")
                    self.assertIn("unverified_nullability", [issue.code for issue in result.unqualified])
                    self.assertNotIn(name, absent.artifact.objects[0])

    def test_device_access_documented_non_null_types_without_coercion_or_guard_weakening(self) -> None:
        for kind in ("int32", "boolean", "string"):
            for name in ACCESS_FIELDS[kind]:
                value = {"int32": 443, "boolean": True, "string": "synthetic-value"}[kind]
                with self.subTest(field=name):
                    if self.o.is_controller_credential_field(name):
                        self.error(self.qualify, {name: value}, self.q.SchemaSubset.DEVICE_ACCESS)
                    else:
                        result = self.qualify({name: value}, self.q.SchemaSubset.DEVICE_ACCESS)
                        self.assertEqual(result.status, "documented-subset")
                        self.assertIs(type(result.artifact.objects[0][name]), type(value))
        for name in ACCESS_FIELDS["enum"]:
            for value in ("synthetic-unknown-enum", 1, True, {}):
                result = self.qualify({name: value}, self.q.SchemaSubset.DEVICE_ACCESS)
                self.assertEqual(result.status, "unqualified")
                self.assertEqual(result.unqualified[0].code, "unverified_enum")

    def test_device_access_incorrect_types_and_int32_bounds_fail_closed(self) -> None:
        wrong = {
            "int32": (True, 1.0, "443", [], {}, -(2 ** 31) - 1, 2 ** 31),
            "boolean": (0, 1, "true", [], {}),
            "string": (1, 1.0, True, [], {}),
        }
        for kind, values in wrong.items():
            for name in ACCESS_FIELDS[kind]:
                for value in values:
                    with self.subTest(field=name, value_type=type(value).__name__):
                        self.error(self.qualify, {name: value}, self.q.SchemaSubset.DEVICE_ACCESS)
        for value in (-(2 ** 31), 2 ** 31 - 1):
            self.qualify({"cliPort": value}, self.q.SchemaSubset.DEVICE_ACCESS)

    def test_protected_credentials_are_preserved_but_never_wire_qualified_or_disclosed(self) -> None:
        reference = {"secret_ref": "synthetic/device-access"}
        result = self.qualify({"cliUsername": reference, "cliPassword": reference}, self.q.SchemaSubset.DEVICE_ACCESS)
        self.assertEqual(result.artifact.objects[0]["cliPassword"], reference)
        self.assertEqual(result.status, "unqualified")
        self.assertIn("credential_representation_unqualified", [issue.code for issue in result.unqualified])
        self.assertNotIn("synthetic/device-access", repr(result))
        marker = "synthetic-raw-credential-marker"
        for data in (
            {"cliPassword": marker}, {"cliUsername": marker}, {"unknown": {"username": marker}},
            {"unknown": {"nestedToken": marker}},
        ):
            error = self.error(self.qualify, data, self.q.SchemaSubset.DEVICE_ACCESS)
            self.assertNotIn(marker, repr(error) + repr(error.result))

    def test_unknown_configuration_still_obeys_strict_json_and_secret_policy(self) -> None:
        for value in (float("nan"), float("inf"), {1: "synthetic"}, object()):
            self.error(self.qualify, {"opaque": value}, self.q.SchemaSubset.DEVICE)
        payload = self.artifact({})
        payload["domain"] = "controller-objects"
        self.error(self.q.qualify_schema, payload, self.q.SchemaSubset.DEVICE, evidence_reference="DOC-V549")

    def test_async_acceptance_progress_and_redirect_never_report_completion(self) -> None:
        sequence = self.sequence()
        for count, phase in ((1, "accepted"), (2, "in-progress"), (3, "result-available")):
            for document in DOCUMENTS:
                result = self.trace(*sequence[:count], document=document)
                self.assertEqual(result.phase, phase)
                self.assertEqual(result.outcome, "not-complete")
                self.assertIsNone(result.final_status)

    def test_async_final_body_or_http_failure_determines_limited_reported_outcome(self) -> None:
        for status, body, outcome in (
            (200, {"status": "ok"}, "reported-success-unverified"),
            (200, {"status": "error", "message": "Synthetic failure"}, "reported-failure"),
            (500, None, "http-failure"), (401, None, "http-failure"),
            (200, {"futureResult": True}, "unqualified-result"),
            (200, [], "unqualified-result"), (204, None, "unqualified-result"),
        ):
            with self.subTest(status=status, outcome=outcome):
                result = self.trace(*self.sequence(), self.response(status, body))
                self.assertEqual(result.phase, "result-received")
                self.assertEqual(result.outcome, outcome)
                self.assertEqual(result.final_status, status)
                if outcome == "unqualified-result":
                    self.assertEqual(result.unqualified[0].code, "result_semantics_unverified")
        self.error(self.trace, *self.sequence(), self.response(202))
        self.error(self.trace, *self.sequence(), self.response(303))

    def test_async_missing_malformed_foreign_or_ambiguous_tracking_fails_safely(self) -> None:
        for headers in (
            {}, {"Location": None}, {"Location": 1},
            {"Location": "https://synthetic.invalid/mgmt/asyncoperations/status/synthetic-1", "location": "synthetic"},
            {"Location": "http://synthetic.invalid/mgmt/asyncoperations/status/synthetic-1"},
            {"Location": "https://other.invalid/mgmt/asyncoperations/status/synthetic-1"},
            {"Location": "/mgmt/asyncoperations/status/synthetic-1"},
            {"Location": "https://synthetic.invalid/mgmt/asyncoperations/status/../synthetic-1"},
            {"Location": "https://synthetic.invalid/mgmt/asyncoperations/status/synthetic-1?x=1"},
            {1: "synthetic"},
        ):
            with self.subTest(headers_kind=tuple(map(type, headers))):
                self.error(self.trace, self.response(202, headers=headers))

    def test_async_changed_ids_missing_result_location_and_tracking_failures_are_blocked(self) -> None:
        initial = self.sequence()[0]
        for status, headers in (
            (200, {"Location": "https://synthetic.invalid/mgmt/asyncoperations/status/different"}),
            (303, {}),
            (303, {"Location": "https://synthetic.invalid/mgmt/asyncoperations/result/different"}),
            (500, {}), (401, {}), (202, {}),
        ):
            self.error(self.trace, initial, self.response(status, headers=headers))
        self.error(self.trace)
        self.error(self.trace, self.response(200))
        self.error(self.trace, *self.sequence(), self.response(200, {"status": "ok"}), self.response(200))

    def test_async_malformed_final_content_is_sanitized_and_origin_never_resolved(self) -> None:
        marker = "synthetic-async-private-marker"
        for body in (marker.encode(), marker.encode() + b"\xff", b'{"status":NaN}'):
            try:
                self.trace(*self.sequence(), self.t.HttpResponse(200, body))
            except self.c.ContractValidationError as exc:
                self.assertNotIn(marker, "".join(traceback.format_exception(exc)) + repr(exc.result))
            else:
                self.fail("Malformed result was accepted.")
        for origin in (
            "http://synthetic.invalid", "https://synthetic.invalid/path",
            "https://synthetic.invalid:" + marker, "https://user:password@synthetic.invalid",
        ):
            error = self.error(self.trace, *self.sequence(), origin=origin)
            self.assertNotIn(marker, repr(error.result))
        self.assertEqual(sum(guard.call_count for guard in self.network_guards), 0)

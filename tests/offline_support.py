import io
import json
import runpy
import sys
import tempfile
import unittest
import importlib
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch


def device_access_acknowledgements(*inventories):
    """Explicit synthetic operator acknowledgements for comparison regression fixtures."""
    policy = importlib.import_module("cc_vision_import.controller_access_policy")
    objects = importlib.import_module("cc_vision_import.controller_objects")
    result = []
    for inventory in inventories:
        artifact = inventory.to_artifact()
        for item, row in zip(inventory.objects, artifact.objects, strict=True):
            if (
                not isinstance(item, objects.ControllerDevice)
                or item.device_access.location == objects.DeviceAccessLocation.ABSENT
                or item.device_access.value is None or item.device_access.value == {}
                or objects.has_uncertain_controller_credentials(row)
            ):
                continue
            result.append(policy.acknowledge_device_access(
                artifact, artifact, item.reference, evidence_reference="evidence-" + "2" * 32,
            ))
    return tuple(result)


class OfflineTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.network_guards: list[Mock] = []
        targets = (
            "socket.socket.connect",
            "socket.socket.connect_ex",
            "socket.socket.sendto",
            "socket.socket.sendall",
            "socket.socket.send",
            "socket.socket.bind",
            "socket.create_connection",
            "socket.getaddrinfo",
            "socket.gethostbyname",
            "socket.gethostbyname_ex",
            "socket.gethostbyaddr",
            "socket.socketpair",
            "socket.socket",
            "http.client.HTTPConnection.request",
            "urllib.request.urlopen",
        )
        for target in targets:
            guard = self.stack.enter_context(
                patch(target, side_effect=AssertionError("Network access is forbidden."))
            )
            self.network_guards.append(guard)
        self.addCleanup(self.assert_no_network_attempts)
        self.directory = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.input_path = self.directory / "fixture.json"

    def assert_no_network_attempts(self) -> None:
        for guard in self.network_guards:
            guard.assert_not_called()

    def invoke(self, *args: str) -> tuple[int, str, str]:
        stdout, stderr = io.StringIO(), io.StringIO()
        with (
            redirect_stdout(stdout),
            redirect_stderr(stderr),
            patch.object(sys, "argv", ["cc_vision_import", *args]),
        ):
            try:
                runpy.run_module("cc_vision_import", run_name="__main__")
            except SystemExit as exc:
                self.assertIsInstance(exc.code, int)
                status = int(exc.code)
            else:
                self.fail("The CLI entry point did not exit.")
        return status, stdout.getvalue(), stderr.getvalue()

    def validate_file(self, module: str = "synthetic") -> tuple[int, dict, str]:
        status, stdout, stderr = self.invoke(
            "validate", "--module", module, "--input", str(self.input_path)
        )
        return status, json.loads(stdout), stderr

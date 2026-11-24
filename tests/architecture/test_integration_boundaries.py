"""IR-07 / FR-21b: one adapter per integration; WeighingMS never imports Dummies.

Scope: every WeighingMS app under ``src/``. Excluded are the ``dummy_*`` apps
themselves and the ``weighingms`` project package, which only wires the
Dummies' URLs and hosts their training controls (project wiring, not domain).
"""

import ast
from pathlib import Path

from django.test import SimpleTestCase

SRC = Path(__file__).resolve().parents[2] / "src"
EXCLUDED = {"weighingms"}


def weighingms_apps():
    return sorted(
        path
        for path in SRC.iterdir()
        if (path / "apps.py").exists()
        and not path.name.startswith("dummy_")
        and path.name not in EXCLUDED
    )


def python_files(app):
    return sorted(path for path in app.rglob("*.py") if "migrations" not in path.parts)


def dummy_imports(source):
    """Return the ``dummy_*`` modules imported by ``source``."""
    found = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or ""]
        else:
            continue
        found += [name for name in names if name.split(".")[0].startswith("dummy_")]
    return found


class NoDummyImportTests(SimpleTestCase):
    def test_scanner_detects_dummy_imports(self):
        source = "import dummy_scale\nfrom dummy_orgatex.models import DummyBatch\n"

        self.assertEqual(dummy_imports(source), ["dummy_scale", "dummy_orgatex.models"])

    def test_scan_covers_the_orgatex_app(self):
        self.assertIn("orgatex", [app.name for app in weighingms_apps()])

    def test_no_weighingms_app_imports_a_dummy(self):
        offenders = {
            str(path.relative_to(SRC)): dummy_imports(path.read_text())
            for app in weighingms_apps()
            for path in python_files(app)
        }

        self.assertEqual({k: v for k, v in offenders.items() if v}, {})


# Each integration path is known by exactly one Python module (None: the
# server has no adapter for it) and exactly one JS file.
PATH_OWNERS = {
    "/batches": ("orgatex/adapter.py", "orgatex/static/orgatex/orgatex-client.js"),
    "/scales": ("devices/scale.py", "devices/static/devices/scale-client.js"),
    "/scanner": ("devices/scanner.py", "devices/static/devices/scanner-client.js"),
    "/printer": (None, "devices/static/devices/printer-client.js"),
    # The server only reads a printed ticket back (bolt 016); it never prints.
    "/tickets": ("devices/printer.py", "devices/static/devices/printer-client.js"),
    # Training failure switches (story 008); the Dummies are reached only here.
    "/training/modes": (None, "station/static/station/training-client.js"),
}


def python_knowers(path_fragment):
    return [
        str(path.relative_to(SRC))
        for app in weighingms_apps()
        for path in python_files(app)
        if path_fragment in path.read_text()
    ]


def js_knowers(path_fragment):
    return [
        str(path.relative_to(SRC))
        for path in sorted(SRC.rglob("*.js"))
        if path_fragment in path.read_text()
    ]


class SingleAdapterTests(SimpleTestCase):
    def test_each_path_is_known_by_one_python_adapter_at_most(self):
        for fragment, (python_owner, _) in PATH_OWNERS.items():
            with self.subTest(path=fragment):
                expected = [python_owner] if python_owner else []
                self.assertEqual(python_knowers(fragment), expected)

    def test_each_path_is_known_by_one_js_client(self):
        for fragment, (_, js_owner) in PATH_OWNERS.items():
            with self.subTest(path=fragment):
                self.assertEqual(js_knowers(fragment), [js_owner])

    def test_device_status_knows_no_device_paths(self):
        source = (SRC / "devices/static/devices/device-status.js").read_text()

        self.assertEqual([p for p in PATH_OWNERS if p in source], [])

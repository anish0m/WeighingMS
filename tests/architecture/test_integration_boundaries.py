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


class SingleOrgatexAdapterTests(SimpleTestCase):
    def test_only_the_python_adapter_knows_the_orgatex_paths(self):
        knowers = [
            str(path.relative_to(SRC))
            for app in weighingms_apps()
            for path in python_files(app)
            if "/batches" in path.read_text()
        ]

        self.assertEqual(knowers, ["orgatex/adapter.py"])

    def test_only_the_js_client_knows_the_orgatex_paths(self):
        knowers = [
            str(path.relative_to(SRC))
            for path in sorted(SRC.rglob("*.js"))
            if "/batches" in path.read_text()
        ]

        self.assertEqual(knowers, ["orgatex/static/orgatex/orgatex-client.js"])

"""FR-21 / workbook STEP 19: no batch or recipe data in the terminal's code.

The UI must fetch every batch, recipe, component and operator from the APIs.
This scans the station templates and static files (except the vendored
Alpine.js) for seed values and for data-array literals.
"""

import re
from pathlib import Path

from django.test import SimpleTestCase

STATION = Path(__file__).resolve().parents[2] / "src" / "station"
VENDOR = STATION / "static" / "station" / "vendor"

# Values from the training seed; none of them may appear in UI code.
SEED_VALUES = (
    "B-24187",
    "B-24188",
    "B-24190",
    "B-24191",
    "SO-9931",
    "JET-04",
    "Teal 4C",
    "Remazol",
    "DYE-4471",
    "R. Karim",
    "OP-01",
    "SUP-01",
)
ARRAY_LITERAL = re.compile(
    r"\b(const|let|var)\s+(batches|queue|recipes?|components|operators)\s*=\s*\[",
    re.IGNORECASE,
)


def ui_files():
    return sorted(
        path
        for path in STATION.rglob("*")
        if path.suffix in {".html", ".js", ".css"} and VENDOR not in path.parents
    )


class NoHardCodedDataTests(SimpleTestCase):
    def test_scan_covers_templates_and_scripts(self):
        names = {path.name for path in ui_files()}

        self.assertTrue(
            {
                "terminal.html",
                "terminal.js",
                "station-client.js",
                "weigh.js",
                "training-panel.js",
                "training-client.js",
            }
            <= names
        )

    def test_no_seed_values_in_ui_files(self):
        for path in ui_files():
            source = path.read_text()
            for value in SEED_VALUES:
                with self.subTest(file=path.name, value=value):
                    self.assertNotIn(value, source)

    def test_no_data_array_literals_in_ui_files(self):
        for path in ui_files():
            with self.subTest(file=path.name):
                self.assertIsNone(ARRAY_LITERAL.search(path.read_text()))

    def test_detector_finds_an_array_literal(self):
        self.assertIsNotNone(ARRAY_LITERAL.search("const batches = [{id: 1}]"))

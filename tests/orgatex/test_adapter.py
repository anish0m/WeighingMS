"""Story 001-read-batches-and-recipe: the OrgaTEX adapter reads over real HTTP."""

from datetime import datetime
from decimal import Decimal
from unittest.mock import patch

from django.test import LiveServerTestCase, SimpleTestCase, override_settings

from dummy_orgatex.services import seed_training_scenario
from orgatex.adapter import (
    Batch,
    OrgatexNotFound,
    OrgatexUnavailable,
    Recipe,
    fetch_batch,
    fetch_queue,
    fetch_recipe,
)
from tests.helpers import set_mode

LOGGER = "orgatex.adapter"


class LiveOrgatexTestCase(LiveServerTestCase):
    """Seeded Dummy OrgaTEX on a real HTTP server; the adapter points at it."""

    def setUp(self):
        seed_training_scenario()
        self.enterContext(
            override_settings(ORGATEX_BASE_URL=f"{self.live_server_url}/api")
        )


class ReadTests(LiveOrgatexTestCase):
    def test_queue_returns_seeded_batches_in_order(self):
        queue = fetch_queue()

        self.assertIsInstance(queue.received_at, datetime)
        self.assertEqual(
            [batch.batch_id for batch in queue.batches],
            ["B-24187", "B-24188", "B-24190", "B-24191"],
        )
        self.assertTrue(all(isinstance(b, Batch) for b in queue.batches))

    def test_batch_details_are_typed(self):
        batch = fetch_batch("B-24187")

        self.assertEqual(batch.order_id, "SO-9931")
        self.assertEqual(batch.machine, "JET-04")
        self.assertEqual(batch.shade, "Teal 4C")
        self.assertEqual(batch.component_count, 5)

    def test_recipe_components_in_sequence_with_decimal_quantities(self):
        recipe = fetch_recipe("B-24187")

        self.assertIsInstance(recipe, Recipe)
        self.assertEqual(recipe.recipe_name, "Teal 4C")
        self.assertEqual(
            [c.code for c in recipe.components],
            ["DYE-1180", "DYE-2204", "DYE-4471", "AUX-0101", "AUX-0107"],
        )
        for component in recipe.components:
            for value in (
                component.target_qty,
                component.tolerance,
                component.display_max,
                component.tare,
            ):
                self.assertIsInstance(value, Decimal)

    def test_recipe_values_equal_the_prototype(self):
        components = {c.code: c for c in fetch_recipe("B-24187").components}

        yellow = components["DYE-4471"]
        self.assertEqual(
            (yellow.target_qty, yellow.tolerance, yellow.unit),
            (Decimal("94.0"), Decimal("0.5"), "g"),
        )
        sulphate = components["AUX-0101"]
        self.assertEqual(
            (sulphate.target_qty, sulphate.tolerance, sulphate.unit),
            (Decimal("24.000"), Decimal("0.120"), "kg"),
        )

    def test_results_are_immutable(self):
        batch = fetch_batch("B-24187")

        with self.assertRaises(AttributeError):
            batch.shade = "changed"


class NotFoundTests(LiveOrgatexTestCase):
    def test_unknown_batch_raises_not_found(self):
        with self.assertRaises(OrgatexNotFound) as caught:
            fetch_batch("B-99999")

        self.assertEqual(caught.exception.code, "BATCH_NOT_FOUND")

    def test_unknown_batch_recipe_raises_not_found(self):
        with self.assertRaises(OrgatexNotFound) as caught:
            fetch_recipe("B-99999")

        self.assertEqual(caught.exception.code, "BATCH_NOT_FOUND")

    def test_batch_without_recipe_raises_recipe_not_available(self):
        with self.assertRaises(OrgatexNotFound) as caught:
            fetch_recipe("B-24188")

        self.assertEqual(caught.exception.code, "RECIPE_NOT_AVAILABLE")

    def test_not_found_is_not_unavailable(self):
        with self.assertRaises(OrgatexNotFound):
            try:
                fetch_batch("B-99999")
            except OrgatexUnavailable:
                self.fail("NotFound reported as Unavailable")


class UnavailableTests(LiveOrgatexTestCase):
    def test_every_read_is_unavailable_while_dummy_is_down(self):
        set_mode(self.client, "orgatex", "unavailable")

        for read in (
            fetch_queue,
            lambda: fetch_batch("B-24187"),
            lambda: fetch_recipe("B-24187"),
        ):
            with (
                self.subTest(read=read),
                self.assertLogs(LOGGER, "WARNING"),
                self.assertRaises(OrgatexUnavailable),
            ):
                read()

    def test_failure_log_has_request_details(self):
        set_mode(self.client, "orgatex", "unavailable")

        with (
            self.assertLogs(LOGGER, "WARNING") as logs,
            self.assertRaises(OrgatexUnavailable),
        ):
            fetch_recipe("B-24187")

        line = logs.output[0]
        self.assertIn(f"{self.live_server_url}/api/batches/B-24187/recipe", line)
        self.assertIn("503", line)
        self.assertIn("ORGATEX_UNAVAILABLE", line)
        self.assertIn("B-24187", line)

    def test_reads_resume_when_dummy_is_back(self):
        set_mode(self.client, "orgatex", "unavailable")
        with self.assertLogs(LOGGER, "WARNING"), self.assertRaises(OrgatexUnavailable):
            fetch_queue()

        set_mode(self.client, "orgatex", "ok")

        self.assertEqual(len(fetch_queue().batches), 4)

    def test_unreachable_orgatex_is_unavailable(self):
        with (
            override_settings(ORGATEX_BASE_URL="http://127.0.0.1:9/api"),
            self.assertLogs(LOGGER, "WARNING") as logs,
            self.assertRaises(OrgatexUnavailable),
        ):
            fetch_queue()

        self.assertIn("http://127.0.0.1:9/api/batches", logs.output[0])

    def test_bare_404_is_unavailable_not_not_found(self):
        with (
            override_settings(ORGATEX_BASE_URL=f"{self.live_server_url}/wrong"),
            self.assertLogs(LOGGER, "WARNING"),
            self.assertRaises(OrgatexUnavailable),
        ):
            fetch_batch("B-24187")


class _FakeResponse:
    def __init__(self, body):
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return self._body


RECIPE_BODY = (
    '{"batchId": "B-24187", "recipeName": "Teal 4C", "components": [{'
    '"sequence": 3, "code": "DYE-4471", "name": "Remazol Yellow RGB", '
    '"colour": "#d9a520", "targetQty": %s, "unit": "g", "tolerance": "0.5", '
    '"displayMax": "125", "lot": "2026-0387", "container": "C-12", '
    '"tare": "214", "state": "pending"}]}'
)


@override_settings(ORGATEX_BASE_URL="http://orgatex.test/api")
class MalformedResponseTests(SimpleTestCase):
    """Stubbed at the HTTP boundary only (coding standards: mocks at boundaries)."""

    def read_recipe_with(self, body):
        response = _FakeResponse(body.encode())
        with patch("orgatex.adapter.urlopen", return_value=response):
            return fetch_recipe("B-24187")

    def assert_unavailable(self, body):
        with (
            self.assertLogs(LOGGER, "WARNING") as logs,
            self.assertRaises(OrgatexUnavailable),
        ):
            self.read_recipe_with(body)
        self.assertIn("malformed", logs.output[0])

    def test_valid_stub_parses(self):
        recipe = self.read_recipe_with(RECIPE_BODY % '"94.0"')

        self.assertEqual(recipe.components[0].target_qty, Decimal("94.0"))

    def test_float_quantity_is_rejected(self):
        self.assert_unavailable(RECIPE_BODY % "94.0")

    def test_non_decimal_string_is_rejected(self):
        self.assert_unavailable(RECIPE_BODY % '"ninety-four"')

    def test_missing_field_is_rejected(self):
        self.assert_unavailable('{"batchId": "B-24187", "recipeName": "Teal 4C"}')

    def test_non_json_body_is_rejected(self):
        self.assert_unavailable("<html>gateway error</html>")

    def test_recipe_for_another_batch_is_rejected(self):
        self.assert_unavailable((RECIPE_BODY % '"94.0"').replace("B-24187", "B-24188"))

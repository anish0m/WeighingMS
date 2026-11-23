"""Bolt 014: the adapter reads back the consumptions OrgaTEX holds (FR-17)."""

from datetime import datetime
from decimal import Decimal
from unittest.mock import patch

from django.test import SimpleTestCase

from orgatex.adapter import (
    Consumption,
    ConsumptionLine,
    OrgatexNotFound,
    OrgatexUnavailable,
    fetch_consumptions,
)
from tests.helpers import post_json, set_mode
from tests.orgatex.test_adapter import LOGGER, LiveOrgatexTestCase, _FakeResponse

BODY = {
    "idempotencyKey": "WMS-B-24187-S7",
    "components": [
        {"code": "DYE-4471", "actualQty": "94.2", "unit": "g"},
        {"code": "AUX-0101", "actualQty": "24.048", "unit": "kg"},
    ],
}


class ConsumptionReadTests(LiveOrgatexTestCase):
    def post(self, body=BODY):
        return post_json(self.client, "/api/batches/B-24187/consumption", body)

    def test_no_consumption_yet_is_an_empty_tuple(self):
        self.assertEqual(fetch_consumptions("B-24187"), ())

    def test_stored_consumption_is_typed_with_decimal_quantities(self):
        accepted = self.post().json()["acceptedAt"]

        (consumption,) = fetch_consumptions("B-24187")

        self.assertIsInstance(consumption, Consumption)
        self.assertEqual(consumption.idempotency_key, "WMS-B-24187-S7")
        self.assertEqual(consumption.accepted_at, datetime.fromisoformat(accepted))
        self.assertEqual(
            consumption.lines,
            (
                ConsumptionLine("DYE-4471", Decimal("94.2"), "g"),
                ConsumptionLine("AUX-0101", Decimal("24.048"), "kg"),
            ),
        )

    def test_a_duplicate_post_is_still_one_consumption(self):
        self.assertEqual(self.post().status_code, 201)
        self.assertEqual(self.post().status_code, 200)

        self.assertEqual(len(fetch_consumptions("B-24187")), 1)

    def test_unknown_batch_raises_not_found(self):
        with self.assertLogs(LOGGER, "INFO"), self.assertRaises(OrgatexNotFound):
            fetch_consumptions("B-99999")

    def test_unavailable_dummy_raises_unavailable(self):
        set_mode(self.client, "orgatex", "unavailable")

        with (
            self.assertLogs(LOGGER, "WARNING") as logs,
            self.assertRaises(OrgatexUnavailable),
        ):
            fetch_consumptions("B-24187")

        self.assertIn("/api/batches/B-24187/consumption", logs.output[0])


class MalformedConsumptionTests(SimpleTestCase):
    def read(self, body):
        with patch("orgatex.adapter.urlopen", return_value=_FakeResponse(body)):
            return fetch_consumptions("B-24187")

    def assert_unavailable(self, body):
        with self.assertLogs(LOGGER, "WARNING"), self.assertRaises(OrgatexUnavailable):
            self.read(body)

    def test_float_quantity_is_rejected(self):
        self.assert_unavailable(
            b'{"batchId": "B-24187", "consumptions": [{"idempotencyKey": "k", '
            b'"acceptedAt": "2026-11-23T10:00:00+00:00", '
            b'"components": [{"code": "DYE-4471", "actualQty": 94.2, "unit": "g"}]}]}'
        )

    def test_non_iso_time_is_rejected(self):
        self.assert_unavailable(
            b'{"batchId": "B-24187", "consumptions": [{"idempotencyKey": "k", '
            b'"acceptedAt": "yesterday", "components": []}]}'
        )

    def test_consumptions_of_another_batch_are_rejected(self):
        self.assert_unavailable(b'{"batchId": "B-24188", "consumptions": []}')

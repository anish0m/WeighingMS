"""Stories 001-read-live-scale-weight, 002-tare-command, 005 (scale side).

The scale adapter reads the seeded Dummy Scale over real HTTP.
"""

from datetime import datetime
from decimal import Decimal
from unittest.mock import patch
from urllib.request import urlopen

from django.test import LiveServerTestCase, SimpleTestCase, override_settings

from devices import scale
from devices.scale import ScaleDisconnected, ScaleReading, ScaleUnavailable
from dummy_orgatex.services import seed_training_scenario
from tests.helpers import post_json, set_mode

LOGGER = "devices"


class LiveScaleTestCase(LiveServerTestCase):
    def setUp(self):
        seed_training_scenario()
        self.enterContext(
            override_settings(SCALE_BASE_URL=f"{self.live_server_url}/api")
        )

    def simulate(self, scale_id, body):
        response = post_json(
            self.client, f"/api/training/scales/{scale_id}/simulate", body
        )
        self.assertEqual(response.status_code, 200)


class ReadWeightTests(LiveScaleTestCase):
    def test_reading_is_decimal_with_unit_and_ready(self):
        self.simulate("scale-3kg", {"action": "set", "weight": "90.0", "unit": "g"})

        reading = scale.read_weight("scale-3kg")

        self.assertIsInstance(reading, ScaleReading)
        self.assertIsInstance(reading.net_weight, Decimal)
        self.assertEqual(reading.net_weight, Decimal("90.0"))
        self.assertEqual((reading.unit, reading.status), ("g", "ready"))
        self.assertIsInstance(reading.read_at, datetime)

    def test_floor_scale_reads_in_kg(self):
        self.simulate("scale-32kg", {"action": "set", "weight": "24.048", "unit": "kg"})

        reading = scale.read_weight("scale-32kg")

        self.assertEqual((reading.net_weight, reading.unit), (Decimal("24.048"), "kg"))

    def test_next_read_returns_the_new_weight(self):
        self.simulate("scale-3kg", {"action": "set", "weight": "90.0", "unit": "g"})
        scale.read_weight("scale-3kg")
        self.simulate("scale-3kg", {"action": "set", "weight": "94.2", "unit": "g"})

        self.assertEqual(scale.read_weight("scale-3kg").net_weight, Decimal("94.2"))

    def test_only_the_requested_scale_is_read(self):
        with patch("devices.http.urlopen", wraps=urlopen) as opened:
            scale.read_weight("scale-32kg")

        urls = [call.args[0].full_url for call in opened.call_args_list]
        self.assertEqual(urls, [f"{self.live_server_url}/api/scales/scale-32kg/weight"])

    def test_status_is_ready(self):
        self.assertEqual(scale.read_status("scale-3kg"), "ready")


class TareTests(LiveScaleTestCase):
    def test_tare_sets_net_weight_to_zero(self):
        self.simulate("scale-3kg", {"action": "set", "weight": "214", "unit": "g"})

        reading = scale.tare("scale-3kg")

        self.assertEqual(reading.net_weight, Decimal(0))
        self.assertEqual(scale.read_weight("scale-3kg").net_weight, Decimal(0))

    def test_tare_on_disconnected_scale_fails_and_tares_nothing(self):
        self.simulate("scale-3kg", {"action": "set", "weight": "214", "unit": "g"})
        set_mode(self.client, "scale-3kg", "disconnected")

        with self.assertLogs(LOGGER, "WARNING"), self.assertRaises(ScaleDisconnected):
            scale.tare("scale-3kg")

        set_mode(self.client, "scale-3kg", "ok")
        self.assertEqual(scale.read_weight("scale-3kg").net_weight, Decimal(214))


class DisconnectedTests(LiveScaleTestCase):
    def test_disconnected_scale_gives_no_weight(self):
        set_mode(self.client, "scale-3kg", "disconnected")

        with (
            self.assertLogs(LOGGER, "WARNING") as logs,
            self.assertRaises(ScaleDisconnected) as caught,
        ):
            scale.read_weight("scale-3kg")

        self.assertEqual(caught.exception.scale_id, "scale-3kg")
        line = logs.output[0]
        self.assertIn(f"{self.live_server_url}/api/scales/scale-3kg/weight", line)
        self.assertIn("503", line)
        self.assertIn("SCALE_DISCONNECTED", line)

    def test_disconnected_status_is_not_ready(self):
        set_mode(self.client, "scale-3kg", "disconnected")

        self.assertEqual(scale.read_status("scale-3kg"), "disconnected")

    def test_other_scale_is_unaffected(self):
        set_mode(self.client, "scale-3kg", "disconnected")

        self.assertEqual(scale.read_weight("scale-32kg").status, "ready")

    def test_reads_resume_when_scale_is_back(self):
        set_mode(self.client, "scale-3kg", "disconnected")
        with self.assertLogs(LOGGER, "WARNING"), self.assertRaises(ScaleDisconnected):
            scale.read_weight("scale-3kg")

        set_mode(self.client, "scale-3kg", "ok")

        self.assertEqual(scale.read_weight("scale-3kg").status, "ready")


class UnavailableTests(LiveScaleTestCase):
    def test_unknown_scale_is_unavailable(self):
        with self.assertLogs(LOGGER, "WARNING"), self.assertRaises(ScaleUnavailable):
            scale.read_weight("scale-9kg")

    def test_unreachable_scale_is_unavailable_not_disconnected(self):
        with (
            override_settings(SCALE_BASE_URL="http://127.0.0.1:9/api"),
            self.assertLogs(LOGGER, "WARNING") as logs,
            self.assertRaises(ScaleUnavailable),
        ):
            scale.read_weight("scale-3kg")

        self.assertIn("http://127.0.0.1:9/api/scales/scale-3kg/weight", logs.output[0])


class _FakeResponse:
    def __init__(self, body):
        self._body = body.encode()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return self._body


WEIGHT_BODY = (
    '{"scaleId": "%s", "netWeight": %s, "unit": "g", "status": "ready", '
    '"readAt": "2026-11-20T08:00:00+00:00"}'
)


@override_settings(SCALE_BASE_URL="http://scale.test/api")
class MalformedResponseTests(SimpleTestCase):
    """Stubbed at the HTTP boundary only (coding standards: mocks at boundaries)."""

    def read_with(self, body):
        with patch("devices.http.urlopen", return_value=_FakeResponse(body)):
            return scale.read_weight("scale-3kg")

    def assert_unavailable(self, body):
        with (
            self.assertLogs(LOGGER, "WARNING") as logs,
            self.assertRaises(ScaleUnavailable),
        ):
            self.read_with(body)
        self.assertIn("malformed", logs.output[0])

    def test_valid_stub_parses(self):
        reading = self.read_with(WEIGHT_BODY % ("scale-3kg", '"94.2"'))

        self.assertEqual(reading.net_weight, Decimal("94.2"))

    def test_float_weight_is_rejected(self):
        self.assert_unavailable(WEIGHT_BODY % ("scale-3kg", "94.2"))

    def test_reading_from_another_scale_is_rejected(self):
        self.assert_unavailable(WEIGHT_BODY % ("scale-32kg", '"94.2"'))

    def test_unknown_status_is_rejected(self):
        self.assert_unavailable(
            (WEIGHT_BODY % ("scale-3kg", '"94.2"')).replace("ready", "settling")
        )

    def test_non_json_body_is_rejected(self):
        self.assert_unavailable("<html>indicator error</html>")

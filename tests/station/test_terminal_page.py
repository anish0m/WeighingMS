"""Story 007/001: the terminal page carries configuration, never scenario data."""

from django.test import Client, TestCase, override_settings

from tests.station.test_no_hard_coded_data import SEED_VALUES

TERMINAL = "/"


class TerminalPageTests(TestCase):
    def test_terminal_renders_with_the_station_name(self):
        response = self.client.get(TERMINAL)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "WeighingMS")
        self.assertContains(response, "STATION 01")

    @override_settings(STATION_NAME="STATION 02")
    def test_station_name_is_configuration(self):
        self.assertContains(self.client.get(TERMINAL), "STATION 02")

    def test_page_carries_a_csrf_token_for_the_station_api(self):
        response = self.client.get(TERMINAL)

        self.assertContains(response, '<meta name="csrf-token" content="')
        self.assertIn("csrftoken", response.cookies)

    def test_alpine_is_served_locally(self):
        html = self.client.get(TERMINAL).content.decode()

        self.assertIn("/static/station/vendor/alpine.min.js", html)
        self.assertNotIn("cdn.", html)
        self.assertNotIn("unpkg", html)

    def test_clients_load_before_the_terminal_component(self):
        html = self.client.get(TERMINAL).content.decode()

        order = [
            "orgatex/orgatex-client.js",
            "devices/device-status.js",
            "devices/scanner-client.js",
            "station/station-client.js",
            "station/training-client.js",
            "station/weigh.js",
            "station/training-panel.js",
            "station/terminal.js",
            "station/vendor/alpine.min.js",
        ]
        positions = [html.index(name) for name in order]
        self.assertEqual(positions, sorted(positions))

    def test_training_panel_is_marked_and_outside_the_device(self):
        """Story 007/008 AC 3: training-only and separate from operator controls."""
        html = self.client.get(TERMINAL).content.decode()

        panel = html.index('data-testid="training-panel"')
        self.assertGreater(panel, html.index('data-testid="status-bar"'))
        self.assertIn("TRAINING ONLY", html[panel:])
        self.assertNotIn("TRAINING ONLY", html[:panel])
        self.assertNotIn("{#", html)  # no template comment leaks into the page

    def test_view_2_keys_and_supervisor_override(self):
        html = self.client.get(TERMINAL).content.decode()

        for label in ("OK · Confirm", "Re-tare", "Quit", "Supervisor override"):
            with self.subTest(label=label):
                self.assertIn(label, html)
        override = html[html.index('data-testid="btn-override"') :]
        self.assertIn("disabled", override[: override.index(">")])

    def test_rendered_page_contains_no_scenario_data(self):
        html = self.client.get(TERMINAL).content.decode()

        for value in SEED_VALUES:
            with self.subTest(value=value):
                self.assertNotIn(value, html)

    def test_page_accepts_only_get(self):
        self.assertEqual(Client().post(TERMINAL).status_code, 405)

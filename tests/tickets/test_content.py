"""Story 001-print-weighing-ticket: the ticket text (prototype layout, training).

Pure tests of ``tickets.content``; values are the stored ones, only formatted.
"""

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace

from django.test import SimpleTestCase, override_settings

from tickets.content import TicketData, barcode_text, build_ticket, line_of

ROWS = (
    ("Remazol Brill. Blue RSPL", "1240.0000", "1241.5000", "g"),
    ("Remazol Red RB", "386.0000", "385.4000", "g"),
    ("Remazol Yellow RGB", "94.0000", "94.2000", "g"),
    ("Sodium Sulphate", "24.0000", "23.9800", "kg"),
    ("Soda Ash", "9.6000", "9.6210", "kg"),
)
COMPLETED = datetime(2026, 11, 24, 3, 46, 12, tzinfo=UTC)


def stored_record(name, target, actual, unit):
    return SimpleNamespace(
        component_name=name,
        target=Decimal(target),
        actual_weight=Decimal(actual),
        unit=unit,
    )


def data(all_within=True):
    return TicketData(
        batch_id="B-24187",
        order_id="SO-9931",
        machine="JET-04",
        shade="Teal 4C",
        completed_at=COMPLETED,
        operator_name="R. Karim",
        lines=tuple(line_of(stored_record(*row)) for row in ROWS),
        all_within=all_within,
    )


class TicketContentTests(SimpleTestCase):
    def lines(self, reprint=False, all_within=True):
        return build_ticket(data(all_within), reprint).splitlines()

    def test_prototype_layout_in_order(self):
        """Story 001 AC 1: every listed field, in the prototype's order."""
        lines = [line.strip() for line in self.lines()]
        rule = "-" * len(max(self.lines(), key=len))

        self.assertEqual(
            lines,
            [
                "FCI DYEING — WEIGHING TICKET",
                rule,
                "BATCH   B-24187",
                "ORDER   SO-9931",
                "MACHINE JET-04",
                "SHADE   Teal 4C",
                "DATE    2026-11-24 03:46",
                "OPER.   R. Karim",
                rule,
                "COMPONENT                    TGT     ACT",
                "Remazol Brill. Blue RSPL  1240.0  1241.5 g",
                "Remazol Red RB             386.0   385.4 g",
                "Remazol Yellow RGB          94.0    94.2 g",
                "Sodium Sulphate           24.000  23.980 kg",
                "Soda Ash                   9.600   9.621 kg",
                rule,
                "ALL WITHIN TOLERANCE",
                "*B-24187*",
                "B-24187",
            ],
        )

    def test_values_are_the_stored_ones_at_display_resolution(self):
        """Story 001 AC 3: target and actual from the record, not recomputed."""
        line = line_of(stored_record("Sodium Sulphate", "24.0000", "23.9800", "kg"))

        self.assertEqual(
            (line.target, line.actual, line.unit), ("24.000", "23.980", "kg")
        )

    def test_reprint_is_marked_on_the_first_line(self):
        """Story 002 AC 1."""
        lines = self.lines(reprint=True)

        self.assertEqual(lines[0].strip(), "*** REPRINT ***")
        self.assertEqual(lines[1:], self.lines())
        self.assertNotIn("REPRINT", build_ticket(data(), False))

    def test_not_all_within(self):
        self.assertIn("NOT ALL WITHIN TOLERANCE", self.lines(all_within=False)[16])

    def test_barcode_is_code_39_text(self):
        self.assertEqual(barcode_text("B-24187"), "*B-24187*")

    def test_rule_spans_the_widest_line_and_lines_end_without_spaces(self):
        text = build_ticket(data(), True)

        lines = text.splitlines()
        self.assertTrue(text.endswith("\n"))
        self.assertEqual(len(lines[2]), max(len(line) for line in lines))
        self.assertTrue(all(line == line.rstrip() for line in lines))

    @override_settings(TIME_ZONE="Asia/Dhaka")
    def test_date_uses_the_server_time_zone(self):
        self.assertIn("DATE    2026-11-24 09:46", build_ticket(data(), False))

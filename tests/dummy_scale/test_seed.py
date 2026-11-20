"""Story 001-seed-training-scenario (AC 3): both Dummy scales are seeded."""

from decimal import Decimal

from django.test import TestCase

from dummy_orgatex.services import seed_training_scenario
from dummy_scale.models import DummyScale


class SeedScalesTests(TestCase):
    def setUp(self):
        seed_training_scenario()

    def test_seed_creates_both_scales_ready_at_zero(self):
        scales = {s.scale_id: s for s in DummyScale.objects.all()}

        self.assertEqual(set(scales), {"scale-3kg", "scale-32kg"})
        for scale in scales.values():
            with self.subTest(scale=scale.scale_id):
                self.assertEqual(scale.status, "ready")
                self.assertEqual(scale.net_weight, Decimal(0))

    def test_scale_capacities_and_units_match_the_prototype(self):
        scales = {s.scale_id: (s.capacity, s.unit) for s in DummyScale.objects.all()}

        # 3 kg precision scale reports in g, 32 kg floor scale in kg (bolt 002).
        self.assertEqual(scales["scale-3kg"], (Decimal(3000), "g"))
        self.assertEqual(scales["scale-32kg"], (Decimal(32), "kg"))

    def test_reseed_does_not_duplicate_scales(self):
        seed_training_scenario()

        self.assertEqual(DummyScale.objects.count(), 2)

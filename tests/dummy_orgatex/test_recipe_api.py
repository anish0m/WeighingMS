"""Story 003-dummy-orgatex-recipe-endpoint."""

from decimal import Decimal

from django.test import TestCase

from dummy_orgatex.services import seed_training_scenario

QUANTITY_KEYS = ("targetQty", "tolerance", "displayMax", "tare")

# code -> (targetQty, unit, tolerance, displayMax, lot, container, tare)
EXPECTED = {
    "DYE-1180": ("1240.0", "g", "6.0", "1600", "2026-0341", "C-09", "214"),
    "DYE-2204": ("386.0", "g", "2.0", "520", "2026-0298", "C-11", "214"),
    "DYE-4471": ("94.0", "g", "0.5", "125", "2026-0387", "C-12", "214"),
    "AUX-0101": ("24.000", "kg", "0.120", "32", "2026-0112", "D-03", "1.850"),
    "AUX-0107": ("9.600", "kg", "0.048", "14", "2026-0155", "D-05", "1.850"),
}


class RecipeApiTests(TestCase):
    def setUp(self):
        seed_training_scenario()

    def test_b24187_recipe_is_teal_4c_with_five_components_in_sequence(self):
        response = self.client.get("/api/batches/B-24187/recipe")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["batchId"], "B-24187")
        self.assertEqual(body["recipeName"], "Teal 4C")
        self.assertEqual([c["sequence"] for c in body["components"]], [1, 2, 3, 4, 5])
        self.assertEqual([c["code"] for c in body["components"]], list(EXPECTED))

    def test_component_values_equal_the_prototype(self):
        components = self.client.get("/api/batches/B-24187/recipe").json()["components"]

        for comp in components:
            target, unit, tol, dmax, lot, cont, tare = EXPECTED[comp["code"]]
            with self.subTest(code=comp["code"]):
                self.assertEqual(Decimal(comp["targetQty"]), Decimal(target))
                self.assertEqual(comp["unit"], unit)
                self.assertEqual(Decimal(comp["tolerance"]), Decimal(tol))
                self.assertEqual(Decimal(comp["displayMax"]), Decimal(dmax))
                self.assertEqual(comp["lot"], lot)
                self.assertEqual(comp["container"], cont)
                self.assertEqual(Decimal(comp["tare"]), Decimal(tare))
                self.assertEqual(comp["state"], "pending")

    def test_quantities_are_json_strings_not_numbers(self):
        components = self.client.get("/api/batches/B-24187/recipe").json()["components"]

        for comp in components:
            for key in QUANTITY_KEYS:
                with self.subTest(code=comp["code"], key=key):
                    self.assertIsInstance(comp[key], str)

    def test_component_carries_name_and_colour(self):
        yellow = self.client.get("/api/batches/B-24187/recipe").json()["components"][2]

        self.assertEqual(yellow["name"], "Remazol Yellow RGB")
        self.assertEqual(yellow["colour"], "#d9a520")

    def test_batch_without_recipe_returns_recipe_not_available(self):
        for batch_id in ("B-24188", "B-24190", "B-24191"):
            with self.subTest(batch=batch_id):
                response = self.client.get(f"/api/batches/{batch_id}/recipe")

                self.assertEqual(response.status_code, 404)
                error = response.json()["error"]
                self.assertEqual(error["code"], "RECIPE_NOT_AVAILABLE")
                self.assertEqual(
                    error["message"], "Recipe not available in training data"
                )
                self.assertNotIn("components", response.json())

    def test_recipe_of_unknown_batch_returns_batch_not_found(self):
        response = self.client.get("/api/batches/B-99999/recipe")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "BATCH_NOT_FOUND")

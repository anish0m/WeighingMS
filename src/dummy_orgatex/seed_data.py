"""Training scenario copied from the prototype docs/customize-weighing-station.html.

Queue rows come from the prototype's View 1 table, the recipe from its
``components`` array. Nothing here is invented. Quantities are strings so they
become exact Decimals.

Training defaults accepted at CHECKPOINT 2:
- OQ-5: only B-24187 has a recipe.
- OQ-6: every component starts pending; the prototype's actuals are not seeded.
- OQ-7: lot and container are supplied per component by this seed.
"""

BATCHES = [
    {
        "batch_id": "B-24187",
        "order_id": "SO-9931",
        "machine": "JET-04",
        "fabric_lot": "100% CTN knit · 480 kg",
        "shade": "Teal 4C",
        "component_count": 5,
    },
    {
        "batch_id": "B-24188",
        "order_id": "SO-9931",
        "machine": "JET-07",
        "fabric_lot": "100% CTN knit · 520 kg",
        "shade": "Teal 4C",
        "component_count": 5,
    },
    {
        "batch_id": "B-24190",
        "order_id": "SO-9944",
        "machine": "JET-02",
        "fabric_lot": "CVC fleece · 310 kg",
        "shade": "Navy 12",
        "component_count": 7,
    },
    {
        "batch_id": "B-24191",
        "order_id": "SO-9947",
        "machine": "WINCH-01",
        "fabric_lot": "Viscose jersey · 190 kg",
        "shade": "Rose 08",
        "component_count": 4,
    },
]

RECIPES = {
    "B-24187": {
        "name": "Teal 4C",
        "components": [
            {
                "code": "DYE-1180",
                "name": "Remazol Brill. Blue RSPL",
                "colour": "#1f4fa8",
                "target_qty": "1240.0",
                "unit": "g",
                "tolerance": "6.0",
                "display_max": "1600",
                "lot": "2026-0341",
                "container": "C-09",
                "tare": "214",
            },
            {
                "code": "DYE-2204",
                "name": "Remazol Red RB",
                "colour": "#b8253a",
                "target_qty": "386.0",
                "unit": "g",
                "tolerance": "2.0",
                "display_max": "520",
                "lot": "2026-0298",
                "container": "C-11",
                "tare": "214",
            },
            {
                "code": "DYE-4471",
                "name": "Remazol Yellow RGB",
                "colour": "#d9a520",
                "target_qty": "94.0",
                "unit": "g",
                "tolerance": "0.5",
                "display_max": "125",
                "lot": "2026-0387",
                "container": "C-12",
                "tare": "214",
            },
            {
                "code": "AUX-0101",
                "name": "Sodium Sulphate",
                "colour": "#c9d2dc",
                "target_qty": "24.000",
                "unit": "kg",
                "tolerance": "0.120",
                "display_max": "32",
                "lot": "2026-0112",
                "container": "D-03",
                "tare": "1.850",
            },
            {
                "code": "AUX-0107",
                "name": "Soda Ash",
                "colour": "#e4eaf0",
                "target_qty": "9.600",
                "unit": "kg",
                "tolerance": "0.048",
                "display_max": "14",
                "lot": "2026-0155",
                "container": "D-05",
                "tare": "1.850",
            },
        ],
    },
}

# Scale names and capacities from the prototype status bar ("SCALE 3 kg",
# "SCALE 32 kg") and its scale labels ("3 kg precision", "32 kg floor").
SCALES = [
    {
        "scale_id": "scale-3kg",
        "name": "3 kg precision",
        "capacity": "3",
        "unit": "kg",
    },
    {
        "scale_id": "scale-32kg",
        "name": "32 kg floor",
        "capacity": "32",
        "unit": "kg",
    },
]

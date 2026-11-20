from django.core.management.base import BaseCommand

from dummy_orgatex.services import seed_training_scenario


class Command(BaseCommand):
    help = (
        "Load (or reset to) the prototype training scenario into Dummy OrgaTEX "
        "and Dummy Scale."
    )

    def handle(self, *args, **options):
        seed_training_scenario()
        self.stdout.write(
            self.style.SUCCESS(
                "Seeded: 4 batches, recipe Teal 4C (5 components), "
                "scales scale-3kg and scale-32kg."
            )
        )

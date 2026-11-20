from django.apps import AppConfig


class DummyScannerConfig(AppConfig):
    """Dummy Scanner: training substitute for the barcode scanner."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "dummy_scanner"
    verbose_name = "Dummy Scanner (training contract)"

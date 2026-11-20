from django.apps import AppConfig


class DummyPrinterConfig(AppConfig):
    """Dummy Printer: training substitute for the ticket printer."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "dummy_printer"
    verbose_name = "Dummy Printer (training contract)"

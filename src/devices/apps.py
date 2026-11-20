from django.apps import AppConfig


class DevicesConfig(AppConfig):
    """Device integrations: one adapter module per device (IR-07)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "devices"
    verbose_name = "Device integrations"

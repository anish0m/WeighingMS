from django.apps import AppConfig


class WeighingConfig(AppConfig):
    """Weighing Station: operator/supervisor identity and weighing sessions."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "weighing"
    verbose_name = "Weighing station"

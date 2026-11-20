from django.apps import AppConfig


class StationConfig(AppConfig):
    """Operator terminal UI: templates and static files only (unit 007)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "station"
    verbose_name = "Operator terminal"

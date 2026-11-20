from django.apps import AppConfig


class DummyOrgatexConfig(AppConfig):
    """Dummy OrgaTEX: training substitute, not the real OrgaTEX interface."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "dummy_orgatex"
    verbose_name = "Dummy OrgaTEX (training contract)"

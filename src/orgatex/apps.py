from django.apps import AppConfig


class OrgatexConfig(AppConfig):
    """OrgaTEX integration: the only WeighingMS code that knows OrgaTEX (IR-07)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "orgatex"
    verbose_name = "OrgaTEX integration"

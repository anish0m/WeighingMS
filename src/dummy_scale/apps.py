from django.apps import AppConfig


class DummyScaleConfig(AppConfig):
    """Dummy Scale: training substitute for the 3 kg and 32 kg scales."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "dummy_scale"
    verbose_name = "Dummy Scale (training contract)"

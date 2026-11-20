from django.apps import AppConfig


class BatchesConfig(AppConfig):
    """Batch & Recipe: batch selection and the read-only recipe snapshot."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "batches"
    verbose_name = "Batch & recipe management"

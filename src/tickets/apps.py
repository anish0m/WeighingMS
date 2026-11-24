from django.apps import AppConfig


class TicketsConfig(AppConfig):
    """Weighing ticket of a completed batch: content, print log, reprint (unit 006)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "tickets"
    verbose_name = "Ticket and printing"

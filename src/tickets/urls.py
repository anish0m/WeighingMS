"""Weighing ticket endpoints (unit 006, bolt 016) under /station/api/."""

from django.urls import path

from tickets import views

app_name = "tickets"

urlpatterns = [
    path(
        "sessions/<int:session_id>/ticket",
        views.ticket_preview,
        name="ticket-preview",
    ),
    path(
        "sessions/<int:session_id>/ticket/prints",
        views.ticket_print,
        name="ticket-print",
    ),
    path(
        "sessions/<int:session_id>/ticket/prints/<int:job_id>/result",
        views.ticket_print_result,
        name="ticket-print-result",
    ),
]

from django.urls import path

from dummy_printer import views

app_name = "dummy_printer"

urlpatterns = [
    path("printer/status", views.printer_status, name="printer-status"),
    path("tickets", views.ticket_create, name="ticket-create"),
    path("tickets/<int:ticket_id>", views.ticket_detail, name="ticket-detail"),
]

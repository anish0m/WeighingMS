"""The operator terminal page (unit 007)."""

from django.urls import path

from station import views

app_name = "station"

urlpatterns = [
    path("", views.terminal, name="terminal"),
]

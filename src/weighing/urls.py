"""WeighingMS station API: identity and weighing sessions (ADR-002, ADR-005)."""

from django.urls import path

from weighing import views

app_name = "weighing"

urlpatterns = [
    path("operators", views.operators, name="operators"),
    path("operator", views.current_operator, name="operator"),
    path("sessions", views.sessions, name="sessions"),
    path("sessions/<int:session_id>", views.session_detail, name="session-detail"),
]

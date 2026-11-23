"""WeighingMS station API: identity, sessions, dyestuff checks, weighing rules
(ADR-002, -005, -006, -008)."""

from django.urls import path

from weighing import views

app_name = "weighing"

urlpatterns = [
    path("operators", views.operators, name="operators"),
    path("operator", views.current_operator, name="operator"),
    path("sessions", views.sessions, name="sessions"),
    path("sessions/<int:session_id>", views.session_detail, name="session-detail"),
    path(
        "sessions/<int:session_id>/components",
        views.session_components,
        name="session-components",
    ),
    path(
        "sessions/<int:session_id>/components/<int:sequence>/identity",
        views.component_identity,
        name="component-identity",
    ),
    path(
        "sessions/<int:session_id>/components/<int:sequence>/evaluation",
        views.component_evaluation,
        name="component-evaluation",
    ),
]

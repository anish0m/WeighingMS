"""WeighingMS station API: identity, sessions, dyestuff checks, weighing rules,
confirmation, progression and OrgaTEX write-back (ADR-002, -005, -006, -008,
-010, -011)."""

from django.urls import path

from weighing import views

app_name = "weighing"

urlpatterns = [
    path("operators", views.operators, name="operators"),
    path("operator", views.current_operator, name="operator"),
    path("sessions", views.sessions, name="sessions"),
    path("current-session", views.current_session, name="current-session"),
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
    path(
        "sessions/<int:session_id>/progress",
        views.session_progress,
        name="session-progress",
    ),
    path(
        "sessions/<int:session_id>/components/<int:sequence>/activate",
        views.component_activate,
        name="component-activate",
    ),
    path(
        "sessions/<int:session_id>/components/<int:sequence>/tare",
        views.component_tare,
        name="component-tare",
    ),
    path(
        "sessions/<int:session_id>/components/<int:sequence>/quit",
        views.component_quit,
        name="component-quit",
    ),
    path(
        "sessions/<int:session_id>/components/<int:sequence>/confirm",
        views.component_confirm,
        name="component-confirm",
    ),
    path(
        "sessions/<int:session_id>/write-back",
        views.session_write_back,
        name="session-write-back",
    ),
    path(
        "sessions/<int:session_id>/write-back/result",
        views.session_write_back_result,
        name="session-write-back-result",
    ),
]

"""WeighingMS station API: batch selection (mounted at /station/api/, ADR-002)."""

from django.urls import path

from batches import views

app_name = "batches"

urlpatterns = [
    path("selections", views.selections, name="selections"),
    path(
        "selections/<int:selection_id>",
        views.selection_detail,
        name="selection-detail",
    ),
]

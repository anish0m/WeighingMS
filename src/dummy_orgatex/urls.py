from django.urls import path

from dummy_orgatex import views

app_name = "dummy_orgatex"

urlpatterns = [
    path("batches", views.batch_list, name="batch-list"),
    path("batches/<str:batch_id>", views.batch_detail, name="batch-detail"),
    path("batches/<str:batch_id>/recipe", views.batch_recipe, name="batch-recipe"),
    path(
        "batches/<str:batch_id>/consumption",
        views.batch_consumption,
        name="batch-consumption",
    ),
]

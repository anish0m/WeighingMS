from django.urls import path

from dummy_scale import views

app_name = "dummy_scale"

urlpatterns = [
    path("scales", views.scale_list, name="scale-list"),
    path("scales/<str:scale_id>/status", views.scale_status, name="scale-status"),
    path("scales/<str:scale_id>/weight", views.scale_weight, name="scale-weight"),
    path("scales/<str:scale_id>/tare", views.scale_tare, name="scale-tare"),
]

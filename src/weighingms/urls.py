"""Root URL configuration.

Contract endpoints of the Dummy integrations are mounted under /api/.
Training-only controls (simulate, failure modes) are under /api/training/.
WeighingMS's own endpoints are under /station/api/ (ADR-002).
The operator terminal page is served at /.
"""

from django.urls import include, path

from dummy_scale import views as scale_views
from dummy_scanner import views as scanner_views
from weighingms import training

training_urlpatterns = [
    path(
        "scales/<str:scale_id>/simulate",
        scale_views.scale_simulate,
        name="scale-simulate",
    ),
    path("scanner/scans", scanner_views.simulate_scan, name="scanner-simulate"),
    path("modes", training.modes, name="modes"),
    path("modes/<str:target>", training.set_mode, name="mode-set"),
]

urlpatterns = [
    path("api/training/", include((training_urlpatterns, "training"))),
    path("api/", include("dummy_orgatex.urls")),
    path("api/", include("dummy_scale.urls")),
    path("api/", include("dummy_scanner.urls")),
    path("api/", include("dummy_printer.urls")),
    path("station/api/", include("batches.urls")),
    path("station/api/", include("weighing.urls")),
    path("", include("station.urls")),
]

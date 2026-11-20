from django.urls import path

from dummy_scanner import views

app_name = "dummy_scanner"

urlpatterns = [
    path("scanner/status", views.scanner_status, name="scanner-status"),
    path("scanner/scans/latest", views.latest_scan, name="scanner-latest-scan"),
]

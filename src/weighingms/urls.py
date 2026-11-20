"""Root URL configuration.

The Dummy OrgaTEX training contract is mounted under /api/.
"""

from django.urls import include, path

urlpatterns = [
    path("api/", include("dummy_orgatex.urls")),
]

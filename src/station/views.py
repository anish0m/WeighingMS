"""Renders the operator terminal shell.

The page carries configuration only (station name, CSRF token). All scenario
data (operators, batches, recipes, device states) is fetched by the browser
from the APIs at runtime (FR-21).
"""

from django.conf import settings
from django.shortcuts import render
from django.views.decorators.http import require_GET


@require_GET
def terminal(request):
    return render(
        request, "station/terminal.html", {"station_name": settings.STATION_NAME}
    )

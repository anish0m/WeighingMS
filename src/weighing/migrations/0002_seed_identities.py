"""Seed the training identities (OQ-3, ADR-004).

TRAINING DATA ONLY. R. Karim · Shift A comes from the prototype header. The
supervisor ID, name and PIN are training values chosen for this build (the
prototype gives none); a real station uses the FCI directory instead (A-09).
Only a hash of the PIN is stored.
"""

from django.contrib.auth.hashers import make_password
from django.db import migrations

OPERATORS = (("OP-01", "R. Karim", "A"),)
SUPERVISORS = (("SUP-01", "Training Supervisor", "2468"),)


def seed(apps, schema_editor):
    Operator = apps.get_model("weighing", "Operator")
    Supervisor = apps.get_model("weighing", "Supervisor")
    for operator_id, name, shift in OPERATORS:
        Operator.objects.create(operator_id=operator_id, name=name, shift=shift)
    for supervisor_id, name, pin in SUPERVISORS:
        Supervisor.objects.create(
            supervisor_id=supervisor_id, name=name, pin_hash=make_password(pin)
        )


def unseed(apps, schema_editor):
    apps.get_model("weighing", "Operator").objects.filter(
        operator_id__in=[o[0] for o in OPERATORS]
    ).delete()
    apps.get_model("weighing", "Supervisor").objects.filter(
        supervisor_id__in=[s[0] for s in SUPERVISORS]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [("weighing", "0001_initial")]

    operations = [migrations.RunPython(seed, unseed)]

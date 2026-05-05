import random

from django.db import migrations, models


PIN_LENGTH = 4
PIN_SPACE_SIZE = 10**PIN_LENGTH


def _is_valid_pin(value):
    return bool(value and len(value) == PIN_LENGTH and str(value).isdigit())


def _allocate_pin(used_pins):
    if len({pin for pin in used_pins if _is_valid_pin(pin)}) >= PIN_SPACE_SIZE:
        raise RuntimeError("Nao ha PINs de 4 digitos disponiveis.")

    rng = random.SystemRandom()
    for _ in range(PIN_SPACE_SIZE):
        candidate = str(rng.randint(0, PIN_SPACE_SIZE - 1)).zfill(PIN_LENGTH)
        if candidate not in used_pins:
            used_pins.add(candidate)
            return candidate

    for number in range(PIN_SPACE_SIZE):
        candidate = str(number).zfill(PIN_LENGTH)
        if candidate not in used_pins:
            used_pins.add(candidate)
            return candidate

    raise RuntimeError("Nao ha PINs de 4 digitos disponiveis.")


def fix_duplicate_active_pins(apps, schema_editor):
    User = apps.get_model("user_django_app", "User")
    used_pins = set()
    users_to_update = []

    queryset = (
        User.objects.filter(deleted_at__isnull=True)
        .only("id", "pin")
        .order_by("pin", "id")
    )
    for user in queryset:
        pin = (user.pin or "").strip()
        if _is_valid_pin(pin) and pin not in used_pins:
            used_pins.add(pin)
            continue

        user.pin = _allocate_pin(used_pins)
        users_to_update.append(user)

    if users_to_update:
        User.objects.bulk_update(users_to_update, ["pin"], batch_size=500)


class Migration(migrations.Migration):
    dependencies = [
        ("user_django_app", "0021_visitas_card_finished_fields"),
    ]

    operations = [
        migrations.RunPython(fix_duplicate_active_pins, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="user",
            constraint=models.UniqueConstraint(
                fields=("pin",),
                condition=models.Q(deleted_at__isnull=True),
                name="unique_active_user_pin",
            ),
        ),
    ]

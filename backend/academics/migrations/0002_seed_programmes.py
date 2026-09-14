from django.db import migrations


def seed_programmes(apps, schema_editor):
    Programme = apps.get_model("academics", "Programme")

    programmes = [
        {"name": "Nursery", "level": "Pre-Primary", "duration": "1 Year", "order": 0},
        {"name": "LKG", "level": "Pre-Primary", "duration": "1 Year", "order": 1},
        {"name": "UKG", "level": "Pre-Primary", "duration": "1 Year", "order": 2},
        {"name": "Class 1", "level": "Primary", "duration": "1 Year", "order": 3},
        {"name": "Class 2", "level": "Primary", "duration": "1 Year", "order": 4},
        {"name": "Class 3", "level": "Primary", "duration": "1 Year", "order": 5},
        {"name": "Class 4", "level": "Primary", "duration": "1 Year", "order": 6},
        {"name": "Class 5", "level": "Primary", "duration": "1 Year", "order": 7},
        {"name": "Class 6", "level": "Lower Secondary", "duration": "1 Year", "order": 8},
        {"name": "Class 7", "level": "Lower Secondary", "duration": "1 Year", "order": 9},
        {"name": "Class 8", "level": "Lower Secondary", "duration": "1 Year", "order": 10},
        {"name": "Class 9", "level": "Secondary", "duration": "1 Year", "order": 11},
        {"name": "Class 10", "level": "Secondary", "duration": "1 Year", "order": 12},
    ]

    for data in programmes:
        Programme.objects.get_or_create(name=data["name"], defaults=data)


def remove_programmes(apps, schema_editor):
    Programme = apps.get_model("academics", "Programme")
    name_prefixes = ["Nursery", "LKG", "UKG"]
    name_prefixes += [f"Class {n}" for n in range(1, 11)]
    Programme.objects.filter(name__in=name_prefixes).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("academics", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_programmes, remove_programmes),
    ]
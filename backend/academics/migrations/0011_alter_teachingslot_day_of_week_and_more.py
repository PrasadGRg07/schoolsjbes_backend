import django.db.models.deletion
from django.db import migrations, models


def flush_deferred_constraints(schema_editor):
    """
    Rows written above queue Postgres' deferred foreign key checks, and it
    refuses a following ALTER TABLE while any are still outstanding:

        cannot ALTER TABLE "academics_subject" because it has pending trigger events

    Running the pending checks now clears the queue, so the schema change in
    this same migration is allowed through.
    """
    schema_editor.execute('SET CONSTRAINTS ALL IMMEDIATE')


def text_subjects_into_rows(apps, schema_editor):
    """
    TeachingSlot.subject used to be free text. Turn each distinct name into a
    real Subject so the existing periods keep their subject instead of being
    wiped when the column becomes a foreign key.

    A Subject must belong to a Programme, so the programme of the class the
    period was for is used. Periods whose class has no programme are collected
    under a single holding programme, which the admin can rename or split later.
    """
    TeachingSlot = apps.get_model('academics', 'TeachingSlot')
    Subject = apps.get_model('academics', 'Subject')
    Programme = apps.get_model('academics', 'Programme')

    # The text column was renamed to subject_name before this runs, and subject
    # is already the new, empty foreign key. Read the old value by its real
    # name, or every period would be relabelled "Unnamed subject".
    existing = list(
        TeachingSlot.objects.values_list('id', 'subject_name', 'school_class_id')
    )

    holding, _ = Programme.objects.get_or_create(
        name='Subjects (migrated)',
        defaults={'level': '', 'description': 'Created when the timetable moved '
                                             'from typed subject names to real subjects.'},
    )

    programmes_by_class = {
        row['id']: row['programme_id']
        for row in apps.get_model('academics', 'SchoolClass')
        .objects.values('id', 'programme_id')
    }

    for slot_id, text_name, school_class_id in existing:
        name = (text_name or '').strip() or 'Unnamed subject'
        programme_id = programmes_by_class.get(school_class_id) or holding.id
        subject, _ = Subject.objects.get_or_create(
            programme_id=programme_id,
            name=name,
            defaults={'order': 0},
        )
        TeachingSlot.objects.filter(id=slot_id).update(subject_id=subject.id)

    flush_deferred_constraints(schema_editor)


def text_subjects_back_to_text(apps, schema_editor):
    """Reverse back to free text, using the subject's own name."""
    TeachingSlot = apps.get_model('academics', 'TeachingSlot')
    for slot in TeachingSlot.objects.select_related('subject').all().iterator():
        TeachingSlot.objects.filter(id=slot.id).update(
            subject_name=slot.subject.name if slot.subject else '',
        )
    flush_deferred_constraints(schema_editor)


class Migration(migrations.Migration):

    dependencies = [
        ('academics', '0010_alter_classteacher_school_class'),
    ]

    operations = [
        migrations.AlterField(
            model_name='teachingslot',
            name='day_of_week',
            field=models.PositiveSmallIntegerField(choices=[(0, 'Monday'), (1, 'Tuesday'), (2, 'Wednesday'), (3, 'Thursday'), (4, 'Friday'), (5, 'Saturday'), (6, 'Sunday')]),
        ),
        migrations.RenameField(
            model_name='teachingslot',
            old_name='subject',
            new_name='subject_name',
        ),
        migrations.AddField(
            model_name='teachingslot',
            name='subject',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='timetable_slots',
                to='academics.subject',
            ),
        ),
        migrations.RunPython(text_subjects_into_rows, text_subjects_back_to_text),
        migrations.AlterField(
            model_name='teachingslot',
            name='subject',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='timetable_slots',
                to='academics.subject',
            ),
        ),
    ]

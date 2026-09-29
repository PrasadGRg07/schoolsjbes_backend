from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('home_page', '0001_initial'),
    ]

    operations = [
        # Rich-text hero copy can outgrow a CharField once the editor writes
        # inline styles, so both fields are free-form text.
        migrations.AlterField(
            model_name='homehero',
            name='eyebrow',
            field=models.TextField(blank=True, default='Welcome to SJBEBS', help_text='Small line above the heading, e.g. "Welcome to SJBEBS".'),
        ),
        migrations.AlterField(
            model_name='homehero',
            name='heading',
            field=models.TextField(default='Nurturing Bright Minds,\nBuilding Futures', help_text='Main heading. Rich text: the admin editor stores HTML, so the font, size, colour and alignment of any word can be changed. Values saved before the editor existed are plain text with newlines, which are still rendered as line breaks.'),
        ),
    ]

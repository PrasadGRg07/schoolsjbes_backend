from django.db import models

DEFAULT_HEADING = 'Nurturing Bright Minds,\nBuilding Futures'

DEFAULT_INTRO = (
    'Shree Jaya Buddha English Boarding School — a premier institution '
    'committed to academic excellence and holistic student development.'
)

DEFAULT_STATS = [
    {'value': '25+', 'label': 'Years of Excellence'},
    {'value': '1200+', 'label': 'Students Enrolled'},
    {'value': '80+', 'label': 'Qualified Teachers'},
    {'value': '98%', 'label': 'Pass Rate'},
]


def default_stats():
    return [dict(stat) for stat in DEFAULT_STATS]


class HomeHero(models.Model):
    """Singleton — the hero banner at the top of the home page."""

    eyebrow = models.TextField(
        blank=True, default='Welcome to SJBEBS',
        help_text='Small line above the heading, e.g. "Welcome to SJBEBS".',
    )
    heading = models.TextField(
        default=DEFAULT_HEADING,
        help_text=(
            'Main heading. Rich text: the admin editor stores HTML, so the '
            'font, size, colour and alignment of any word can be changed. '
            'Values saved before the editor existed are plain text with '
            'newlines, which are still rendered as line breaks.'
        ),
    )
    heading_highlight = models.CharField(
        max_length=100, blank=True, default='Bright Minds',
        help_text='Words inside the heading that are shown in gold.',
    )
    intro = models.TextField(default=DEFAULT_INTRO, blank=True)
    primary_button_text = models.CharField(max_length=60, blank=True, default='Apply Now →')
    primary_button_url = models.CharField(max_length=300, blank=True, default='/admissions')
    secondary_button_text = models.CharField(max_length=60, blank=True, default='Discover Our School')
    secondary_button_url = models.CharField(max_length=300, blank=True, default='/about')
    stats = models.JSONField(
        default=default_stats, blank=True,
        help_text='List of {"value": "25+", "label": "Years of Excellence"} objects.',
    )
    show_stats = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Home Page Hero'
        verbose_name_plural = 'Home Page Hero'

    def __str__(self):
        return 'Home Page Hero'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

from django.db import models


class CoverCropMixin(models.Model):
    """How a cover image is framed when it is shown in a fixed-size box.

    A photo that does not match the shape of the box gets cropped, and the
    default centre crop regularly cuts faces or headings in half. `cover_ratio`
    picks the shape of the box; `cover_focus_x` / `cover_focus_y` record which
    part of the photo has to stay visible, as a 0-1 fraction of the image. That
    is exactly what CSS `object-position` expects, so the front end can apply it
    without any conversion.
    """

    COVER_RATIO_CHOICES = [
        ('landscape', 'Landscape (16:9)'),
        ('square', 'Square (1:1)'),
        ('portrait', 'Portrait (4:5)'),
        ('original', 'Original (no crop)'),
    ]

    cover_ratio = models.CharField(
        max_length=12, choices=COVER_RATIO_CHOICES, default='landscape',
    )
    cover_focus_x = models.FloatField(default=0.5)
    cover_focus_y = models.FloatField(default=0.5)

    class Meta:
        abstract = True

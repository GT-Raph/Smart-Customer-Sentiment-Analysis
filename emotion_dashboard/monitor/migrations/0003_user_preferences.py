from django.conf import settings
from django.db import migrations, models
import django.core.validators
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("monitor", "0002_remove_saas_tenancy"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserPreference",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "default_date_range",
                    models.CharField(
                        choices=[
                            ("day", "Today"),
                            ("week", "Last 7 days"),
                            ("14days", "Last 14 days"),
                            ("month", "Last 30 days"),
                        ],
                        default="14days",
                        max_length=10,
                    ),
                ),
                (
                    "default_hourly_range",
                    models.CharField(
                        choices=[("today", "Today"), ("yesterday", "Yesterday")],
                        default="today",
                        max_length=12,
                    ),
                ),
                (
                    "auto_refresh_seconds",
                    models.PositiveIntegerField(
                        choices=[
                            (0, "Disabled"),
                            (30, "Every 30 seconds"),
                            (60, "Every minute"),
                            (120, "Every 2 minutes"),
                            (300, "Every 5 minutes"),
                        ],
                        default=0,
                    ),
                ),
                ("compact_mode", models.BooleanField(default=False)),
                ("reduce_motion", models.BooleanField(default=False)),
                ("email_weekly_summary", models.BooleanField(default=False)),
                ("notify_negative", models.BooleanField(default=False)),
                (
                    "negative_threshold",
                    models.PositiveSmallIntegerField(
                        default=35,
                        validators=[
                            django.core.validators.MinValueValidator(1),
                            django.core.validators.MaxValueValidator(100),
                        ],
                    ),
                ),
                (
                    "minimum_detections",
                    models.PositiveIntegerField(
                        default=20,
                        validators=[
                            django.core.validators.MinValueValidator(1),
                            django.core.validators.MaxValueValidator(100000),
                        ],
                    ),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "default_branch",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="default_for_users",
                        to="monitor.branch",
                    ),
                ),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="preferences",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"db_table": "monitor_user_preference"},
        ),
    ]

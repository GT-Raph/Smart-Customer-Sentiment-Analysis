# Clean initial schema for the SaaS-ready version.

from django.conf import settings
import django.contrib.auth.models
import django.contrib.auth.validators
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    initial = True
    dependencies = [("auth", "0012_alter_user_first_name_max_length")]

    operations = [
        migrations.CreateModel(
            name="Organization",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=150)),
                ("slug", models.SlugField(max_length=80, unique=True)),
                ("plan", models.CharField(choices=[("free", "Free"), ("starter", "Starter"), ("business", "Business"), ("enterprise", "Enterprise")], default="free", max_length=20)),
                ("subscription_status", models.CharField(choices=[("trialing", "Trialing"), ("active", "Active"), ("past_due", "Past due"), ("suspended", "Suspended"), ("cancelled", "Cancelled")], default="trialing", max_length=20)),
                ("monthly_analysis_limit", models.PositiveIntegerField(default=1000, help_text="Use 0 for unlimited analyses")),
                ("billing_customer_reference", models.CharField(blank=True, max_length=128)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name="MonthlyUsage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("period_start", models.DateField()),
                ("analyses_count", models.PositiveIntegerField(default=0)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="monthly_usage", to="monitor.organization")),
            ],
            options={"ordering": ["-period_start"]},
        ),
        migrations.AddConstraint(
            model_name="monthlyusage",
            constraint=models.UniqueConstraint(fields=("organization", "period_start"), name="unique_monthly_usage_period"),
        ),
        migrations.CreateModel(
            name="CustomUser",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("password", models.CharField(max_length=128, verbose_name="password")),
                ("last_login", models.DateTimeField(blank=True, null=True, verbose_name="last login")),
                ("is_superuser", models.BooleanField(default=False, help_text="Designates that this user has all permissions without explicitly assigning them.", verbose_name="superuser status")),
                ("username", models.CharField(error_messages={"unique": "A user with that username already exists."}, help_text="Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.", max_length=150, unique=True, validators=[django.contrib.auth.validators.UnicodeUsernameValidator()], verbose_name="username")),
                ("first_name", models.CharField(blank=True, max_length=150, verbose_name="first name")),
                ("last_name", models.CharField(blank=True, max_length=150, verbose_name="last name")),
                ("email", models.EmailField(blank=True, max_length=254, verbose_name="email address")),
                ("is_staff", models.BooleanField(default=False, help_text="Designates whether the user can log into this admin site.", verbose_name="staff status")),
                ("is_active", models.BooleanField(default=True, help_text="Designates whether this user should be treated as active. Unselect this instead of deleting accounts.", verbose_name="active")),
                ("date_joined", models.DateTimeField(default=django.utils.timezone.now, verbose_name="date joined")),
                ("organization", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="users", to="monitor.organization")),
                ("groups", models.ManyToManyField(blank=True, help_text="The groups this user belongs to. A user will get all permissions granted to each of their groups.", related_name="user_set", related_query_name="user", to="auth.group", verbose_name="groups")),
                ("user_permissions", models.ManyToManyField(blank=True, help_text="Specific permissions for this user.", related_name="user_set", related_query_name="user", to="auth.permission", verbose_name="user permissions")),
            ],
            options={"verbose_name": "user", "verbose_name_plural": "users", "abstract": False},
            managers=[("objects", django.contrib.auth.models.UserManager())],
        ),
        migrations.CreateModel(
            name="Branch",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100)),
                ("pc_prefix", models.CharField(help_text="Globally unique PC name prefix for this branch", max_length=50, unique=True)),
                ("location", models.CharField(blank=True, max_length=200)),
                ("is_active", models.BooleanField(default=True)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="branches", to="monitor.organization")),
            ],
            options={"ordering": ["organization__name", "name"]},
        ),
        migrations.AddField(
            model_name="customuser",
            name="branch",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="users", to="monitor.branch", verbose_name="Assigned Branch"),
        ),
        migrations.CreateModel(
            name="Device",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100)),
                ("pc_name", models.CharField(max_length=128)),
                ("api_key_prefix", models.CharField(max_length=24, unique=True)),
                ("api_key_hash", models.CharField(max_length=64)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("last_seen_at", models.DateTimeField(blank=True, null=True)),
                ("branch", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="devices", to="monitor.branch")),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="devices", to="monitor.organization")),
            ],
        ),
        migrations.AddConstraint(
            model_name="device",
            constraint=models.UniqueConstraint(fields=("organization", "pc_name"), name="unique_device_pc_per_org"),
        ),
        migrations.CreateModel(
            name="UserProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("branch", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="monitor.branch")),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="profile", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="Visitor",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("face_id", models.CharField(max_length=128)),
                ("first_seen", models.DateTimeField()),
                ("last_seen", models.DateTimeField()),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="visitors", to="monitor.organization")),
            ],
        ),
        migrations.AddConstraint(
            model_name="visitor",
            constraint=models.UniqueConstraint(fields=("organization", "face_id"), name="unique_face_per_org"),
        ),
        migrations.AddIndex(
            model_name="visitor",
            index=models.Index(fields=["organization", "face_id"], name="monitor_vis_organiz_979213_idx"),
        ),
        migrations.CreateModel(
            name="CapturedSnapshot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("job_id", models.CharField(max_length=26, unique=True)),
                ("pc_name", models.CharField(max_length=128)),
                ("session_id", models.CharField(blank=True, db_index=True, max_length=64)),
                ("image_path", models.TextField(blank=True, null=True)),
                ("upload_content_type", models.CharField(blank=True, max_length=64)),
                ("upload_size_bytes", models.PositiveIntegerField(default=0)),
                ("timestamp", models.DateTimeField()),
                ("status", models.CharField(choices=[("queued", "Queued"), ("processing", "Processing"), ("processed", "Processed"), ("failed", "Failed")], default="queued", max_length=16)),
                ("emotion", models.CharField(blank=True, max_length=32, null=True)),
                ("confidence", models.FloatField(blank=True, null=True)),
                ("emotion_vector", models.JSONField(blank=True, null=True)),
                ("processed", models.BooleanField(default=False)),
                ("embedding", models.JSONField(blank=True, null=True)),
                ("error_message", models.CharField(blank=True, max_length=500)),
                ("processed_at", models.DateTimeField(blank=True, null=True)),
                ("branch", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="snapshots", to="monitor.branch")),
                ("device", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="snapshots", to="monitor.device")),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="snapshots", to="monitor.organization")),
                ("visitor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="snapshots", to="monitor.visitor")),
            ],
            options={"db_table": "captured_snapshots", "ordering": ["-timestamp"]},
        ),
        migrations.AddIndex(
            model_name="capturedsnapshot",
            index=models.Index(fields=["organization", "branch", "timestamp"], name="captured_sn_organiz_ab1771_idx"),
        ),
        migrations.AddIndex(
            model_name="capturedsnapshot",
            index=models.Index(fields=["status", "timestamp"], name="captured_sn_status_7519fa_idx"),
        ),
        migrations.AddIndex(
            model_name="capturedsnapshot",
            index=models.Index(fields=["visitor", "timestamp"], name="captured_sn_visitor_388bf2_idx"),
        ),
    ]

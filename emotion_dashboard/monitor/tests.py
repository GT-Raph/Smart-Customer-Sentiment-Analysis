import hashlib
import io

from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from emotion_dashboard.settings import database_from_url
from .models import Branch, CapturedSnapshot, CustomUser, Device, Organization, Visitor
from .views import get_user_pc_prefix


class TenantAccessTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Example", slug="example")
        self.branch = Branch.objects.create(
            organization=self.org, name="Accra", pc_prefix="ACC001"
        )

    def test_unassigned_user_is_denied(self):
        user = CustomUser(username="unassigned")
        with self.assertRaises(PermissionDenied):
            get_user_pc_prefix(user)

    def test_assigned_user_gets_only_branch_prefix(self):
        user = CustomUser(
            username="analyst", organization=self.org, branch=self.branch
        )
        self.assertEqual(get_user_pc_prefix(user), "ACC001")

    def test_cross_organization_branch_is_invalid(self):
        other = Organization.objects.create(name="Other", slug="other")
        user = CustomUser(username="bad", organization=other, branch=self.branch)
        with self.assertRaises(ValidationError):
            user.full_clean()

    def test_branch_assignment_requires_an_organization(self):
        user = CustomUser(username="bad", branch=self.branch)
        with self.assertRaises(ValidationError):
            user.full_clean()

    def test_unassigned_logged_in_user_cannot_open_dashboard(self):
        user = CustomUser.objects.create_user(username="unassigned", password="safe-pass-123")
        self.client.force_login(user)
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 403)

    def test_assigned_user_can_open_dashboard(self):
        user = CustomUser.objects.create_user(
            username="analyst",
            password="safe-pass-123",
            organization=self.org,
            branch=self.branch,
        )
        self.client.force_login(user)
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("branch_detail", args=[self.branch.id]))

    def test_assigned_user_can_only_open_their_branch(self):
        other = Branch.objects.create(
            organization=self.org, name="Kumasi", pc_prefix="KSI001"
        )
        user = CustomUser.objects.create_user(
            username="analyst",
            password="safe-pass-123",
            organization=self.org,
            branch=self.branch,
        )
        self.client.force_login(user)
        self.assertEqual(self.client.get(f"/branch/{self.branch.id}/").status_code, 200)
        self.assertEqual(self.client.get(f"/branch/{other.id}/").status_code, 403)

    def test_overlapping_pc_prefix_cannot_leak_another_branch_totals(self):
        overlapping_branch = Branch.objects.create(
            organization=self.org, name="Remote", pc_prefix="ACC0012"
        )
        device = Device.objects.create(
            organization=self.org,
            branch=overlapping_branch,
            name="Remote camera",
            pc_name="ACC0012-CAM",
            api_key_prefix="remote-prefix",
            api_key_hash="0" * 64,
        )
        visitor = Visitor.objects.create(
            organization=self.org,
            face_id="remote-visitor",
            first_seen=timezone.now(),
            last_seen=timezone.now(),
        )
        CapturedSnapshot.objects.create(
            job_id="01REMOTEVISITOR00000000000",
            organization=self.org,
            branch=overlapping_branch,
            device=device,
            visitor=visitor,
            pc_name=device.pc_name,
            timestamp=timezone.now(),
            status=CapturedSnapshot.Status.PROCESSED,
            processed=True,
            emotion="happy",
        )
        user = CustomUser.objects.create_user(
            username="analyst",
            password="safe-pass-123",
            organization=self.org,
            branch=self.branch,
        )
        self.client.force_login(user)

        response = self.client.get("/dashboard/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_visitors"], 0)

    def test_superuser_invalid_branch_filter_returns_404(self):
        admin = CustomUser.objects.create_superuser(
            username="admin", email="admin@example.com", password="safe-pass-123"
        )
        self.client.force_login(admin)
        response = self.client.get("/dashboard/?branch=DOES-NOT-EXIST")
        self.assertEqual(response.status_code, 404)

    def test_superuser_saas_navigation_pages_render(self):
        admin = CustomUser.objects.create_superuser(
            username="admin", email="admin@example.com", password="safe-pass-123"
        )
        self.client.force_login(admin)
        for url in (
            "/dashboard/",
            "/branches/",
            f"/branch/{self.branch.id}/",
            "/emotion-analytics/",
            "/reports/",
            "/settings/",
        ):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)


class DatabaseUrlTests(TestCase):
    def test_supabase_url_enables_ssl_and_health_checks(self):
        config = database_from_url(
            "postgresql://postgres.project:secret@aws-0-region.pooler.supabase.com:5432/postgres"
        )
        self.assertEqual(config["ENGINE"], "django.db.backends.postgresql")
        self.assertEqual(config["OPTIONS"]["sslmode"], "require")
        self.assertTrue(config["CONN_HEALTH_CHECKS"])

    def test_invalid_port_has_an_actionable_error(self):
        with self.assertRaisesRegex(RuntimeError, "invalid port"):
            database_from_url(
                "postgresql://postgres.project:secret@pooler.supabase.com:Z9/postgres"
            )


class DeviceKeyCommandTests(TestCase):
    def test_command_prints_key_once_and_stores_only_hash(self):
        org = Organization.objects.create(name="Example", slug="example")
        branch = Branch.objects.create(
            organization=org, name="Accra", pc_prefix="ACC001"
        )
        output = io.StringIO()
        call_command(
            "create_device_key",
            organization="example",
            branch=branch.id,
            name="Front Desk",
            pc_name="ACC001-CAM",
            stdout=output,
        )
        token = output.getvalue().strip().splitlines()[-1]
        device = Device.objects.get(pc_name="ACC001-CAM")
        self.assertTrue(token.startswith(f"scs_{device.api_key_prefix}_"))
        self.assertEqual(
            device.api_key_hash,
            hashlib.sha256(token.encode("utf-8")).hexdigest(),
        )
        self.assertNotEqual(device.api_key_hash, token)

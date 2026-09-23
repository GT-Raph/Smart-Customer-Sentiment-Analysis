import hashlib
import io
import json
from types import SimpleNamespace

from django.core.exceptions import PermissionDenied
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from emotion_dashboard.xampp_mysql.features import DatabaseFeatures

from .models import Branch, CapturedSnapshot, CustomUser, Device, Visitor
from .views import get_user_pc_prefix


class XamppCompatibilityBackendTests(SimpleTestCase):
    def test_mariadb_10_4_uses_lastrowid_instead_of_returning(self):
        features = DatabaseFeatures(
            SimpleNamespace(mysql_is_mariadb=True, mysql_version=(10, 4, 32))
        )

        self.assertEqual(features.minimum_database_version, (10, 4))
        self.assertFalse(features.can_return_columns_from_insert)


class LocalAccessTests(TestCase):
    def setUp(self):
        self.branch = Branch.objects.create(name="Accra", pc_prefix="ACC001")

    def test_unassigned_user_is_denied(self):
        user = CustomUser(username="unassigned")
        with self.assertRaises(PermissionDenied):
            get_user_pc_prefix(user)

    def test_assigned_user_gets_only_branch_prefix(self):
        user = CustomUser(username="analyst", branch=self.branch)
        self.assertEqual(get_user_pc_prefix(user), "ACC001")

    def test_inactive_branch_user_is_denied(self):
        self.branch.is_active = False
        user = CustomUser(username="analyst", branch=self.branch)
        with self.assertRaises(PermissionDenied):
            get_user_pc_prefix(user)

    def test_unassigned_logged_in_user_cannot_open_dashboard(self):
        user = CustomUser.objects.create_user(username="unassigned", password="safe-pass-123")
        self.client.force_login(user)
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 403)

    def test_assigned_user_can_open_dashboard(self):
        user = CustomUser.objects.create_user(
            username="analyst",
            password="safe-pass-123",
            branch=self.branch,
        )
        self.client.force_login(user)
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 200)

    def test_superuser_invalid_branch_filter_returns_404(self):
        admin = CustomUser.objects.create_superuser(
            username="admin", email="admin@example.com", password="safe-pass-123"
        )
        self.client.force_login(admin)
        response = self.client.get("/dashboard/?branch=DOES-NOT-EXIST")
        self.assertEqual(response.status_code, 404)


class DeviceKeyCommandTests(TestCase):
    def test_command_prints_key_once_and_stores_only_hash(self):
        branch = Branch.objects.create(name="Accra", pc_prefix="ACC001")
        output = io.StringIO()
        call_command(
            "create_device_key",
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


class DashboardUiSmokeTests(TestCase):
    def setUp(self):
        self.branch = Branch.objects.create(name="Accra", pc_prefix="ACC001")
        self.admin = CustomUser.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="safe-pass-123",
        )
        self.device = Device.objects.create(
            branch=self.branch,
            name="Front desk",
            pc_name="ACC001-CAM",
            api_key_prefix="ui-test",
            api_key_hash="a" * 64,
            last_seen_at=timezone.now(),
        )
        self.visitor = Visitor.objects.create(
            face_id="ui-visitor",
            first_seen=timezone.now(),
            last_seen=timezone.now(),
        )
        self.snapshot = CapturedSnapshot.objects.create(
            job_id="01UITEST000000000000000000",
            branch=self.branch,
            device=self.device,
            visitor=self.visitor,
            pc_name=self.device.pc_name,
            timestamp=timezone.now(),
            status=CapturedSnapshot.Status.PROCESSED,
            processed=True,
            emotion="happy",
            confidence=0.95,
        )

    def test_public_login_page_uses_existing_saas_style_template(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "registration/login.html")

    def test_authenticated_dashboard_pages_keep_rendering(self):
        self.client.force_login(self.admin)
        routes_and_templates = {
            "/dashboard/": "monitor/dashboard.html",
            "/branches/": "monitor/branch_overview.html",
            "/reports/": "monitor/reports.html",
            "/settings/": "monitor/settings.html",
            f"/branch/{self.branch.pk}/": "monitor/branch_detail.html",
            "/emotion-analytics/": "monitor/emotion_analytics.html",
        }

        for route, template in routes_and_templates.items():
            with self.subTest(route=route):
                response = self.client.get(route)
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, template)

    def test_dashboard_contains_full_sidebar_navigation(self):
        self.client.force_login(self.admin)
        response = self.client.get("/dashboard/")

        self.assertContains(response, 'id="sidebar"')
        self.assertContains(response, 'id="sidebarToggle"')
        self.assertContains(response, 'href="/dashboard/"')
        self.assertContains(response, 'href="/branches/"')
        self.assertContains(response, 'href="/emotion-analytics/"')
        self.assertContains(response, 'href="/reports/"')
        self.assertContains(response, 'href="/settings/"')
        self.assertContains(response, "Self-hosted intelligence")

    def test_branch_detail_displays_normalised_confidence_as_a_percentage(self):
        self.client.force_login(self.admin)

        response = self.client.get(f"/branch/{self.branch.pk}/")

        self.assertContains(response, "95.0%")

    def test_dashboard_includes_all_deepface_expression_categories(self):
        for index, emotion in enumerate(("fear", "disgust"), start=1):
            CapturedSnapshot.objects.create(
                job_id=f"01UICATEGORY{index:014d}",
                branch=self.branch,
                device=self.device,
                visitor=self.visitor,
                pc_name=self.device.pc_name,
                timestamp=timezone.now(),
                status=CapturedSnapshot.Status.PROCESSED,
                processed=True,
                emotion=emotion,
                confidence=0.80,
            )

        self.client.force_login(self.admin)
        response = self.client.get("/dashboard/")

        self.assertEqual(response.context["negative_percentage"], 66.7)
        labels = json.loads(response.context["emotion_labels"])
        self.assertIn("fear", labels)
        self.assertIn("disgust", labels)

    def test_logout_is_post_only(self):
        self.client.force_login(self.admin)

        self.assertEqual(self.client.get("/logout/").status_code, 405)
        response = self.client.post("/logout/")

        self.assertRedirects(response, "/")

    def test_csv_report_uses_non_saas_columns(self):
        self.client.force_login(self.admin)
        today = timezone.localdate().isoformat()
        response = self.client.post(
            "/reports/",
            {
                "date_from": today,
                "date_to": today,
                "branch": str(self.branch.pk),
            },
        )

        self.assertEqual(response.status_code, 200)
        content = b"".join(response.streaming_content).decode("utf-8")
        self.assertIn("Branch,Visitor ID,PC,Emotion,Confidence,Timestamp", content)
        self.assertIn("Accra,ui-visitor,ACC001-CAM,happy,0.95", content)
        self.assertNotIn("Bank", content)

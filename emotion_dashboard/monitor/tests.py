import hashlib
import io

from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.test import TestCase

from .models import Branch, CustomUser, Device, Organization
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

    def test_superuser_invalid_branch_filter_returns_404(self):
        admin = CustomUser.objects.create_superuser(
            username="admin", email="admin@example.com", password="safe-pass-123"
        )
        self.client.force_login(admin)
        response = self.client.get("/dashboard/?branch=DOES-NOT-EXIST")
        self.assertEqual(response.status_code, 404)


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

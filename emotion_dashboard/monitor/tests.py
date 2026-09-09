import tempfile
from pathlib import Path

from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import (
    Bank,
    Branch,
    CapturedSnapshot,
    CustomUser,
    Visitor,
)


class TenantIsolationTests(TestCase):
    def setUp(self):
        self.image_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.image_directory.cleanup)
        self.settings_override = override_settings(
            CAPTURED_FACES_ROOT=Path(self.image_directory.name)
        )
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)

        self.bank_a = Bank.objects.create(
            name="Bank A",
            code="BANK_A",
        )

        self.bank_b = Bank.objects.create(
            name="Bank B",
            code="BANK_B",
        )

        self.branch_a = Branch.objects.create(
            bank=self.bank_a,
            name="Bank A Main Branch",
            code="MAIN",
            pc_prefix="BANK-A-PC",
            location="Accra",
        )

        self.branch_b = Branch.objects.create(
            bank=self.bank_b,
            name="Bank B Main Branch",
            code="MAIN",
            pc_prefix="BANK-B-PC",
            location="Kumasi",
        )

        self.bank_a_admin = (
            CustomUser.objects.create_user(
                username="bank-a-admin",
                password="SafePass12345",
                bank=self.bank_a,
            )
        )

        self.bank_b_admin = (
            CustomUser.objects.create_user(
                username="bank-b-admin",
                password="SafePass12345",
                bank=self.bank_b,
            )
        )

        self.bank_a_branch_user = (
            CustomUser.objects.create_user(
                username="bank-a-branch-user",
                password="SafePass12345",
                bank=self.bank_a,
                branch=self.branch_a,
            )
        )

        # The same face ID may exist in different banks.
        # The bank relationship keeps them separate.
        self.visitor_a = Visitor.objects.create(
            bank=self.bank_a,
            face_id="same-face-id",
        )

        self.visitor_b = Visitor.objects.create(
            bank=self.bank_b,
            face_id="same-face-id",
        )

        self.snapshot_a = (
            CapturedSnapshot.objects.create(
                job_id="job-bank-a",
                bank=self.bank_a,
                branch=self.branch_a,
                visitor=self.visitor_a,
                pc_name="BANK-A-PC-01",
                image_path=(
                    "BANK_A/MAIN/bank-a.jpg"
                ),
                timestamp=timezone.now(),
                emotion="happy",
                confidence=94.5,
                status="done",
                processed=True,
            )
        )

        self.snapshot_b = (
            CapturedSnapshot.objects.create(
                job_id="job-bank-b",
                bank=self.bank_b,
                branch=self.branch_b,
                visitor=self.visitor_b,
                pc_name="BANK-B-PC-01",
                image_path=(
                    "BANK_B/MAIN/bank-b.jpg"
                ),
                timestamp=timezone.now(),
                emotion="angry",
                confidence=91.0,
                status="done",
                processed=True,
            )
        )

    def test_bank_a_dashboard_does_not_count_bank_b_data(self):
        login_successful = self.client.login(
            username="bank-a-admin",
            password="SafePass12345",
        )

        self.assertTrue(
            login_successful
        )

        response = self.client.get(
            reverse("dashboard")
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.context[
                "total_detections"
            ],
            1,
        )

        self.assertEqual(
            response.context[
                "top_emotion"
            ]["emotion"],
            "happy",
        )

    def test_bank_b_dashboard_does_not_count_bank_a_data(self):
        self.client.login(
            username="bank-b-admin",
            password="SafePass12345",
        )

        response = self.client.get(
            reverse("dashboard")
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.context[
                "total_detections"
            ],
            1,
        )

        self.assertEqual(
            response.context[
                "top_emotion"
            ]["emotion"],
            "angry",
        )

    def test_bank_a_cannot_open_bank_b_branch(self):
        self.client.login(
            username="bank-a-admin",
            password="SafePass12345",
        )

        response = self.client.get(
            reverse(
                "branch_detail",
                args=[self.branch_b.id],
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_bank_a_cannot_open_bank_b_image(self):
        self.client.login(
            username="bank-a-admin",
            password="SafePass12345",
        )

        response = self.client.get(
            reverse(
                "snapshot_image",
                args=[self.snapshot_b.id],
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_bank_a_can_open_bank_a_image(self):
        image_path = (
            Path(self.image_directory.name)
            / self.snapshot_a.image_path
        )
        image_path.parent.mkdir(parents=True, exist_ok=True)
        image_path.write_bytes(b"snapshot-a")

        self.client.login(
            username="bank-a-admin",
            password="SafePass12345",
        )

        response = self.client.get(
            reverse(
                "snapshot_image",
                args=[self.snapshot_a.id],
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )
        self.assertEqual(
            b"".join(response.streaming_content),
            b"snapshot-a",
        )
        response.close()

    def test_branch_user_cannot_open_another_bank_branch(self):
        self.client.login(
            username="bank-a-branch-user",
            password="SafePass12345",
        )

        response = self.client.get(
            reverse(
                "branch_detail",
                args=[self.branch_b.id],
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_same_face_id_can_exist_in_two_banks(self):
        self.assertEqual(
            self.visitor_a.face_id,
            self.visitor_b.face_id,
        )

        self.assertNotEqual(
            self.visitor_a.bank_id,
            self.visitor_b.bank_id,
        )

        self.assertNotEqual(
            self.visitor_a.id,
            self.visitor_b.id,
        )

    def test_bank_admin_cannot_filter_dashboard_using_other_bank_branch(self):
        self.client.login(
            username="bank-a-admin",
            password="SafePass12345",
        )

        response = self.client.get(
            reverse("dashboard"),
            {
                "branch": self.branch_b.id,
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        # The unauthorised branch filter must not reveal
        # Bank B's angry snapshot.
        self.assertEqual(
            response.context[
                "top_emotion"
            ]["emotion"],
            "happy",
        )

    def test_visitor_pages_are_tenant_scoped(self):
        self.client.login(
            username="bank-a-admin",
            password="SafePass12345",
        )

        visitors_response = self.client.get(
            reverse("visitors")
        )
        history_response = self.client.get(
            reverse("visit_history")
        )
        hidden_detail_response = self.client.get(
            reverse(
                "visitor_detail",
                args=[self.visitor_b.id],
            )
        )

        self.assertEqual(visitors_response.status_code, 200)
        self.assertEqual(len(visitors_response.context["visitors"]), 1)
        self.assertEqual(history_response.status_code, 200)
        self.assertEqual(len(history_response.context["visits"]), 1)
        self.assertEqual(hidden_detail_response.status_code, 404)

    def test_normalization_happens_before_uniqueness_validation(self):
        duplicate_bank = Bank(
            name="Duplicate",
            code="bank_a",
        )

        with self.assertRaises(ValidationError):
            duplicate_bank.full_clean()

        self.assertEqual(duplicate_bank.code, "BANK_A")

        duplicate_branch = Branch(
            bank=self.bank_a,
            name="Duplicate Main",
            code="main",
            pc_prefix="bank-a-pc",
        )

        with self.assertRaises(ValidationError):
            duplicate_branch.full_clean()

        self.assertEqual(duplicate_branch.code, "MAIN")
        self.assertEqual(duplicate_branch.pc_prefix, "BANK-A-PC")

    def test_visitor_detail_counts_scoped_visits(self):
        CapturedSnapshot.objects.create(
            job_id="job-bank-a-second",
            bank=self.bank_a,
            branch=self.branch_a,
            visitor=self.visitor_a,
            pc_name="BANK-A-PC-01",
            image_path="BANK_A/MAIN/bank-a-second.jpg",
            timestamp=timezone.now(),
            emotion="happy",
            confidence=93.0,
            status="done",
            processed=True,
        )
        self.assertEqual(
            CapturedSnapshot.objects.filter(
                visitor=self.visitor_a,
                status="done",
                emotion="happy",
            ).count(),
            2,
        )

        self.client.login(
            username="bank-a-admin",
            password="SafePass12345",
        )
        response = self.client.get(
            reverse("visitor_detail", args=[self.visitor_a.id])
        )

        self.assertEqual(response.status_code, 200)
        rendered_context = response.context[-1]
        self.assertEqual(rendered_context["emotion_counts"]["happy"], 2)
        self.assertEqual(rendered_context["total_visits"], 2)

    def test_password_reset_page_is_available(self):
        response = self.client.get(
            reverse("password_reset")
        )

        self.assertEqual(response.status_code, 200)

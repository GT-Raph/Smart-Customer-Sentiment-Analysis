import tempfile
from pathlib import Path

from django.test import (
    TestCase,
    override_settings,
)
from django.urls import reverse
from django.utils import timezone

from .models import (
    Bank,
    Branch,
    CapturedSnapshot,
    CustomUser,
    Visitor,
)


TEST_IMAGE_DIRECTORY = (
    Path(tempfile.gettempdir())
    / "sentiment-test-faces"
)


@override_settings(
    CAPTURED_FACES_ROOT=TEST_IMAGE_DIRECTORY
)
class TenantIsolationTests(TestCase):
    def setUp(self):
        TEST_IMAGE_DIRECTORY.mkdir(
            parents=True,
            exist_ok=True,
        )

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
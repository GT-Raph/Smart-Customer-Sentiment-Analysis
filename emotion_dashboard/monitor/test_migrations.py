from datetime import timedelta

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone


class NonSaaSMigrationTests(TransactionTestCase):
    migrate_from = ("monitor", "0001_initial")
    migrate_to = ("monitor", "0002_remove_saas_tenancy")

    def setUp(self):
        super().setUp()
        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_from])
        old_apps = executor.loader.project_state([self.migrate_from]).apps

        Organization = old_apps.get_model("monitor", "Organization")
        Branch = old_apps.get_model("monitor", "Branch")
        Device = old_apps.get_model("monitor", "Device")
        Visitor = old_apps.get_model("monitor", "Visitor")
        CapturedSnapshot = old_apps.get_model("monitor", "CapturedSnapshot")

        first_org = Organization.objects.create(name="First", slug="first")
        second_org = Organization.objects.create(name="Second", slug="second")
        first_branch = Branch.objects.create(
            organization=first_org, name="First branch", pc_prefix="FIRST"
        )
        second_branch = Branch.objects.create(
            organization=second_org, name="Second branch", pc_prefix="SECOND"
        )
        first_device = Device.objects.create(
            organization=first_org,
            branch=first_branch,
            name="Camera one",
            pc_name="SHARED-CAMERA",
            api_key_prefix="first-key",
            api_key_hash="a" * 64,
        )
        second_device = Device.objects.create(
            organization=second_org,
            branch=second_branch,
            name="Camera two",
            pc_name="SHARED-CAMERA",
            api_key_prefix="second-key",
            api_key_hash="b" * 64,
        )

        now = timezone.now()
        first_visitor = Visitor.objects.create(
            organization=first_org,
            face_id="shared-face",
            first_seen=now - timedelta(days=2),
            last_seen=now - timedelta(days=1),
        )
        second_visitor = Visitor.objects.create(
            organization=second_org,
            face_id="shared-face",
            first_seen=now,
            last_seen=now,
        )
        CapturedSnapshot.objects.create(
            job_id="01MIGRATEFIRST000000000000",
            organization=first_org,
            branch=first_branch,
            device=first_device,
            visitor=first_visitor,
            pc_name=first_device.pc_name,
            timestamp=now,
        )
        CapturedSnapshot.objects.create(
            job_id="01MIGRATESECOND00000000000",
            organization=second_org,
            branch=second_branch,
            device=second_device,
            visitor=second_visitor,
            pc_name=second_device.pc_name,
            timestamp=now,
        )

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_to])
        self.apps = executor.loader.project_state([self.migrate_to]).apps

    def test_existing_records_are_preserved_and_normalized(self):
        Device = self.apps.get_model("monitor", "Device")
        Visitor = self.apps.get_model("monitor", "Visitor")
        CapturedSnapshot = self.apps.get_model("monitor", "CapturedSnapshot")

        self.assertEqual(Device.objects.count(), 2)
        self.assertEqual(Device.objects.values("pc_name").distinct().count(), 2)
        self.assertEqual(Visitor.objects.count(), 1)
        self.assertEqual(CapturedSnapshot.objects.count(), 2)
        self.assertEqual(
            CapturedSnapshot.objects.values("visitor_id").distinct().count(), 1
        )

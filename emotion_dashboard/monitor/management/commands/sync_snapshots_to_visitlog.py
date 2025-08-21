from django.core.management.base import BaseCommand
from monitor.models import CapturedSnapshot, VisitLog, Visitor, Branch

class Command(BaseCommand):
    help = "Sync processed CapturedSnapshot rows into VisitLog for dashboard analytics"

    def handle(self, *args, **kwargs):
        count = 0
        # Only process snapshots that are processed and have emotion
        for snap in CapturedSnapshot.objects.filter(processed=True).exclude(emotion__isnull=True):
            # Find branch by pc_name prefix
            branch = None
            for b in Branch.objects.all():
                if snap.pc_name.startswith(b.code_prefix):
                    branch = b
                    break
            if not branch:
                continue

            # Find or create Visitor
            visitor, _ = Visitor.objects.get_or_create(face_id=snap.face_id, defaults={"name": snap.face_id})

            # Check if already exists
            if VisitLog.objects.filter(visitor=visitor, emotion=snap.emotion, timestamp=snap.timestamp, branch=branch).exists():
                continue

            # Insert VisitLog
            VisitLog.objects.create(
                visitor=visitor,
                emotion=snap.emotion,
                timestamp=snap.timestamp,
                branch=branch
            )
            count += 1
        self.stdout.write(self.style.SUCCESS(f"Synced {count} snapshots to VisitLog"))
        self.stdout.write(self.style.SUCCESS(f"Synced {count} snapshots to VisitLog"))

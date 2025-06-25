from django.core.management.base import BaseCommand
from django.db import connection
from monitor.models import Visitor

class Command(BaseCommand):
    help = "Sync face_id values from unique_face_id table to Visitor model"

    def handle(self, *args, **kwargs):
        with connection.cursor() as cursor:
            cursor.execute("SELECT face_id FROM unique_face_id")
            face_ids = [row[0] for row in cursor.fetchall()]

        created = 0
        for face_id in face_ids:
            if face_id and not Visitor.objects.filter(face_id=face_id).exists():
                Visitor.objects.create(face_id=face_id)
                created += 1

        self.stdout.write(self.style.SUCCESS(f"Sync complete. {created} new Visitor(s) created."))
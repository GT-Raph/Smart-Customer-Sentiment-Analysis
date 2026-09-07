from django.db import migrations, models


def normalize_single_installation_data(apps, schema_editor):
    """Resolve cross-organization duplicates before global uniqueness is applied."""

    database_alias = schema_editor.connection.alias
    Device = apps.get_model("monitor", "Device")
    Visitor = apps.get_model("monitor", "Visitor")
    CapturedSnapshot = apps.get_model("monitor", "CapturedSnapshot")

    used_pc_names: set[str] = set()
    for device in Device.objects.using(database_alias).order_by("id").iterator():
        candidate = device.pc_name
        if candidate in used_pc_names:
            suffix = f"-{device.pk}"
            candidate = f"{candidate[: 128 - len(suffix)]}{suffix}"
            counter = 2
            while candidate in used_pc_names:
                suffix = f"-{device.pk}-{counter}"
                candidate = f"{device.pc_name[: 128 - len(suffix)]}{suffix}"
                counter += 1
            Device.objects.using(database_alias).filter(pk=device.pk).update(
                pc_name=candidate
            )
        used_pc_names.add(candidate)

    visitor_by_face_id: dict[str, object] = {}
    for visitor in Visitor.objects.using(database_alias).order_by("id").iterator():
        keeper = visitor_by_face_id.get(visitor.face_id)
        if keeper is None:
            visitor_by_face_id[visitor.face_id] = visitor
            continue

        CapturedSnapshot.objects.using(database_alias).filter(
            visitor_id=visitor.pk
        ).update(visitor_id=keeper.pk)
        keeper.first_seen = min(keeper.first_seen, visitor.first_seen)
        keeper.last_seen = max(keeper.last_seen, visitor.last_seen)
        keeper.save(using=database_alias, update_fields=["first_seen", "last_seen"])
        visitor.delete(using=database_alias)


class Migration(migrations.Migration):
    dependencies = [("monitor", "0001_initial")]

    operations = [
        migrations.RunPython(normalize_single_installation_data, migrations.RunPython.noop),
        migrations.RemoveConstraint(
            model_name="device",
            name="unique_device_pc_per_org",
        ),
        migrations.RemoveConstraint(
            model_name="visitor",
            name="unique_face_per_org",
        ),
        migrations.RemoveIndex(
            model_name="visitor",
            name="monitor_vis_organiz_979213_idx",
        ),
        migrations.RemoveIndex(
            model_name="capturedsnapshot",
            name="captured_sn_organiz_ab1771_idx",
        ),
        migrations.AlterModelOptions(
            name="branch",
            options={"ordering": ["name"]},
        ),
        migrations.RemoveField(model_name="customuser", name="organization"),
        migrations.RemoveField(model_name="device", name="organization"),
        migrations.RemoveField(model_name="capturedsnapshot", name="organization"),
        migrations.RemoveField(model_name="visitor", name="organization"),
        migrations.RemoveField(model_name="branch", name="organization"),
        migrations.DeleteModel(name="MonthlyUsage"),
        migrations.DeleteModel(name="Organization"),
        migrations.AlterField(
            model_name="device",
            name="pc_name",
            field=models.CharField(max_length=128, unique=True),
        ),
        migrations.AlterField(
            model_name="visitor",
            name="face_id",
            field=models.CharField(max_length=128, unique=True),
        ),
        migrations.AddIndex(
            model_name="capturedsnapshot",
            index=models.Index(
                fields=["branch", "timestamp"],
                name="snapshot_branch_time_idx",
            ),
        ),
    ]

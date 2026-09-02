from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "core",
            "0003_ai_intelligence",
        ),
    ]

    operations = [
        migrations.AlterField(
            model_name="leave",
            name="status",
            field=models.CharField(
                choices=[
                    (
                        "PENDING",
                        "Pending",
                    ),
                    (
                        "APPROVED",
                        "Approved",
                    ),
                    (
                        "REJECTED",
                        "Rejected",
                    ),
                    (
                        "CANCELLED",
                        "Cancelled",
                    ),
                ],
                default="PENDING",
                max_length=20,
            ),
        ),
    ]
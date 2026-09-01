from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [("core", "0001_initial")]
    operations = [
        migrations.AlterField(
            model_name="user",
            name="employee_id",
            field=models.CharField(max_length=100, unique=True),
        ),
        migrations.AddField(
            model_name="user",
            name="must_change_password",
            field=models.BooleanField(default=True),
        ),
    ]

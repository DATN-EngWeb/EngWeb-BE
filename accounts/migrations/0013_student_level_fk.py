from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("user_progress", "0001_initial"),
        ("accounts", "0012_remove_student_last_attempt_at_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="student",
            name="title",
        ),
        migrations.AlterField(
            model_name="student",
            name="level",
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="students",
                to="user_progress.userlevel",
            ),
        ),
    ]

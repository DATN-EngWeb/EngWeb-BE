from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

	initial = True

	dependencies = []

	operations = [
		migrations.CreateModel(
			name="UserLevel",
			fields=[
				(
					"id",
					models.BigAutoField(
						auto_created=True,
						primary_key=True,
						serialize=False,
						verbose_name="ID",
					),
				),
				(
					"level_number",
					models.IntegerField(
						unique=True,
						validators=[django.core.validators.MinValueValidator(1)],
					),
				),
				("level_title", models.CharField(max_length=50)),
				(
					"level_icon",
					models.URLField(blank=True, max_length=200, null=True),
				),
				(
					"min_xp",
					models.IntegerField(
						validators=[django.core.validators.MinValueValidator(0)]
					),
				),
				(
					"max_xp",
					models.IntegerField(
						validators=[django.core.validators.MinValueValidator(0)]
					),
				),
			],
			options={
				"db_table": "user_level",
				"ordering": ["min_xp"],
			},
		),
	]

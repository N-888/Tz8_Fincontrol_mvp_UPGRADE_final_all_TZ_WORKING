# Generated manually for FinControl optional features.
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="category",
            name="parent",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="children",
                to="core.category",
            ),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="ai_advice_enabled",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="telegram_voice_enabled",
            field=models.BooleanField(default=False),
        ),
        migrations.AlterUniqueTogether(
            name="category",
            unique_together={("user", "parent", "name")},
        ),
    ]

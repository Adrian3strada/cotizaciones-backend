from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("quotes", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="quote",
            name="cableado",
            field=models.BooleanField(default=False, verbose_name="Cableado"),
        ),
        migrations.AddField(
            model_name="quote",
            name="cableado_monto",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                default=Decimal("0.00"),
                max_digits=14,
                verbose_name="Cableado (monto)",
            ),
        ),
        migrations.AddField(
            model_name="quote",
            name="instalacion",
            field=models.BooleanField(default=False, verbose_name="Instalación"),
        ),
        migrations.AddField(
            model_name="quote",
            name="instalacion_monto",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                default=Decimal("0.00"),
                max_digits=14,
                verbose_name="Instalación (monto)",
            ),
        ),
    ]

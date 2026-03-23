from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="cameramodel",
            name="base_price",
            field=models.DecimalField(
                decimal_places=2,
                max_digits=14,
                verbose_name="Precio base (USD)",
                help_text="Lista de precios siempre en dólares. En cotizaciones en MXN se convierte con el tipo de cambio de la cotización.",
            ),
        ),
        migrations.RemoveField(
            model_name="cameramodel",
            name="currency",
        ),
    ]

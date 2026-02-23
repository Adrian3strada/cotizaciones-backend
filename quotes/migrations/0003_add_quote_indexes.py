# Generated manually for performance indexes

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("quotes", "0002_add_quote_item_group"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="quote",
            index=models.Index(fields=["sales_user", "status"], name="quotes_sales_status_idx"),
        ),
        migrations.AddIndex(
            model_name="quote",
            index=models.Index(fields=["issue_date"], name="quotes_issue_date_idx"),
        ),
        migrations.AddIndex(
            model_name="quote",
            index=models.Index(fields=["customer", "status"], name="quotes_customer_status_idx"),
        ),
    ]

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def seed_categories(apps, schema_editor):
    Category = apps.get_model("notifications", "NotificationCategory")
    categories = [
        {
            "code": "general",
            "name": "Genel",
            "description": "Genel duyurular ve uygulama bilgilendirmeleri.",
            "sort_order": 10,
        },
        {
            "code": "orders",
            "name": "Siparişler",
            "description": "Sipariş ve işlem durumu bildirimleri.",
            "sort_order": 20,
        },
        {
            "code": "campaigns",
            "name": "Kampanyalar",
            "description": "Kampanya, fırsat ve tanıtım bildirimleri.",
            "sort_order": 30,
        },
        {
            "code": "system",
            "name": "Sistem",
            "description": "Sistem ve hesap ile ilgili bilgilendirmeler.",
            "sort_order": 40,
        },
    ]
    for item in categories:
        Category.objects.get_or_create(code=item["code"], defaults=item)


class Migration(migrations.Migration):
    dependencies = [
        ("notifications", "0002_notification"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="NotificationCategory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.SlugField(max_length=50, unique=True)),
                ("name", models.CharField(max_length=100)),
                ("description", models.CharField(blank=True, max_length=250)),
                ("is_active", models.BooleanField(default=True)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["sort_order", "name"],
                "verbose_name_plural": "Notification categories",
            },
        ),
        migrations.CreateModel(
            name="UserNotificationPreference",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("enabled", models.BooleanField(default=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "category",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="user_preferences",
                        to="notifications.notificationcategory",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="notification_preferences",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["category__sort_order", "category__name"]},
        ),
        migrations.AddConstraint(
            model_name="usernotificationpreference",
            constraint=models.UniqueConstraint(
                fields=("user", "category"),
                name="unique_user_notification_category_preference",
            ),
        ),
        migrations.AddField(
            model_name="notification",
            name="category",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="notifications",
                to="notifications.notificationcategory",
            ),
        ),
        migrations.RunPython(seed_categories, migrations.RunPython.noop),
    ]

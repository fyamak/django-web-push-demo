from django.conf import settings
from django.db import models


class PushSubscription(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="push_subscriptions",
    )
    endpoint = models.TextField(unique=True)
    p256dh = models.TextField()
    auth = models.TextField()
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.user} - {self.endpoint[:60]}"

    def as_webpush_dict(self):
        return {
            "endpoint": self.endpoint,
            "keys": {
                "p256dh": self.p256dh,
                "auth": self.auth,
            },
        }


class NotificationCategory(models.Model):
    """Admin-managed notification topic that users can opt in/out of."""

    code = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=250, blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name_plural = "Notification categories"

    def __str__(self):
        return self.name


class UserNotificationPreference(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_preferences",
    )
    category = models.ForeignKey(
        NotificationCategory,
        on_delete=models.CASCADE,
        related_name="user_preferences",
    )
    enabled = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "category"],
                name="unique_user_notification_category_preference",
            )
        ]
        ordering = ["category__sort_order", "category__name"]

    def __str__(self):
        return f"{self.user} - {self.category}: {'on' if self.enabled else 'off'}"


class Notification(models.Model):
    """Persistent in-app history for every notification accepted for a user."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    category = models.ForeignKey(
        NotificationCategory,
        on_delete=models.PROTECT,
        related_name="notifications",
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=120)
    body = models.TextField(max_length=500)
    url = models.CharField(max_length=500, default="/")
    sent_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} - {self.title} ({self.created_at:%Y-%m-%d %H:%M})"

    @property
    def is_read(self):
        return self.read_at is not None

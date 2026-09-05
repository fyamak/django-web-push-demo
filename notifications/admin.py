from django.contrib import admin

from .models import Notification, PushSubscription


@admin.register(PushSubscription)
class PushSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "short_endpoint", "updated_at")
    search_fields = ("user__username", "endpoint")
    readonly_fields = ("created_at", "updated_at")

    @admin.display(description="Endpoint")
    def short_endpoint(self, obj):
        return obj.endpoint[:80]


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "title", "sent_count", "failed_count", "read_at", "created_at")
    list_filter = ("created_at", "read_at")
    search_fields = ("user__username", "title", "body")
    readonly_fields = ("created_at",)

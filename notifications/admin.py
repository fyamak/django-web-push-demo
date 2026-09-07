from django.contrib import admin

from .models import (
    Notification,
    NotificationCategory,
    PushSubscription,
    UserNotificationPreference,
)


@admin.register(PushSubscription)
class PushSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "short_endpoint", "updated_at")
    search_fields = ("user__username", "endpoint")
    readonly_fields = ("created_at", "updated_at")

    @admin.display(description="Endpoint")
    def short_endpoint(self, obj):
        return obj.endpoint[:80]


@admin.register(NotificationCategory)
class NotificationCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active", "sort_order")
    list_editable = ("is_active", "sort_order")
    search_fields = ("name", "code", "description")
    ordering = ("sort_order", "name")


@admin.register(UserNotificationPreference)
class UserNotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ("user", "category", "enabled", "updated_at")
    list_filter = ("enabled", "category")
    search_fields = ("user__username", "user__email", "category__name")
    autocomplete_fields = ("user", "category")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "category", "title", "sent_count", "failed_count", "read_at", "created_at")
    list_filter = ("category", "created_at", "read_at")
    search_fields = ("user__username", "title", "body")
    readonly_fields = ("created_at",)

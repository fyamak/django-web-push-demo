from django.contrib import admin
from .models import PushSubscription


@admin.register(PushSubscription)
class PushSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "short_endpoint", "updated_at")
    search_fields = ("user__username", "endpoint")
    readonly_fields = ("created_at", "updated_at")

    @admin.display(description="Endpoint")
    def short_endpoint(self, obj):
        return obj.endpoint[:80]

from django.urls import path
from . import views

app_name = "notifications"

urlpatterns = [
    path("", views.home, name="home"),
    path("manifest.json", views.manifest, name="manifest"),
    path("service-worker.js", views.service_worker, name="service_worker"),
    path("notifications/<int:notification_id>/open/", views.open_notification, name="open_notification"),
    path("api/notifications/", views.notification_history, name="notification_history"),
    path("api/notifications/mark-all-read/", views.mark_all_notifications_read, name="mark_all_notifications_read"),
    path("api/push/subscribe/", views.subscribe, name="subscribe"),
    path("api/push/unsubscribe/", views.unsubscribe, name="unsubscribe"),
    path("api/push/send-test/", views.send_test, name="send_test"),
]

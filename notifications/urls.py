from django.urls import path
from . import views

app_name = "notifications"

urlpatterns = [
    path("", views.home, name="home"),
    path("admin-home/", views.admin_home, name="admin_home"),
    path("admin-send-notification/",views.admin_send_notification, name="admin_send_notification"),
    path("notification-settings/", views.notification_settings_page, name="notification_settings_page"),
    path("signup/", views.signup, name="signup"),
    path("manifest.json", views.manifest, name="manifest"),
    path("service-worker.js", views.service_worker, name="service_worker"),
    path("notifications/<int:notification_id>/open/", views.open_notification, name="open_notification"),
    path("api/notifications/", views.notification_history, name="notification_history"),
    path("api/notifications/mark-all-read/", views.mark_all_notifications_read, name="mark_all_notifications_read"),
    path("api/notification-preferences/", views.notification_preferences, name="notification_preferences"),
    path("api/notification-preferences/save/", views.save_notification_preferences, name="save_notification_preferences"),
    path("api/push/subscribe/", views.subscribe, name="subscribe"),
    path("api/push/unsubscribe/", views.unsubscribe, name="unsubscribe"),
    path("api/push/send-test/", views.send_test, name="send_test"),
    path("api/users/<int:user_id>/notification-state/", views.target_user_notification_state, name="target_user_notification_state"),
    path("api/push/send-to-user/", views.send_to_user, name="send_to_user"),
]

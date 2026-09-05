import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Notification, PushSubscription
from .services import send_push_to_user


class PushSubscriptionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="tester", password="StrongPass123!")
        self.client.force_login(self.user)

    def test_subscribe_creates_record(self):
        payload = {
            "endpoint": "https://push.example.test/abc",
            "keys": {"p256dh": "key1", "auth": "key2"},
        }
        response = self.client.post(
            reverse("notifications:subscribe"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(PushSubscription.objects.count(), 1)
        self.assertEqual(PushSubscription.objects.get().user, self.user)

    @patch("notifications.views.send_push_to_user")
    def test_send_test_calls_service(self, mock_send):
        mock_send.return_value = {"notification_id": 1, "sent": 1, "failed": 0, "errors": []}
        response = self.client.post(
            reverse("notifications:send_test"),
            data=json.dumps({"title": "x", "body": "y", "url": "/"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        mock_send.assert_called_once()


class NotificationTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="history-tester", password="secret123")
        self.client.force_login(self.user)

    @patch("notifications.services.send_push_to_subscription")
    def test_each_push_gets_unique_tag_and_history_record(self, mock_send):
        mock_send.return_value = (True, None)
        PushSubscription.objects.create(
            user=self.user,
            endpoint="https://push.example/subscription",
            p256dh="p256dh",
            auth="auth",
        )

        first = send_push_to_user(self.user, "Birinci", "İlk mesaj")
        first_payload = mock_send.call_args.args[1]
        second = send_push_to_user(self.user, "İkinci", "İkinci mesaj")
        second_payload = mock_send.call_args.args[1]

        self.assertEqual(Notification.objects.filter(user=self.user).count(), 2)
        self.assertNotEqual(first["notification_id"], second["notification_id"])
        self.assertNotEqual(first_payload["tag"], second_payload["tag"])
        self.assertEqual(first_payload["tag"], f"notification-{first['notification_id']}")
        self.assertEqual(second_payload["tag"], f"notification-{second['notification_id']}")

    def test_open_notification_marks_it_read_and_redirects(self):
        item = Notification.objects.create(
            user=self.user,
            title="Takip",
            body="Detay",
            url="/hedef/",
        )

        response = self.client.get(reverse("notifications:open_notification", args=[item.pk]))
        self.assertRedirects(response, "/hedef/", fetch_redirect_response=False)

        item.refresh_from_db()
        self.assertIsNotNone(item.read_at)

    def test_user_cannot_open_another_users_notification(self):
        User = get_user_model()
        other = User.objects.create_user(username="other", password="secret123")
        item = Notification.objects.create(user=other, title="Özel", body="Mesaj")

        response = self.client.get(reverse("notifications:open_notification", args=[item.pk]))
        self.assertEqual(response.status_code, 404)

    def test_history_api_only_returns_current_users_items(self):
        User = get_user_model()
        other = User.objects.create_user(username="other2", password="secret123")
        Notification.objects.create(user=self.user, title="Benim", body="Mesaj")
        Notification.objects.create(user=other, title="Başkasının", body="Mesaj")

        response = self.client.get(reverse("notifications:notification_history"))
        self.assertEqual(response.status_code, 200)
        items = response.json()["items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "Benim")

    def test_mark_all_read_only_updates_current_user(self):
        User = get_user_model()
        other = User.objects.create_user(username="other3", password="secret123")
        own = Notification.objects.create(user=self.user, title="Benim", body="Mesaj")
        foreign = Notification.objects.create(user=other, title="Başkasının", body="Mesaj")

        response = self.client.post(reverse("notifications:mark_all_notifications_read"), data="{}", content_type="application/json")
        self.assertEqual(response.status_code, 200)

        own.refresh_from_db()
        foreign.refresh_from_db()
        self.assertIsNotNone(own.read_at)
        self.assertIsNone(foreign.read_at)

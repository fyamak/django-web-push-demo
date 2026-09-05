import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import PushSubscription


class PushSubscriptionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="tester", password="StrongPass123!")
        self.client.login(username="tester", password="StrongPass123!")

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
        mock_send.return_value = {"sent": 1, "failed": 0, "errors": []}
        response = self.client.post(
            reverse("notifications:send_test"),
            data=json.dumps({"title": "x", "body": "y", "url": "/"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        mock_send.assert_called_once()

import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import (
    Notification,
    NotificationCategory,
    PushSubscription,
    UserNotificationPreference,
)
from .services import is_category_enabled_for_user, send_push_to_user


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
    def test_send_test_is_always_self_and_bypasses_preferences(self, mock_send):
        mock_send.return_value = {
            "notification_id": 1,
            "sent": 1,
            "failed": 0,
            "errors": [],
            "skipped": False,
            "skip_reason": None,
        }
        response = self.client.post(
            reverse("notifications:send_test"),
            data=json.dumps({"title": "x", "body": "y", "url": "/"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        mock_send.assert_called_once()
        args, kwargs = mock_send.call_args
        self.assertEqual(args[0], self.user)
        self.assertIsNone(kwargs["category"])
        self.assertFalse(kwargs["respect_preferences"])


class NotificationPreferenceTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="pref-user", password="secret123")
        self.category_on = NotificationCategory.objects.create(
            code="orders-test",
            name="Sipariş Test",
            sort_order=1,
        )
        self.category_off = NotificationCategory.objects.create(
            code="campaign-test",
            name="Kampanya Test",
            sort_order=2,
        )
        self.client.force_login(self.user)

    def test_missing_explicit_preference_is_disabled(self):
        self.assertFalse(is_category_enabled_for_user(self.user, self.category_on))
        self.assertFalse(is_category_enabled_for_user(self.user, self.category_off))

    def test_save_preferences_creates_explicit_values_for_all_active_categories(self):
        response = self.client.post(
            reverse("notifications:save_notification_preferences"),
            data=json.dumps({"enabled_category_ids": [self.category_off.pk]}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            UserNotificationPreference.objects.get(user=self.user, category=self.category_on).enabled
        )
        self.assertTrue(
            UserNotificationPreference.objects.get(user=self.user, category=self.category_off).enabled
        )

    @patch("notifications.services.send_push_to_subscription")
    def test_disabled_category_is_skipped_without_history(self, mock_send):
        UserNotificationPreference.objects.create(
            user=self.user,
            category=self.category_on,
            enabled=False,
        )
        PushSubscription.objects.create(
            user=self.user,
            endpoint="https://push.example/disabled",
            p256dh="p256dh",
            auth="auth",
        )

        result = send_push_to_user(
            self.user,
            "Sipariş",
            "Mesaj",
            category=self.category_on,
        )

        self.assertTrue(result["skipped"])
        self.assertEqual(result["skip_reason"], "preference_disabled")
        self.assertEqual(Notification.objects.filter(user=self.user).count(), 0)
        mock_send.assert_not_called()

    @patch("notifications.services.send_push_to_subscription")
    def test_enabled_category_sends_and_writes_category_to_history(self, mock_send):
        mock_send.return_value = (True, None)
        UserNotificationPreference.objects.create(
            user=self.user,
            category=self.category_off,
            enabled=True,
        )
        PushSubscription.objects.create(
            user=self.user,
            endpoint="https://push.example/enabled",
            p256dh="p256dh",
            auth="auth",
        )

        result = send_push_to_user(
            self.user,
            "Kampanya",
            "Mesaj",
            category=self.category_off,
        )

        self.assertFalse(result["skipped"])
        self.assertEqual(result["sent"], 1)
        item = Notification.objects.get(pk=result["notification_id"])
        self.assertEqual(item.category, self.category_off)
        payload = mock_send.call_args.args[1]
        self.assertEqual(payload["category"], self.category_off.code)


class TargetedNotificationTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.staff = User.objects.create_user(
            username="sender",
            password="secret123",
            is_staff=True,
        )
        self.recipient = User.objects.create_user(username="recipient", password="secret123")
        self.other = User.objects.create_user(username="other", password="secret123")
        self.category = NotificationCategory.objects.create(
            code="targeted-test",
            name="Hedefli Test",
        )
        PushSubscription.objects.create(
            user=self.recipient,
            endpoint="https://push.example/recipient",
            p256dh="p256dh",
            auth="auth",
        )
        UserNotificationPreference.objects.create(
            user=self.recipient,
            category=self.category,
            enabled=True,
        )

    @patch("notifications.services.send_push_to_subscription")
    def test_staff_can_send_to_selected_user(self, mock_send):
        mock_send.return_value = (True, None)
        self.client.force_login(self.staff)

        response = self.client.post(
            reverse("notifications:send_to_user"),
            data=json.dumps(
                {
                    "user_id": self.recipient.pk,
                    "category_id": self.category.pk,
                    "title": "Hedef",
                    "body": "Sadece alıcı",
                    "url": "/",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.assertEqual(Notification.objects.filter(user=self.recipient).count(), 1)
        self.assertEqual(Notification.objects.filter(user=self.other).count(), 0)
        self.assertEqual(Notification.objects.filter(user=self.staff).count(), 0)

    @patch("notifications.services.send_push_to_subscription")
    def test_recipient_preference_blocks_staff_send(self, mock_send):
        UserNotificationPreference.objects.filter(
            user=self.recipient,
            category=self.category,
        ).update(enabled=False)
        self.client.force_login(self.staff)

        response = self.client.post(
            reverse("notifications:send_to_user"),
            data=json.dumps(
                {
                    "user_id": self.recipient.pk,
                    "category_id": self.category.pk,
                    "title": "Hedef",
                    "body": "Engellenmeli",
                    "url": "/",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])
        self.assertTrue(data["skipped"])
        self.assertEqual(data["skip_reason"], "preference_disabled")
        self.assertEqual(Notification.objects.filter(user=self.recipient).count(), 0)
        mock_send.assert_not_called()

    def test_non_staff_cannot_send_to_other_user(self):
        self.client.force_login(self.other)
        response = self.client.post(
            reverse("notifications:send_to_user"),
            data=json.dumps(
                {
                    "user_id": self.recipient.pk,
                    "category_id": self.category.pk,
                    "title": "Yetkisiz",
                    "body": "Olmamalı",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Notification.objects.count(), 0)


class NotificationHistoryTests(TestCase):
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

        first = send_push_to_user(self.user, "Birinci", "İlk mesaj", respect_preferences=False)
        first_payload = mock_send.call_args.args[1]
        second = send_push_to_user(self.user, "İkinci", "İkinci mesaj", respect_preferences=False)
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
        other = User.objects.create_user(username="other-history", password="secret123")
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

        response = self.client.post(
            reverse("notifications:mark_all_notifications_read"),
            data="{}",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

        own.refresh_from_db()
        foreign.refresh_from_db()
        self.assertIsNotNone(own.read_at)
        self.assertIsNone(foreign.read_at)


class SignUpTests(TestCase):
    def setUp(self):
        self.category_a = NotificationCategory.objects.create(code="signup-general", name="Genel Kayıt")
        self.category_b = NotificationCategory.objects.create(code="signup-orders", name="Sipariş Kayıt")

    def test_login_page_links_to_signup(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("notifications:signup"))

    def test_signup_creates_normal_user_logs_in_and_initializes_preferences(self):
        response = self.client.post(
            reverse("notifications:signup"),
            data={
                "username": "new-user",
                "email": "new-user@example.com",
                "password1": "StrongSignupPass123!",
                "password2": "StrongSignupPass123!",
            },
        )

        self.assertRedirects(response, reverse("notifications:home"))
        user = get_user_model().objects.get(username="new-user")
        self.assertFalse(user.is_staff)
        self.assertEqual(user.email, "new-user@example.com")
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

        preferences = UserNotificationPreference.objects.filter(user=user)
        self.assertEqual(
            preferences.count(),
            NotificationCategory.objects.filter(is_active=True).count(),
        )
        self.assertFalse(preferences.filter(enabled=True).exists())

    def test_signed_in_user_is_redirected_away_from_signup(self):
        user = get_user_model().objects.create_user(username="existing", password="StrongPass123!")
        self.client.force_login(user)
        response = self.client.get(reverse("notifications:signup"))
        self.assertRedirects(response, reverse("notifications:home"))


class TargetUserStateTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.staff = User.objects.create_user(username="staff-state", password="secret123", is_staff=True)
        self.user = User.objects.create_user(username="state-user", email="state@example.com", password="secret123")
        self.category_on = NotificationCategory.objects.create(code="state-on", name="Açık Kategori", sort_order=1)
        self.category_off = NotificationCategory.objects.create(code="state-off", name="Kapalı Kategori", sort_order=2)
        UserNotificationPreference.objects.create(user=self.user, category=self.category_on, enabled=True)
        UserNotificationPreference.objects.create(user=self.user, category=self.category_off, enabled=False)
        PushSubscription.objects.create(
            user=self.user,
            endpoint="https://push.example/state-user",
            p256dh="p256dh",
            auth="auth",
        )

    def test_staff_can_view_selected_users_notification_state(self):
        self.client.force_login(self.staff)
        response = self.client.get(
            reverse("notifications:target_user_notification_state", args=[self.user.pk])
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["user"]["username"], self.user.username)
        self.assertEqual(data["subscription_count"], 1)
        prefs = {item["code"]: item["enabled"] for item in data["preferences"]}
        self.assertTrue(prefs[self.category_on.code])
        self.assertFalse(prefs[self.category_off.code])

    def test_normal_user_cannot_view_another_users_notification_state(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("notifications:target_user_notification_state", args=[self.staff.pk])
        )
        self.assertEqual(response.status_code, 403)

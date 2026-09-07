import json
import logging

from django.conf import settings
from django.urls import reverse
from py_vapid import VapidException
from pywebpush import WebPushException, webpush

from .models import Notification, PushSubscription, UserNotificationPreference

logger = logging.getLogger(__name__)


def send_push_to_subscription(subscription, payload):
    try:
        webpush(
            subscription_info=subscription.as_webpush_dict(),
            data=json.dumps(payload, ensure_ascii=False),
            vapid_private_key=settings.VAPID_PRIVATE_KEY_PATH,
            vapid_claims={"sub": settings.VAPID_SUBJECT},
            ttl=60,
            timeout=15,
        )
        return True, None
    except (WebPushException, VapidException) as exc:
        status_code = getattr(getattr(exc, "response", None), "status_code", None)
        if status_code in (404, 410):
            subscription.delete()
            logger.info("Expired push subscription deleted: %s", subscription.pk)
        else:
            logger.exception("Web push failed for subscription %s", subscription.pk)
        return False, str(exc)


def is_category_enabled_for_user(user, category):
    """Only an explicit enabled preference opts a user into a category."""
    if category is None:
        return True

    explicit = UserNotificationPreference.objects.filter(
        user=user,
        category=category,
    ).values_list("enabled", flat=True).first()

    return explicit is True


def send_push_to_user(user, title, body, url="/", category=None, respect_preferences=True):
    """Send one logical notification to every active browser subscription of a user.

    Categorized notifications honor that recipient's preference. If the category is
    disabled, no Notification history row and no push delivery are created.
    Uncategorized technical/test notifications can still be sent when desired.
    """
    if category is not None and not category.is_active:
        return {
            "notification_id": None,
            "sent": 0,
            "failed": 0,
            "errors": [],
            "skipped": True,
            "skip_reason": "category_inactive",
        }

    if respect_preferences and category is not None and not is_category_enabled_for_user(user, category):
        return {
            "notification_id": None,
            "sent": 0,
            "failed": 0,
            "errors": [],
            "skipped": True,
            "skip_reason": "preference_disabled",
        }

    notification = Notification.objects.create(
        user=user,
        category=category,
        title=title,
        body=body,
        url=url,
    )

    open_url = reverse("notifications:open_notification", args=[notification.pk])
    payload = {
        "notification_id": notification.pk,
        "title": title,
        "body": body,
        "url": open_url,
        "tag": f"notification-{notification.pk}",
        "category": category.code if category else None,
    }

    sent = 0
    failed = 0
    errors = []

    for subscription in PushSubscription.objects.filter(user=user).iterator():
        ok, error = send_push_to_subscription(subscription, payload)
        if ok:
            sent += 1
        else:
            failed += 1
            if error:
                errors.append(error)

    notification.sent_count = sent
    notification.failed_count = failed
    notification.save(update_fields=["sent_count", "failed_count"])

    return {
        "notification_id": notification.pk,
        "sent": sent,
        "failed": failed,
        "errors": errors,
        "skipped": False,
        "skip_reason": None,
    }

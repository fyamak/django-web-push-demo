import json
import logging

from django.conf import settings
from django.urls import reverse
from pywebpush import WebPushException, webpush

from .models import Notification, PushSubscription

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
    except WebPushException as exc:
        status_code = getattr(getattr(exc, "response", None), "status_code", None)
        if status_code in (404, 410):
            subscription.delete()
            logger.info("Expired push subscription deleted: %s", subscription.pk)
        else:
            logger.exception("Web push failed for subscription %s", subscription.pk)
        return False, str(exc)


def send_push_to_user(user, title, body, url="/"):
    # Her gönderim önce DB'ye ayrı bir bildirim kaydı olarak yazılır.
    # Bu kayıt işletim sistemi bildirim geçmişinden bağımsız kalıcı geçmiş sağlar.
    notification = Notification.objects.create(
        user=user,
        title=title,
        body=body,
        url=url,
    )

    # Aynı `tag` tarayıcı/işletim sisteminde önceki bildirimin değiştirilmesine
    # neden olur. Bu yüzden her bildirim için benzersiz tag kullanıyoruz.
    open_url = reverse("notifications:open_notification", args=[notification.pk])
    payload = {
        "notification_id": notification.pk,
        "title": title,
        "body": body,
        "url": open_url,
        "tag": f"notification-{notification.pk}",
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
    }

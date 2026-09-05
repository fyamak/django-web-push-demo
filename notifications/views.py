import json
from pathlib import Path

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .models import Notification, PushSubscription
from .services import send_push_to_user


def _read_public_key():
    path = Path(settings.VAPID_PUBLIC_KEY_PATH)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


@login_required
def home(request):
    notifications = Notification.objects.filter(user=request.user)[:50]
    return render(
        request,
        "notifications/home.html",
        {
            "vapid_public_key": _read_public_key(),
            "subscription_count": PushSubscription.objects.filter(user=request.user).count(),
            "notifications": notifications,
            "unread_count": Notification.objects.filter(user=request.user, read_at__isnull=True).count(),
        },
    )


@require_GET
def manifest(request):
    data = {
        "id": "/",
        "name": "Django Web Push Demo",
        "short_name": "Push Demo",
        "description": "Django PWA Web Push bildirim demo uygulaması",
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#111827",
        "icons": [
            {
                "src": "/static/notifications/icons/icon-192.png",
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "any maskable",
            },
            {
                "src": "/static/notifications/icons/icon-512.png",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any maskable",
            },
        ],
    }
    return JsonResponse(data)


@require_GET
def service_worker(request):
    response = render(request, "notifications/service-worker.js", content_type="application/javascript")
    response["Service-Worker-Allowed"] = "/"
    response["Cache-Control"] = "no-cache"
    return response


def _json_body(request):
    try:
        return json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


def _serialize_notification(notification):
    return {
        "id": notification.pk,
        "title": notification.title,
        "body": notification.body,
        "url": notification.url,
        "open_url": reverse("notifications:open_notification", args=[notification.pk]),
        "sent_count": notification.sent_count,
        "failed_count": notification.failed_count,
        "is_read": notification.is_read,
        "created_at": notification.created_at.isoformat(),
        "created_at_display": timezone.localtime(notification.created_at).strftime("%d.%m.%Y %H:%M"),
    }


@login_required
@require_GET
def notification_history(request):
    items = Notification.objects.filter(user=request.user)[:50]
    return JsonResponse(
        {
            "ok": True,
            "unread_count": Notification.objects.filter(user=request.user, read_at__isnull=True).count(),
            "items": [_serialize_notification(item) for item in items],
        }
    )


@login_required
@require_GET
def open_notification(request, notification_id):
    notification = get_object_or_404(Notification, pk=notification_id, user=request.user)
    if notification.read_at is None:
        notification.read_at = timezone.now()
        notification.save(update_fields=["read_at"])

    target = notification.url if notification.url.startswith("/") and not notification.url.startswith("//") else "/"
    return HttpResponseRedirect(target)


@login_required
@require_POST
def mark_all_notifications_read(request):
    updated = Notification.objects.filter(user=request.user, read_at__isnull=True).update(read_at=timezone.now())
    return JsonResponse({"ok": True, "updated": updated})


@login_required
@require_POST
def subscribe(request):
    data = _json_body(request)
    if not data:
        return JsonResponse({"ok": False, "error": "Geçersiz JSON."}, status=400)

    endpoint = data.get("endpoint")
    keys = data.get("keys") or {}
    p256dh = keys.get("p256dh")
    auth = keys.get("auth")

    if not endpoint or not p256dh or not auth:
        return JsonResponse({"ok": False, "error": "Subscription alanları eksik."}, status=400)

    subscription, created = PushSubscription.objects.update_or_create(
        endpoint=endpoint,
        defaults={
            "user": request.user,
            "p256dh": p256dh,
            "auth": auth,
            "user_agent": request.headers.get("User-Agent", "")[:1000],
        },
    )

    return JsonResponse({"ok": True, "created": created, "id": subscription.pk})


@login_required
@require_POST
def unsubscribe(request):
    data = _json_body(request)
    endpoint = (data or {}).get("endpoint")
    if not endpoint:
        return JsonResponse({"ok": False, "error": "Endpoint gerekli."}, status=400)

    deleted, _ = PushSubscription.objects.filter(user=request.user, endpoint=endpoint).delete()
    return JsonResponse({"ok": True, "deleted": deleted})


@login_required
@require_POST
def send_test(request):
    data = _json_body(request) or {}
    title = str(data.get("title") or "Django Web Push")[:120]
    body = str(data.get("body") or "Test bildirimi başarıyla gönderildi.")[:500]
    url = str(data.get("url") or "/")[:500]
    if not url.startswith("/") or url.startswith("//"):
        url = "/"

    result = send_push_to_user(request.user, title=title, body=body, url=url)
    # Push ulaşmasa bile notification geçmişe kaydedildiği için response içinde id döner.
    status = 200 if result["sent"] > 0 else 400
    return JsonResponse({"ok": result["sent"] > 0, **result}, status=status)

import json
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from .forms import SignUpForm
from .models import (
    Notification,
    NotificationCategory,
    PushSubscription,
    UserNotificationPreference,
)
from .services import is_category_enabled_for_user, send_push_to_user


def _read_public_key():
    path = Path(settings.VAPID_PUBLIC_KEY_PATH)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def _preference_items(user):
    categories = list(NotificationCategory.objects.filter(is_active=True))
    explicit = {
        item.category_id: item.enabled
        for item in UserNotificationPreference.objects.filter(user=user, category__in=categories)
    }
    return [
        {
            "id": category.pk,
            "code": category.code,
            "name": category.name,
            "description": category.description,
            "enabled": explicit.get(category.pk, False),
        }
        for category in categories
    ]


@require_http_methods(["GET", "POST"])
def signup(request):
    """Create a normal end-user account and sign the user in immediately."""
    if request.user.is_authenticated:
        return redirect("notifications:home")

    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                user = form.save()
                active_categories = NotificationCategory.objects.filter(is_active=True)
                UserNotificationPreference.objects.bulk_create(
                    [
                        UserNotificationPreference(user=user, category=category, enabled=False)
                        for category in active_categories
                    ],
                    ignore_conflicts=True,
                )
            login(request, user)
            return redirect("notifications:home")
    else:
        form = SignUpForm()

    return render(request, "registration/signup.html", {"form": form})


@login_required
def home(request):
    notifications = Notification.objects.filter(user=request.user).select_related("category")[:50]
    context = {
        "vapid_public_key": _read_public_key(),
        "subscription_count": PushSubscription.objects.filter(user=request.user).count(),
        "notifications": notifications,
        "unread_count": Notification.objects.filter(user=request.user, read_at__isnull=True).count(),
        "preference_items": _preference_items(request.user),
    }

    if request.user.is_staff:
        User = get_user_model()
        context["target_users"] = User.objects.filter(is_active=True).order_by("username")
        context["notification_categories"] = NotificationCategory.objects.filter(is_active=True)

    return render(request, "notifications/home.html", context)


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
        "category": (
            {"id": notification.category_id, "code": notification.category.code, "name": notification.category.name}
            if notification.category_id
            else None
        ),
        "sent_count": notification.sent_count,
        "failed_count": notification.failed_count,
        "is_read": notification.is_read,
        "created_at": notification.created_at.isoformat(),
        "created_at_display": timezone.localtime(notification.created_at).strftime("%d.%m.%Y %H:%M"),
    }


@login_required
@require_GET
def notification_history(request):
    items = Notification.objects.filter(user=request.user).select_related("category")[:50]
    return JsonResponse(
        {
            "ok": True,
            "unread_count": Notification.objects.filter(user=request.user, read_at__isnull=True).count(),
            "items": [_serialize_notification(item) for item in items],
        }
    )


@login_required
@require_GET
def notification_preferences(request):
    return JsonResponse({"ok": True, "items": _preference_items(request.user)})


@login_required
@require_POST
def save_notification_preferences(request):
    data = _json_body(request)
    if data is None:
        return JsonResponse({"ok": False, "error": "Geçersiz JSON."}, status=400)

    enabled_ids = data.get("enabled_category_ids", [])
    if not isinstance(enabled_ids, list):
        return JsonResponse({"ok": False, "error": "enabled_category_ids bir liste olmalı."}, status=400)

    try:
        enabled_ids = {int(item) for item in enabled_ids}
    except (TypeError, ValueError):
        return JsonResponse({"ok": False, "error": "Geçersiz kategori kimliği."}, status=400)

    categories = list(NotificationCategory.objects.filter(is_active=True))
    valid_ids = {category.pk for category in categories}
    unknown_ids = enabled_ids - valid_ids
    if unknown_ids:
        return JsonResponse({"ok": False, "error": "Aktif olmayan veya bilinmeyen kategori seçildi."}, status=400)

    with transaction.atomic():
        for category in categories:
            UserNotificationPreference.objects.update_or_create(
                user=request.user,
                category=category,
                defaults={"enabled": category.pk in enabled_ids},
            )

    return JsonResponse({"ok": True, "items": _preference_items(request.user)})


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
    """Technical self-test. Intentionally bypasses category preferences."""
    data = _json_body(request) or {}
    title = str(data.get("title") or "Django Web Push")[:120]
    body = str(data.get("body") or "Test bildirimi başarıyla gönderildi.")[:500]
    url = str(data.get("url") or "/")[:500]
    if not url.startswith("/") or url.startswith("//"):
        url = "/"

    result = send_push_to_user(
        request.user,
        title=title,
        body=body,
        url=url,
        category=None,
        respect_preferences=False,
    )
    status = 200 if result["sent"] > 0 else 400
    return JsonResponse({"ok": result["sent"] > 0, **result}, status=status)


@login_required
@require_GET
def target_user_notification_state(request, user_id):
    """Staff-only visibility into one recipient's push readiness and preferences."""
    if not request.user.is_staff:
        return JsonResponse({"ok": False, "error": "Bu işlem için yetkiniz yok."}, status=403)

    User = get_user_model()
    target_user = get_object_or_404(User, pk=user_id, is_active=True)
    return JsonResponse(
        {
            "ok": True,
            "user": {
                "id": target_user.pk,
                "username": target_user.username,
                "email": target_user.email,
            },
            "subscription_count": PushSubscription.objects.filter(user=target_user).count(),
            "preferences": _preference_items(target_user),
        }
    )


@login_required
@require_POST
def send_to_user(request):
    """Staff-only product notification sender. Recipient preferences are mandatory."""
    if not request.user.is_staff:
        return JsonResponse({"ok": False, "error": "Bu işlem için yetkiniz yok."}, status=403)

    data = _json_body(request)
    if not data:
        return JsonResponse({"ok": False, "error": "Geçersiz JSON."}, status=400)

    User = get_user_model()
    target_user = get_object_or_404(User, pk=data.get("user_id"), is_active=True)
    category = get_object_or_404(NotificationCategory, pk=data.get("category_id"), is_active=True)

    title = str(data.get("title") or "Yeni bildirim")[:120]
    body = str(data.get("body") or "Yeni bir bildiriminiz var.")[:500]
    url = str(data.get("url") or "/")[:500]
    if not url.startswith("/") or url.startswith("//"):
        url = "/"

    enabled = is_category_enabled_for_user(target_user, category)
    result = send_push_to_user(
        target_user,
        title=title,
        body=body,
        url=url,
        category=category,
        respect_preferences=True,
    )

    if result["skipped"] and result["skip_reason"] == "preference_disabled":
        return JsonResponse(
            {
                "ok": True,
                **result,
                "recipient": target_user.username,
                "category": category.name,
                "preference_enabled": enabled,
                "message": f"{target_user.username} kullanıcısı {category.name} bildirimlerini kapattığı için gönderim yapılmadı.",
            }
        )

    if result["skipped"]:
        return JsonResponse(
            {
                "ok": False,
                **result,
                "recipient": target_user.username,
                "category": category.name,
                "preference_enabled": enabled,
                "error": "Bildirim kategorisi aktif değil.",
            },
            status=400,
        )

    ok = result["sent"] > 0
    return JsonResponse(
        {
            "ok": ok,
            **result,
            "recipient": target_user.username,
            "category": category.name,
            "preference_enabled": enabled,
            "message": f"{target_user.username} kullanıcısına bildirim gönderildi." if ok else None,
            "error": None if ok else "Kullanıcının aktif push aboneliği yok veya gönderim başarısız oldu.",
        },
        status=200 if ok else 400,
    )

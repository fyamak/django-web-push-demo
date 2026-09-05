import json
from pathlib import Path

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST

from .models import PushSubscription
from .services import send_push_to_user


def _read_public_key():
    path = Path(settings.VAPID_PUBLIC_KEY_PATH)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


@login_required
def home(request):
    return render(
        request,
        "notifications/home.html",
        {
            "vapid_public_key": _read_public_key(),
            "subscription_count": PushSubscription.objects.filter(user=request.user).count(),
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
    if not url.startswith("/"):
        url = "/"

    result = send_push_to_user(request.user, title=title, body=body, url=url)
    status = 200 if result["sent"] > 0 else 400
    return JsonResponse({"ok": result["sent"] > 0, **result}, status=status)

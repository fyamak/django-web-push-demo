# Django Web Push + PWA Demo

Bu proje, mevcut bir Django uygulamasına entegre etmeden önce **ücretsiz standart Web Push** akışını gerçek olarak test etmek için hazırlanmıştır.

Akış:

1. Kullanıcı Django ile giriş yapar.
2. Tarayıcı/PWA bir Service Worker kaydeder.
3. Kullanıcı kendi isteğiyle bildirim izni verir.
4. `PushManager.subscribe()` tarayıcıya özel bir subscription üretir.
5. Subscription Django'da kullanıcıyla ilişkilendirilir.
6. Django `pywebpush` + VAPID ile tarayıcının push servisine mesaj yollar.
7. Service Worker push mesajını alır ve işletim sistemi bildirimi gösterir.

Firebase projesi, OneSignal hesabı veya Apple Developer üyeliği gerekmez. Kendi VPS maliyetin dışında bu demo için ayrıca bildirim servisi ücreti yoktur.

## Klasör yapısı

```text
django-web-push-demo/
├─ Dockerfile
├─ docker-compose.local.yml
├─ docker-compose.test.yml
├─ .env.local.example
├─ .env.test.example
├─ entrypoint.sh
├─ manage.py
├─ pushdemo/
│  └─ settings/
│     ├─ base.py
│     ├─ local.py
│     └─ test.py
├─ notifications/
│  ├─ models.py
│  ├─ services.py
│  ├─ views.py
│  ├─ urls.py
│  ├─ management/commands/
│  │  ├─ ensure_vapid_keys.py
│  │  ├─ ensure_demo_user.py
│  │  └─ send_push.py
│  ├─ templates/
│  └─ static/
├─ nginx/
└─ scripts/
```

## 1. Local Windows/Linux/macOS testi

### Environment dosyası

```bash
cp .env.local.example .env.local
```

Windows PowerShell:

```powershell
Copy-Item .env.local.example .env.local
```

### Ayağa kaldır

```bash
docker compose --env-file .env.local -f docker-compose.local.yml up --build
```

Tarayıcı:

```text
http://localhost:8000
```

Varsayılan demo hesabı:

```text
Kullanıcı: demo
Şifre: Demo12345!
```

`localhost`, Web API'lerinde geliştirme amacıyla güvenli bağlam istisnasıdır. Bu nedenle localde HTTP ile Service Worker / Push denenebilir.

Sayfada sırayla:

1. **Bildirimleri etkinleştir**
2. Tarayıcı izin sorusuna izin ver
3. **Test bildirimi gönder**

Container logları:

```bash
docker compose --env-file .env.local -f docker-compose.local.yml logs -f web
```

Django shell yerine doğrudan terminalden push göndermek için:

```bash
docker compose --env-file .env.local -f docker-compose.local.yml exec web \
  python manage.py send_push --username demo --title "Sunucudan" --body "Terminal testi"
```

## 2. Ubuntu test VPS: 31.97.37.175

Telefon üzerinden Push API için güvenilir HTTPS gerekir. Projede Nginx + Let's Encrypt IP sertifikası akışı hazırdır.

### Ön şartlar

Ubuntu sunucuda Docker + Docker Compose plugin kurulu olmalı. Güvenlik duvarında en az şu portlar açık olmalı:

```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

Ayrıca sağlayıcının panelinde ayrı firewall/security-group varsa 80 ve 443 orada da açık olmalı.

### Environment dosyasını hazırla

```bash
cp .env.test.example .env.test
nano .env.test
```

Özellikle şunları değiştir:

```text
DJANGO_SECRET_KEY=
POSTGRES_PASSWORD=
DEMO_PASSWORD=
VAPID_SUBJECT=mailto:senin-mail-adresin
LETSENCRYPT_EMAIL=senin-mail-adresin
```

Random Django secret üretmek için OpenSSL gerektirmeyen örnek:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

### İlk kurulum + HTTPS

```bash
chmod +x scripts/*.sh
./scripts/bootstrap_test_https.sh
```

Script şunları yapar:

1. Nginx'i önce HTTP modunda başlatır.
2. Django/PostgreSQL'i Docker ile başlatır.
3. Certbot 5.4 ile Let's Encrypt'ten `31.97.37.175` için `shortlived` IP sertifikası ister.
4. Nginx'i HTTPS konfigürasyonuna geçirir.
5. Nginx'i reload eder.

Sonra:

```text
https://31.97.37.175
```

### IP sertifikasının yenilenmesi

Let's Encrypt IP sertifikaları kısa ömürlü olduğu için yenilemeyi otomatik çalıştır.

Örnek root crontab:

```bash
sudo crontab -e
```

Örnek (repo yolu `/home/django-web-push-demo` ise):

```cron
0 */12 * * * cd /home/django-web-push-demo && ./scripts/renew_ip_cert.sh >> /var/log/django-push-cert-renew.log 2>&1
```

Certbot yalnızca gerektiğinde yeniler; script sonrasında Nginx reload edilir.

Test sunucusu logları:

```bash
docker compose --env-file .env.test -f docker-compose.test.yml logs -f web nginx
```

## 3. iPhone testi

1. iPhone/iPad en az iOS/iPadOS 16.4 kullanmalı.
2. Safari'de `https://31.97.37.175` aç.
3. Paylaş menüsü → **Ana Ekrana Ekle**.
4. Safari sekmesini değil, ana ekrandaki uygulama ikonunu aç.
5. Django hesabıyla giriş yap.
6. **Bildirimleri etkinleştir** düğmesine dokun.
7. iOS izin ekranında izin ver.
8. **Test bildirimi gönder** düğmesine bas.
9. Uygulamayı kapatıp tekrar Django terminal komutuyla push göndererek arka plan senaryosunu da dene.

Not: iOS'ta izin isteme işlemi bir kullanıcı etkileşiminin sonucu olmalıdır. Bu projede izin yalnızca buton tıklamasıyla istenir.

## 4. Android testi

Chrome/uyumlu tarayıcıda `https://31.97.37.175` aç. Menüden **Ana ekrana ekle / Uygulamayı yükle** seçeneğini kullan veya tarayıcı destekliyorsa sayfadaki “Uygulamayı yükle” düğmesini kullan. Ardından bildirim iznini etkinleştir.

## 5. VAPID anahtarları

Projede `openssl` komutuna ihtiyaç yoktur.

Container ilk başladığında:

```bash
python manage.py ensure_vapid_keys
```

otomatik çalışır ve Python `cryptography` ile P-256 VAPID key pair üretir.

Dosyalar:

```text
/app/keys/vapid_private.pem
/app/keys/vapid_public.txt
```

Docker volume'da saklandığı için container recreate/redeploy sonrası aynı kalır.

**Önemli:** VAPID private key'i sonradan değiştirirsen mevcut browser subscription'larını yeniden oluşturman gerekebilir. Gerçek uygulamada anahtarı kalıcı bir secret olarak sakla.

## 6. Django modelinin mantığı

Her tarayıcı/cihaz bir subscription kaydı oluşturur:

```python
class PushSubscription(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    endpoint = models.TextField(unique=True)
    p256dh = models.TextField()
    auth = models.TextField()
```

Aynı kullanıcı telefon + masaüstü + başka tarayıcıdan izin verirse birden fazla kaydı olur. Push gönderiminde kullanıcının bütün kayıtlarına gönderilir.

## 7. Gerçek uygulamana entegrasyonda kullanacağın servis

Örneğin sipariş oluştuğunda:

```python
from notifications.services import send_push_to_user

send_push_to_user(
    user=request.user,
    title="Yeni işlem",
    body="İşleminiz başarıyla tamamlandı.",
    url="/orders/123/",
)
```

Bu fonksiyonu Django signal, Celery task, management command, view veya kendi business servisinden çağırabilirsin.

Çok fazla kullanıcıya toplu bildirim göndereceksen HTTP request içinde binlerce push göndermek yerine Celery/RQ gibi queue kullanmak daha doğru olur.

## 8. Güvenlik notları

- Subscription endpoint değerini secret/capability URL gibi değerlendir.
- Subscribe/unsubscribe endpoint'leri login gerektirir.
- JSON POST'larında Django CSRF koruması korunmuştur; `csrf_exempt` kullanılmamıştır.
- Private VAPID key git'e yazılmaz.
- Test ortamında secure session ve CSRF cookie açılmıştır.
- Gerçek uygulamada kullanıcı tercihleri için ayrıca `notifications_enabled`, kategori seçimi gibi ayarlar eklemek iyi olur.

## 9. Sık görülen problemler

### `Notification.permission = denied`
Tarayıcı/site ayarlarından bildirim iznini sıfırla ve tekrar dene.

### Telefonda `window.isSecureContext = false`
HTTPS sertifikası geçerli değildir veya HTTP ile açıyorsundur. `https://31.97.37.175` kullan.

### iPhone'da izin düğmesi çalışıyor ama notification gelmiyor
Ana ekrandan kurulan PWA üzerinden açtığından emin ol. Normal Safari sekmesi iOS Web Push senaryosu için yeterli değildir.

### Django'da `sent=0`
Kullanıcının veritabanında aktif subscription kaydı yoktur. Önce ilgili cihazda bildirim aboneliğini aç.

### 404 / 410 push response
Tarayıcı subscription'ı artık geçersizdir. Servis bu kaydı otomatik siler; kullanıcı tekrar bildirimleri etkinleştirebilir.

### VPS'ten Apple push endpointlerine erişim engelli
Apple cihazları için sunucunun `*.push.apple.com` adreslerine outbound HTTPS erişimini engelleme.

## 10. Testleri çalıştırma

Local container çalışırken:

```bash
docker compose --env-file .env.local -f docker-compose.local.yml exec web python manage.py test
```

## Mimari özet

```text
Django user
   |
   v
Browser / Home Screen PWA
   |  PushManager.subscribe()
   v
Django PushSubscription DB
   |
   | pywebpush + VAPID
   v
Browser vendor push service
   |
   v
Service Worker (push event)
   |
   v
OS Notification
```

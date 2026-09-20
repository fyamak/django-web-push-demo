# testplatform.farmingo.com.tr deployment

Bu deployment, sunucuda Nginx'in host uzerinde zaten calistigini varsayar.
Docker icinde ikinci bir Nginx/Certbot baslatilmaz.

Bu surumde `.env`, `.env.server` veya `env_file` kullanilmaz. Test sunucusu
ayarlarinin tamami `pushdemo/settings/test.py` ve `docker-compose.test.yml`
icinde dogrudan tanimlidir.

## Mimari

- Internet: `https://testplatform.farmingo.com.tr`
- Host Nginx: `443`
- Django/Gunicorn container: host uzerinde sadece `127.0.0.1:5001`
- Container ici Gunicorn: `8000`
- Static host dizini: `/var/www/platform_farmingo/`
- PostgreSQL: yalnizca Docker network icinde

## Ilk kurulum

```bash
cd /home/notification/django-web-push-demo
sudo mkdir -p /var/www/platform_farmingo
sudo chmod 755 /var/www/platform_farmingo

docker compose -f docker-compose.test.yml up -d --build
```

Kontrol:

```bash
docker compose -f docker-compose.test.yml ps
docker compose -f docker-compose.test.yml logs --tail=200 web db
curl -I http://127.0.0.1:5001/
sudo nginx -t
sudo systemctl reload nginx
```

Disaridan:

```text
https://testplatform.farmingo.com.tr
```

## Ayar degistirme

Test sunucusu Django ayarlari:

```text
pushdemo/settings/test.py
```

PostgreSQL container ayarlari:

```text
docker-compose.test.yml
```

DB kullanici/parolasini degistirirsen iki dosyada da ayni degeri kullanmalisin.

## Host Nginx

Mevcut config'te `/` icin `proxy_pass http://127.0.0.1:5001;` ve `/static/`
icin `alias /var/www/platform_farmingo/;` bu compose ile uyumludur.

Projede Django Channels/WebSocket kullanilmadigi icin eski projeden kalan `/ws/`
location bloguna ihtiyac yoktur ve kaldirilmasi onerilir.

## Ayni domain'deki eski Web Push projesi

Tarayicida eski Service Worker / PushSubscription kalabilir. Bu surum,
subscription'in `applicationServerKey` degerini yeni VAPID public key ile
karsilastirir; uyusmuyorsa eski aboneligi kaldirir. Kullanici daha sonra
"Bildirimleri etkinlestir" ile yeni anahtara bagli abonelik olusturabilir.

VAPID private/public key'leri `vapid_test` Docker volume'unda saklanir. Bu volume'u
her deploy'da silmeyin; silerseniz tum istemcilerin yeniden abone olmasi gerekir.

## Kullanıcı bazlı bildirim sürümüne güncelleme

Bu sürüm `0003_notification_categories_and_preferences` migration'ını içerir. Container başlangıcında `python manage.py migrate --noinput` otomatik çalıştığı için normal rebuild yeterlidir:

```bash
cd /home/notification/django-web-push-demo
docker-compose -f docker-compose.test.yml down
docker-compose -f docker-compose.test.yml up -d --build
```

Veritabanı ve VAPID volume'larını silmeyin; `down -v` kullanmayın.

Kontrol:

```bash
docker-compose -f docker-compose.test.yml logs --tail=200 web
docker-compose -f docker-compose.test.yml exec web python manage.py showmigrations notifications
```

`0003_notification_categories_and_preferences` satırında `[X]` görülmelidir.

Test ortamında `demo` kullanıcısı `DEMO_IS_STAFF = True` ile gönderici panelini görebilir. Hedef kullanıcıların ayrıca kendi hesaplarıyla giriş yapıp **Bildirimleri etkinleştir** demesi ve en az bir bildirim kategorisini seçip tercihlerini kaydetmesi gerekir.

## Yeni kullanıcı kaydı ve çoklu kullanıcı testi

Yeni kullanıcılar giriş ekranındaki **Kayıt ol** bağlantısından veya doğrudan `/signup/` adresinden hesap oluşturabilir. Bu değişiklik yeni bir veritabanı migration'ı gerektirmez; mevcut Django `User` modeli kullanılır.

Yeni kayıt olan kullanıcılar `staff` değildir. İlk girişten sonra:

1. **Bildirimleri etkinleştir** ile o tarayıcı/cihazın push aboneliğini kendi hesabına bağlar.
2. **Bildirim tercihlerim** bölümünden almak istediği kategorileri açar ve kaydeder.
3. Staff kullanıcı gönderim panelinde bu kullanıcıyı hedef olarak seçebilir; panel alıcının aktif push aboneliği sayısını ve kategori tercihlerini gösterir.

Aynı tarayıcı profilindeki tek PushSubscription son giriş yapan kullanıcıyla eşleştirilir. Birden fazla kullanıcıyı aynı anda test etmek için farklı tarayıcı profilleri, gizli pencere profilleri veya farklı cihazlar kullanmak daha nettir.

Bu sürümde `docker-compose.test.yml` ayrıca `DJANGO_SETTINGS_MODULE=pushdemo.settings.test` değerini doğrudan container ortamına verir. Böylece `docker-compose exec web python manage.py ...` komutları da test ayarlarını kullanır. Port yayını `127.0.0.1:5001:8000` olarak kalmalıdır.

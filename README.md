# Django Web Push Demo

Bu proje Django uygulamasında **ücretsiz standart Web Push** kullanımını local ve test sunucusunda denemek için hazırlanmıştır.

Kullanılan yapı:

- Django 5.2
- Host makinede PostgreSQL
- Docker / Docker Compose (Django web container)
- PWA manifest
- Service Worker
- Web Push API
- VAPID
- `pywebpush`
- Test ortamında Nginx + HTTPS

Bu sürümde **`.env` dosyası kullanılmaz**. Local ve test ayarları doğrudan Django settings dosyalarında ve ilgili Docker Compose dosyalarında tanımlıdır.

## Proje yapısı

```text
pushdemo/
  settings/
    base.py
    local.py
    test.py
notifications/
docker-compose.local.yml
docker-compose.test.yml
entrypoint.sh
nginx/
scripts/
```

## Local ayarlar

Django local ayarları:

```text
pushdemo/settings/local.py
```

PostgreSQL local bilgileri `local.py` icinde tanimlidir. PostgreSQL artik Docker servisi degildir; host makinede calisir:

```text
Database: pushdemo
User: pushdemo
Password: pushdemo-local-password
Host: host.docker.internal (Django container tarafindan)
Port: 5432
```

Bu değerler demo içindir.

## Local çalıştırma

Windows PowerShell'de proje dizininde:

```powershell
docker-compose -f docker-compose.local.yml up --build
```

veya yeni Docker Compose komutu ile:

```powershell
docker compose -f docker-compose.local.yml up --build
```

Artık `--env-file` kullanmana gerek yoktur.

Uygulama:

```text
http://localhost:8000
```

Demo kullanıcı:

```text
Kullanıcı adı: demo
Şifre: Demo12345!
```

Host PostgreSQL daha once kurulmus ve `pushdemo` DB/user olusturulmus olmalidir. Ilk acilista web container:

1. PostgreSQL baglantisini bekler ve migration'ları uygular,
2. VAPID anahtarlarını oluşturur,
3. demo kullanıcısını oluşturur,
4. Django development server'ı başlatır.

VAPID anahtarları `vapid_local` Docker volume'unda tutulur.

## Local logları izleme

```powershell
docker compose -f docker-compose.local.yml logs -f web
```

PostgreSQL host servisidir; loglari isletim sistemindeki PostgreSQL servisinden izlenir.

## Terminalden test push gönderme

```powershell
docker compose -f docker-compose.local.yml exec web python manage.py send_push --username demo --title "Test" --body "Django push bildirimi"
```

Önce tarayıcı üzerinden giriş yapıp **Bildirimleri etkinleştir** butonuna basman gerekir. Böylece tarayıcı subscription bilgisi veritabanına kaydedilir.


## PostgreSQL artik Docker disinda

Bu surumde `docker-compose.local.yml` ve `docker-compose.test.yml` icinde `db` servisi yoktur. Ayrintili host PostgreSQL kurulumu ve mevcut Docker DB verisini kaybetmeden tasima adimlari:

```text
DATABASE_SETUP.md
```

Test sunucusunda web container `network_mode: host` ile calisir ve host PostgreSQL'e `127.0.0.1:5432` uzerinden baglanir. Gunicorn da sadece `127.0.0.1:5001` uzerinde dinler.

## Test sunucusu — testplatform.farmingo.com.tr

Bu sürüm, test sunucusunda Nginx'in **host üzerinde zaten çalıştığı** düzene göre
hazırlanmıştır. Docker ikinci bir Nginx/Certbot başlatmaz.

Ayrıntılı kurulum ve kontrol komutları:

```text
SERVER_DEPLOY.md
```

Özet:

```bash
sudo mkdir -p /var/www/platform_farmingo
docker compose -f docker-compose.test.yml up -d --build
```

Bu sürümde `.env`, `.env.server` ve `env_file` kullanılmaz. Test ayarları doğrudan `pushdemo/settings/test.py` ve `docker-compose.test.yml` içindedir.

Django/Gunicorn host üzerinde yalnızca `127.0.0.1:5001` portuna yayınlanır.
Mevcut host Nginx `https://testplatform.farmingo.com.tr` trafiğini bu porta proxy eder.
`collectstatic` çıktısı `/var/www/platform_farmingo/` dizinine yazılır.

Eski IP tabanlı Docker Nginx/Certbot kurulumu bu sunucu düzeninde kullanılmaz.

## Local / test ayrımı nasıl yapılıyor?

Compose dosyaları `entrypoint.sh` dosyasına yalnızca çalışma modunu (`local` / `test`) gönderir; uygulama ayarları için `.env` dosyası okunmaz.

Local compose:

```yaml
command: ["local"]
```

Test compose:

```yaml
command: ["test"]
```

`entrypoint.sh` buna göre:

```text
pushdemo.settings.local
```

veya:

```text
pushdemo.settings.test
```

ayarını seçer.

## Ayar değiştirmek istersen

Local için:

```text
pushdemo/settings/local.py
docker-compose.local.yml
```

Test için:

```text
pushdemo/settings/test.py
docker-compose.test.yml
```

PostgreSQL kullanıcı adı/parolasını değiştirirsen ilgili Django settings dosyasini ve host PostgreSQL rol parolasini birlikte degistirmen gerekir.

## Demo kullanıcı bilgileri

Şu dosyada tanımlıdır:

```text
pushdemo/settings/base.py
```

```python
DEMO_USERNAME = "demo"
DEMO_PASSWORD = "Demo12345!"
DEMO_EMAIL = "demo@example.com"
```

## Web Push akışı

```text
Kullanıcı login olur
       ↓
Bildirimleri etkinleştir
       ↓
Service Worker register edilir
       ↓
PushManager subscription oluşturur
       ↓
endpoint + p256dh + auth Django'ya gönderilir
       ↓
PushSubscription tablosuna kaydedilir
       ↓
Django pywebpush ile VAPID imzalı mesaj gönderir
       ↓
Browser Push Service
       ↓
Service Worker push event
       ↓
Telefon / bilgisayar bildirimi
```

## iPhone

iPhone'da uygulamayı Safari üzerinden açıp **Ana Ekrana Ekle** yaptıktan sonra ana ekrandaki PWA üzerinden bildirim izni vermen gerekir. Cihazın iOS/iPadOS **16.4 veya üzeri** olması gerekiyor.

## Önemli

Bu proje entegrasyon demosudur. Şifreler ve Django `SECRET_KEY` değerleri bilerek doğrudan dosyalara yazılmıştır çünkü bu sürümde `.env` kullanılmaması istenmiştir.

Gerçek production uygulamasına geçirirken DB parolası, Django `SECRET_KEY` ve benzeri secret değerleri repository içinde tutmamak daha doğru olur.

## Bildirimlerin ayrı görünmesi ve geçmiş

Her gönderim artık `Notification` tablosunda ayrı bir kayıt oluşturur. Push payload içindeki `tag` değeri de `notification-<id>` biçiminde benzersizdir.

Web Notification API'de aynı `tag` değerini tekrar kullanmak önceki bildirimin yeni bildirimle değiştirilmesine neden olabilir. Bu nedenle sabit tag kullanılmamalıdır.

Uygulama ana sayfasındaki **Bildirim geçmişi** bölümü son 50 bildirimi gösterir. İşletim sistemi bildirimi kullanıcı tarafından temizlense bile bu geçmiş Django veritabanında kalır. Bildirime tıklanınca kayıt okundu olarak işaretlenir ve bildirimin hedef adresine yönlendirilir.

## Kullanıcı bazlı gönderim ve bildirim tercihleri

Bu sürümde gerçek bildirimler kullanıcı bazlı gönderilir.

- `staff` yetkili kullanıcı ana ekrandaki **Kullanıcıya bildirim gönder** bölümünden hedef kullanıcıyı seçer.
- Gönderimde bir bildirim kategorisi seçmek zorunludur.
- Hedef kullanıcının o kategori için açık tercihi yoksa gönderim **atlanır**.
- Tercih kapalı olduğunda push gönderilmez ve kullanıcının bildirim geçmişine kayıt oluşturulmaz.
- Kullanıcı kendi **Bildirim tercihlerim** bölümünden kategorileri açıp kapatır.
- Yeni kategoriler Django admin üzerinden `NotificationCategory` tablosundan yönetilebilir.
- Teknik **Kendime test bildirimi** kategori tercihlerinden bağımsızdır; yalnızca Web Push altyapısını test etmek içindir.

İlk migration ile örnek kategoriler oluşturulur:

```text
Genel
Siparişler
Kampanyalar
Sistem
```

Yeni kullanıcılar hiçbir kategoriye otomatik abone edilmez. Kullanıcının kategoriyi açıkça seçip tercihlerini kaydetmesi gerekir.

### İlgili modeller

```text
PushSubscription
NotificationCategory
UserNotificationPreference
Notification
```

`Notification.category` alanı sayesinde geçmişte bildirimin hangi kategoriden geldiği de görülebilir.

### Staff gönderim API'si

```text
POST /api/push/send-to-user/
```

Örnek JSON:

```json
{
  "user_id": 12,
  "category_id": 2,
  "title": "Siparişiniz hazır",
  "body": "Siparişiniz teslimata hazırlandı.",
  "url": "/orders/123/"
}
```

Bu endpoint yalnızca `is_staff=True` kullanıcılar tarafından kullanılabilir.

### Tercih API'si

Kullanıcının kendi tercihlerini okumak:

```text
GET /api/notification-preferences/
```

Kaydetmek:

```text
POST /api/notification-preferences/save/
```

Örnek:

```json
{
  "enabled_category_ids": [1, 2]
}
```

Listede olmayan aktif kategoriler kapalı olarak kaydedilir.

### Management command

Kategori tercihine uyarak kullanıcıya gönderim:

```bash
docker compose -f docker-compose.test.yml exec web \
  python manage.py send_push \
  --username demo \
  --category orders \
  --title "Sipariş" \
  --body "Siparişiniz hazır."
```

Teknik/özel durumda tercihi yok saymak gerekirse `--ignore-preferences` kullanılabilir. Normal ürün bildirimlerinde bu seçenek kullanılmamalıdır.

## Kullanıcı kaydı ve kullanıcı bazlı bildirimler

- `/signup/` üzerinden yeni kullanıcılar kendi hesaplarını oluşturabilir.
- Yeni kayıtlar normal kullanıcıdır (`is_staff=False`) ve aktif bildirim kategorileri başlangıçta kapalıdır; kullanıcı ana ekrandan kendi tercihlerini açar.
- Her tarayıcı push aboneliği giriş yapan kullanıcıyla eşleştirilir. Bildirim gönderimi yalnızca seçilen kullanıcının aboneliklerine yapılır.
- Staff kullanıcılar ana ekrandaki **Kullanıcıya bildirim gönder** bölümünden hedef kullanıcıyı seçebilir ve seçilen kullanıcının aktif push aboneliği ile kategori tercihlerini görebilir.
- Kategorili gönderimler alıcının tercihini zorunlu olarak kontrol eder. Kullanıcı kategoriyi kapattıysa push ve bildirim geçmişi kaydı oluşturulmaz.
- Test sunucusunda web container portu yalnızca `127.0.0.1:5001` üzerinde yayınlanır; internete doğrudan açılmaz ve host Nginx üzerinden erişilir.

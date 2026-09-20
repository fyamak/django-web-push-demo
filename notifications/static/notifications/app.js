(() => {
  const logEl = document.getElementById("log");
  const enableBtn = document.getElementById("enableBtn");
  const disableBtn = document.getElementById("disableBtn");
  const sendBtn = document.getElementById("sendBtn");
  const installBtn = document.getElementById("installBtn");
  const markAllReadBtn = document.getElementById("markAllReadBtn");
  const historyList = document.getElementById("historyList");
  const unreadCount = document.getElementById("unreadCount");
  const savePreferencesBtn = document.getElementById("savePreferencesBtn");
  const sendToUserBtn = document.getElementById("sendToUserBtn");
  const sendToUserResult = document.getElementById("sendToUserResult");
  const targetUserSelect = document.getElementById("targetUser");
  const targetCategorySelect = document.getElementById("targetCategory");
  const targetUserMeta = document.getElementById("targetUserMeta");
  const targetUserPreferences = document.getElementById("targetUserPreferences");
  const publicKey = document.body.dataset.vapidPublicKey;
  let deferredInstallPrompt = null;

  function log(message, data = null) {
    const stamp = new Date().toLocaleTimeString();
    let line = `[${stamp}] ${message}`;
    if (data !== null) line += `\n${JSON.stringify(data, null, 2)}`;
    logEl.textContent = `${line}\n\n${logEl.textContent}`;
  }

  function getCookie(name) {
    const cookies = document.cookie ? document.cookie.split(";") : [];
    for (const cookie of cookies) {
      const item = cookie.trim();
      if (item.startsWith(`${name}=`)) return decodeURIComponent(item.substring(name.length + 1));
    }
    return null;
  }

  function urlBase64ToUint8Array(base64String) {
    const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
    const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
    const rawData = atob(base64);
    return Uint8Array.from([...rawData].map((char) => char.charCodeAt(0)));
  }

  async function postJson(url, data = {}) {
    const response = await fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCookie("csrftoken"),
      },
      body: JSON.stringify(data),
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.error || payload.errors?.join(" | ") || `HTTP ${response.status}`);
    return payload;
  }

  async function getRegistration() {
    if (!("serviceWorker" in navigator)) throw new Error("Bu tarayıcı Service Worker desteklemiyor.");
    return navigator.serviceWorker.register("/service-worker.js", { scope: "/" });
  }

  function applicationServerKeyMatches(subscription) {
    const existingKey = subscription?.options?.applicationServerKey;
    if (!existingKey || !publicKey) return false;

    const expected = urlBase64ToUint8Array(publicKey);
    const current = new Uint8Array(existingKey);
    if (current.length !== expected.length) return false;
    return current.every((value, index) => value === expected[index]);
  }

  async function getCompatibleSubscription(registration) {
    const subscription = await registration.pushManager.getSubscription();
    if (!subscription) return null;

    if (!applicationServerKeyMatches(subscription)) {
      log("Eski VAPID anahtarına ait push aboneliği bulundu; yenileniyor.");
      try {
        await postJson("/api/push/unsubscribe/", { endpoint: subscription.endpoint });
      } catch (_) {
        // Yeni veritabanında eski endpoint'in bulunmaması normaldir.
      }
      await subscription.unsubscribe();
      return null;
    }

    return subscription;
  }

  async function syncExistingSubscription() {
    const registration = await getRegistration();
    const subscription = await getCompatibleSubscription(registration);
    if (subscription) {
      await postJson("/api/push/subscribe/", subscription.toJSON());
      log("Var olan tarayıcı aboneliği Django kullanıcısıyla eşitlendi.");
    }
    return subscription;
  }

  async function enableNotifications() {
    try {
      if (!publicKey) throw new Error("VAPID public key bulunamadı.");
      if (!("Notification" in window)) throw new Error("Bu tarayıcı Notification API desteklemiyor.");
      if (!window.isSecureContext) throw new Error("Web Push için HTTPS gerekir (localhost hariç). ");

      const permission = await Notification.requestPermission();
      document.getElementById("permissionStatus").textContent = permission;
      if (permission !== "granted") throw new Error(`Bildirim izni verilmedi: ${permission}`);

      const registration = await getRegistration();
      let subscription = await getCompatibleSubscription(registration);
      if (!subscription) {
        subscription = await registration.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: urlBase64ToUint8Array(publicKey),
        });
      }

      const result = await postJson("/api/push/subscribe/", subscription.toJSON());
      log("Bildirim aboneliği hazır.", result);
      alert("Bildirim aboneliği başarıyla açıldı.");
    } catch (error) {
      log(`Abonelik hatası: ${error.message}`);
      alert(error.message);
    }
  }

  async function disableNotifications() {
    try {
      const registration = await getRegistration();
      const subscription = await registration.pushManager.getSubscription();
      if (!subscription) {
        log("Kapatılacak aktif abonelik bulunamadı.");
        return;
      }

      await postJson("/api/push/unsubscribe/", { endpoint: subscription.endpoint });
      await subscription.unsubscribe();
      log("Bildirim aboneliği kapatıldı.");
      alert("Bildirimler kapatıldı.");
    } catch (error) {
      log(`Abonelik kapatma hatası: ${error.message}`);
      alert(error.message);
    }
  }

  function renderHistory(items, count) {
    unreadCount.textContent = count;
    historyList.replaceChildren();

    if (!items.length) {
      const empty = document.createElement("div");
      empty.className = "history-empty";
      empty.textContent = "Henüz bildirim yok.";
      historyList.appendChild(empty);
      return;
    }

    for (const item of items) {
      const link = document.createElement("a");
      link.href = item.open_url;
      link.className = `notification-item${item.is_read ? "" : " unread"}`;

      const head = document.createElement("div");
      head.className = "notification-head";

      const title = document.createElement("strong");
      title.textContent = item.title;
      head.appendChild(title);

      const date = document.createElement("span");
      date.className = "notification-date";
      date.textContent = item.created_at_display;
      head.appendChild(date);

      const body = document.createElement("div");
      body.className = "notification-body";
      body.textContent = item.body;

      const meta = document.createElement("div");
      meta.className = "notification-meta";
      const categoryPrefix = item.category?.name ? `${item.category.name} · ` : "";
      meta.textContent = `${categoryPrefix}Gönderim: ${item.sent_count} başarılı, ${item.failed_count} başarısız${item.is_read ? " · okundu" : " · okunmadı"}`;

      link.append(head, body, meta);
      historyList.appendChild(link);
    }
  }

  async function refreshNotificationHistory() {
    try {
      const response = await fetch("/api/notifications/", { credentials: "same-origin" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const result = await response.json();
      renderHistory(result.items || [], result.unread_count || 0);
    } catch (error) {
      log(`Bildirim geçmişi yenilenemedi: ${error.message}`);
    }
  }

  async function markAllRead() {
    try {
      await postJson("/api/notifications/mark-all-read/");
      await refreshNotificationHistory();
    } catch (error) {
      log(`Okundu işaretleme hatası: ${error.message}`);
    }
  }

  async function savePreferences() {
    try {
      savePreferencesBtn.disabled = true;
      const enabledCategoryIds = [...document.querySelectorAll(".preference-checkbox:checked")].map((item) => Number(item.value));
      const result = await postJson("/api/notification-preferences/save/", {
        enabled_category_ids: enabledCategoryIds,
      });
      log("Bildirim tercihleri kaydedildi.", result);
      alert("Bildirim tercihlerin kaydedildi.");
    } catch (error) {
      log(`Tercih kaydetme hatası: ${error.message}`);
      alert(error.message);
    } finally {
      savePreferencesBtn.disabled = false;
    }
  }

  async function sendTest() {
    try {
      sendBtn.disabled = true;
      const result = await postJson("/api/push/send-test/", {
        title: document.getElementById("title").value,
        body: document.getElementById("body").value,
        url: document.getElementById("url").value,
      });
      log("Django teknik push gönderim sonucu", result);
      await refreshNotificationHistory();
    } catch (error) {
      await refreshNotificationHistory();
      log(`Push gönderim hatası: ${error.message}`);
      alert(error.message);
    } finally {
      sendBtn.disabled = false;
    }
  }

  async function refreshTargetUserState() {
    if (!targetUserSelect || !targetCategorySelect || !targetUserMeta || !targetUserPreferences) return;

    const userId = Number(targetUserSelect.value);
    if (!userId) return;

    targetUserMeta.textContent = "Kullanıcı bilgileri yükleniyor…";
    targetUserPreferences.replaceChildren();

    try {
      const response = await fetch(`/api/users/${userId}/notification-state/`, {
        credentials: "same-origin",
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(result.error || `HTTP ${response.status}`);

      const emailText = result.user?.email ? ` · ${result.user.email}` : "";
      targetUserMeta.textContent = `${result.user.username}${emailText} · aktif push aboneliği: ${result.subscription_count}`;

      const preferenceMap = new Map((result.preferences || []).map((item) => [Number(item.id), item]));
      for (const option of targetCategorySelect.options) {
        const categoryId = Number(option.value);
        const pref = preferenceMap.get(categoryId);
        if (!option.dataset.baseLabel) option.dataset.baseLabel = option.textContent;
        option.dataset.preferenceEnabled = pref?.enabled ? "true" : "false";
        option.textContent = `${option.dataset.baseLabel}${pref?.enabled ? " · açık" : " · kapalı"}`;
      }

      for (const pref of result.preferences || []) {
        const badge = document.createElement("span");
        badge.className = `recipient-pref ${pref.enabled ? "on" : "off"}`;
        badge.textContent = `${pref.name}: ${pref.enabled ? "açık" : "kapalı"}`;
        targetUserPreferences.appendChild(badge);
      }

      if (!(result.preferences || []).length) {
        const empty = document.createElement("span");
        empty.className = "small";
        empty.textContent = "Aktif bildirim kategorisi bulunmuyor.";
        targetUserPreferences.appendChild(empty);
      }
    } catch (error) {
      targetUserMeta.textContent = `Alıcı durumu alınamadı: ${error.message}`;
      log(`Alıcı durumu alınamadı: ${error.message}`);
    }
  }

  async function sendToUser() {
    try {
      sendToUserBtn.disabled = true;
      sendToUserResult.className = "result-box";
      sendToUserResult.textContent = "";

      const result = await postJson("/api/push/send-to-user/", {
        user_id: Number(targetUserSelect.value),
        category_id: Number(targetCategorySelect.value),
        title: document.getElementById("targetTitle").value,
        body: document.getElementById("targetBody").value,
        url: document.getElementById("targetUrl").value,
      });

      const message = result.message || `Gönderim sonucu: ${result.sent} başarılı, ${result.failed} başarısız.`;
      sendToUserResult.textContent = message;
      sendToUserResult.className = `result-box visible${result.skipped ? " warn" : " ok"}`;
      log("Kullanıcı bazlı bildirim sonucu", result);

      if (Number(targetUserSelect.value) === Number(document.body.dataset.userId)) {
        await refreshNotificationHistory();
      }
    } catch (error) {
      sendToUserResult.textContent = error.message;
      sendToUserResult.className = "result-box visible warn";
      log(`Kullanıcıya gönderim hatası: ${error.message}`);
    } finally {
      sendToUserBtn.disabled = false;
    }
  }

  async function init() {
    document.getElementById("secureStatus").textContent = window.isSecureContext ? "Uygun" : "Uygun değil";
    document.getElementById("permissionStatus").textContent = "Notification" in window ? Notification.permission : "Desteklenmiyor";

    try {
      const registration = await getRegistration();
      document.getElementById("swStatus").textContent = registration ? "Kayıtlı" : "Kayıt başarısız";
      await syncExistingSubscription();
      await refreshNotificationHistory();
      await refreshTargetUserState();
      log("Uygulama hazır.");
    } catch (error) {
      document.getElementById("swStatus").textContent = "Hata";
      await refreshNotificationHistory();
      log(`Başlangıç hatası: ${error.message}`);
    }
  }

  window.addEventListener("beforeinstallprompt", (event) => {
    event.preventDefault();
    deferredInstallPrompt = event;
    installBtn.hidden = false;
  });

  installBtn.addEventListener("click", async () => {
    if (!deferredInstallPrompt) return;
    deferredInstallPrompt.prompt();
    await deferredInstallPrompt.userChoice;
    deferredInstallPrompt = null;
    installBtn.hidden = true;
  });

  enableBtn.addEventListener("click", enableNotifications);
  disableBtn.addEventListener("click", disableNotifications);
  sendBtn.addEventListener("click", sendTest);
  markAllReadBtn.addEventListener("click", markAllRead);
  if (savePreferencesBtn) savePreferencesBtn.addEventListener("click", savePreferences);
  if (sendToUserBtn) sendToUserBtn.addEventListener("click", sendToUser);
  if (targetUserSelect) targetUserSelect.addEventListener("change", refreshTargetUserState);
  init();
})();

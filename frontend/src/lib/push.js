import { api } from "./api";

function urlBase64ToUint8Array(base64String) {
    const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
    const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
    const raw = atob(base64);
    const out = new Uint8Array(raw.length);
    for (let i = 0; i < raw.length; ++i) out[i] = raw.charCodeAt(i);
    return out;
}

export async function ensurePushSubscription() {
    if (typeof window === "undefined") return null;
    if (!("serviceWorker" in navigator) || !("PushManager" in window) || !("Notification" in window)) {
        return null;
    }
    try {
        const reg = await navigator.serviceWorker.register("/sw.js");
        await navigator.serviceWorker.ready;

        if (Notification.permission === "denied") return null;
        if (Notification.permission !== "granted") {
            const perm = await Notification.requestPermission();
            if (perm !== "granted") return null;
        }

        let sub = await reg.pushManager.getSubscription();
        if (!sub) {
            const { data } = await api.get("/push/vapid-public-key");
            const key = data.public_key;
            if (!key) return null;
            sub = await reg.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: urlBase64ToUint8Array(key),
            });
        }
        await api.post("/push/subscribe", { subscription: sub.toJSON() });
        return sub;
    } catch (e) {
        // silent: notifications not supported / blocked
        return null;
    }
}

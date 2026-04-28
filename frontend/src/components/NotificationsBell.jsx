import { useEffect, useState, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { Bell } from "lucide-react";
import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { toast } from "sonner";

function timeAgo(iso) {
    try {
        const s = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
        if (s < 60) return `${s}s`;
        if (s < 3600) return `${Math.floor(s / 60)}m`;
        if (s < 86400) return `${Math.floor(s / 3600)}h`;
        return `${Math.floor(s / 86400)}d`;
    } catch {
        return "";
    }
}

export default function NotificationsBell() {
    const { user } = useAuth();
    const [open, setOpen] = useState(false);
    const [items, setItems] = useState([]);
    const [count, setCount] = useState(0);
    const ref = useRef(null);
    const wsRef = useRef(null);
    const navigate = useNavigate();

    const fetchCount = useCallback(async () => {
        if (!user) return;
        try {
            const { data } = await api.get("/notifications/unread-count");
            setCount(data.count || 0);
        } catch {}
    }, [user]);

    const fetchItems = useCallback(async () => {
        try {
            const { data } = await api.get("/notifications");
            setItems(data);
        } catch {}
    }, []);

    // WebSocket for realtime
    useEffect(() => {
        if (!user) return;
        const token = localStorage.getItem("skiller_token");
        if (!token) return;

        const base = process.env.REACT_APP_BACKEND_URL || "";
        const wsUrl = base.replace(/^http/i, "ws") + `/api/ws?token=${encodeURIComponent(token)}`;

        let alive = true;
        let reconnectTimer = null;
        let pingTimer = null;

        const connect = () => {
            if (!alive) return;
            const ws = new WebSocket(wsUrl);
            wsRef.current = ws;
            ws.onopen = () => {
                pingTimer = setInterval(() => {
                    if (ws.readyState === WebSocket.OPEN) ws.send("ping");
                }, 25000);
            };
            ws.onmessage = (e) => {
                try {
                    const msg = JSON.parse(e.data);
                    if (msg.type === "notification" && msg.data) {
                        setItems((prev) => [msg.data, ...prev].slice(0, 50));
                        setCount((c) => c + 1);
                        toast(msg.data.message, {
                            description: msg.data.kind,
                        });
                    }
                } catch {}
            };
            ws.onclose = () => {
                clearInterval(pingTimer);
                if (alive) reconnectTimer = setTimeout(connect, 4000);
            };
            ws.onerror = () => {
                try { ws.close(); } catch {}
            };
        };
        connect();

        // Initial unread count fetch
        fetchCount();

        return () => {
            alive = false;
            clearInterval(pingTimer);
            clearTimeout(reconnectTimer);
            try { wsRef.current?.close(); } catch {}
        };
    }, [user?.id, fetchCount]); // eslint-disable-line

    useEffect(() => {
        const onClick = (e) => {
            if (ref.current && !ref.current.contains(e.target)) setOpen(false);
        };
        if (open) document.addEventListener("mousedown", onClick);
        return () => document.removeEventListener("mousedown", onClick);
    }, [open]);

    const handleOpen = async () => {
        if (!open) {
            await fetchItems();
            setOpen(true);
            await api.post("/notifications/read-all").catch(() => {});
            setCount(0);
        } else {
            setOpen(false);
        }
    };

    const onClickItem = (n) => {
        setOpen(false);
        if (n.kind === "follow" && n.actor?.username) navigate(`/u/${n.actor.username}`);
        else if (n.meta?.post_id) navigate(`/p/${n.meta.post_id}`);
    };

    if (!user) return null;

    return (
        <div className="relative" ref={ref}>
            <button
                onClick={handleOpen}
                data-testid="notifications-bell"
                aria-label="Notifications"
                className="relative grid h-10 w-10 place-items-center rounded-full hover:bg-accent"
            >
                <Bell size={18} />
                {count > 0 && (
                    <span
                        className="absolute -right-0 -top-0 grid h-5 min-w-[20px] place-items-center rounded-full bg-destructive px-1 text-[10px] font-bold text-destructive-foreground"
                        data-testid="notif-badge"
                    >
                        {count > 9 ? "9+" : count}
                    </span>
                )}
            </button>
            {open && (
                <div
                    className="absolute right-0 top-12 z-50 w-80 overflow-hidden rounded-2xl border border-border bg-popover shadow-xl"
                    data-testid="notifications-panel"
                >
                    <div className="border-b border-border px-4 py-3 font-semibold">
                        Notifications
                    </div>
                    <div className="max-h-96 overflow-auto">
                        {items.length === 0 ? (
                            <div className="px-4 py-10 text-center text-sm text-muted-foreground">
                                You're all caught up.
                            </div>
                        ) : (
                            items.map((n) => (
                                <button
                                    key={n.id}
                                    onClick={() => onClickItem(n)}
                                    className="flex w-full items-start gap-3 border-b border-border/60 px-4 py-3 text-left hover:bg-accent"
                                >
                                    <img
                                        src={
                                            n.actor?.avatar_url ||
                                            `https://api.dicebear.com/9.x/initials/svg?seed=${n.actor?.name || "S"}`
                                        }
                                        alt=""
                                        className="h-9 w-9 rounded-full border border-border object-cover"
                                    />
                                    <div className="min-w-0 flex-1">
                                        <div className="text-sm">{n.message}</div>
                                        <div className="text-xs text-muted-foreground">
                                            {timeAgo(n.created_at)} ago
                                        </div>
                                    </div>
                                    {!n.read && (
                                        <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-primary" />
                                    )}
                                </button>
                            ))
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}

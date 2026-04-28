import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Bell } from "lucide-react";
import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";

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

export default function Notifications() {
    const { user } = useAuth();
    const navigate = useNavigate();
    const [items, setItems] = useState([]);

    useEffect(() => {
        if (!user) return;
        api.get("/notifications").then((r) => setItems(r.data));
        api.post("/notifications/read-all").catch(() => {});
    }, [user?.id]);

    const onClickItem = (n) => {
        if (n.kind === "follow" && n.actor?.username) navigate(`/u/${n.actor.username}`);
        else if (n.meta?.post_id) navigate(`/p/${n.meta.post_id}`);
    };

    if (!user)
        return (
            <div className="py-20 text-center text-muted-foreground">
                Sign in to see your notifications.
            </div>
        );

    return (
        <div className="mx-auto max-w-2xl px-4 py-6" data-testid="notifications-page">
            <div className="mb-4 flex items-center gap-2">
                <Bell size={18} />
                <h1 className="font-display text-2xl font-bold tracking-tight">
                    Notifications
                </h1>
            </div>
            <div className="overflow-hidden rounded-2xl border border-border">
                {items.length === 0 ? (
                    <div className="px-4 py-12 text-center text-sm text-muted-foreground">
                        No notifications yet. Get out there.
                    </div>
                ) : (
                    items.map((n) => (
                        <button
                            key={n.id}
                            onClick={() => onClickItem(n)}
                            className="flex w-full items-start gap-3 border-b border-border/60 px-4 py-3 text-left last:border-0 hover:bg-accent"
                        >
                            <img
                                src={
                                    n.actor?.avatar_url ||
                                    `https://api.dicebear.com/9.x/initials/svg?seed=${n.actor?.name || "S"}`
                                }
                                alt=""
                                className="h-10 w-10 rounded-full border border-border object-cover"
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
    );
}

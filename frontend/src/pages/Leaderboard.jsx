import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { Trophy, Medal, Award } from "lucide-react";

export default function Leaderboard() {
    const [users, setUsers] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        api
            .get("/leaderboard?limit=30")
            .then((r) => setUsers(r.data))
            .finally(() => setLoading(false));
    }, []);

    return (
        <div className="mx-auto max-w-3xl px-4 py-6" data-testid="leaderboard-page">
            <h1 className="font-display text-2xl font-bold tracking-tight md:text-3xl">
                Leaderboard
            </h1>
            <p className="mt-1 text-sm text-muted-foreground">
                Top creators on Skiller — by XP earned through posting, learning and earning.
            </p>

            {loading ? (
                <div className="py-20 text-center text-muted-foreground">Loading…</div>
            ) : (
                <div className="mt-6 overflow-hidden rounded-2xl border border-border">
                    {users.map((u, i) => {
                        const Icon = i === 0 ? Trophy : i === 1 ? Medal : i === 2 ? Award : null;
                        const tone =
                            i === 0
                                ? "text-yellow-500"
                                : i === 1
                                  ? "text-zinc-400"
                                  : i === 2
                                    ? "text-amber-700"
                                    : "text-muted-foreground";
                        return (
                            <Link
                                to={`/u/${u.username}`}
                                key={u.id}
                                data-testid={`leaderboard-row-${u.username}`}
                                className="flex items-center gap-4 border-b border-border/60 px-4 py-3 last:border-0 hover:bg-accent"
                            >
                                <div className={`w-8 text-center font-display text-lg font-bold ${tone}`}>
                                    {Icon ? <Icon size={18} className="mx-auto" /> : i + 1}
                                </div>
                                <img
                                    src={
                                        u.avatar_url ||
                                        `https://api.dicebear.com/9.x/initials/svg?seed=${u.name}`
                                    }
                                    alt=""
                                    className="h-10 w-10 rounded-full border border-border object-cover"
                                />
                                <div className="min-w-0 flex-1">
                                    <div className="truncate text-sm font-semibold">{u.username}</div>
                                    <div className="truncate text-xs text-muted-foreground">{u.name}</div>
                                </div>
                                <div className="text-right">
                                    <div className="font-display text-sm font-bold">
                                        {u.xp.toLocaleString()} XP
                                    </div>
                                    <div className="text-xs text-muted-foreground">
                                        L{u.level.level} · {u.level.name}
                                    </div>
                                </div>
                                <div className="hidden text-xs text-muted-foreground md:block">
                                    {u.badge_count} badges
                                </div>
                            </Link>
                        );
                    })}
                </div>
            )}
        </div>
    );
}

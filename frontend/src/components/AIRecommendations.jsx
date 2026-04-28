import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Sparkles } from "lucide-react";
import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";

export default function AIRecommendations() {
    const { user } = useAuth();
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!user) {
            setLoading(false);
            return;
        }
        api
            .get("/ai/recommend")
            .then((r) => setData(r.data))
            .catch(() => setData(null))
            .finally(() => setLoading(false));
    }, [user?.id]);

    if (!user) return null;
    if (loading)
        return (
            <div className="rounded-2xl border border-border p-4">
                <div className="flex items-center gap-2 text-sm font-semibold">
                    <Sparkles size={14} className="text-primary" /> Smart Picks
                </div>
                <div className="mt-3 text-xs text-muted-foreground">Personalising…</div>
            </div>
        );
    if (!data) return null;

    return (
        <div
            className="rounded-2xl border border-border p-4"
            data-testid="ai-recommendations"
        >
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-sm font-semibold">
                    <Sparkles size={14} className="text-primary" /> Smart Picks
                </div>
                <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-bold uppercase tracking-widest text-primary">
                    AI
                </span>
            </div>

            {data.courses?.length > 0 && (
                <section className="mt-3">
                    <div className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
                        Courses
                    </div>
                    <div className="mt-1 space-y-1">
                        {data.courses.slice(0, 2).map((c) => (
                            <Link
                                key={c.id}
                                to="/courses"
                                className="block rounded-xl px-2 py-2 text-sm hover:bg-accent"
                            >
                                <div className="font-semibold">{c.title}</div>
                                <div className="line-clamp-1 text-xs text-muted-foreground">
                                    {c.why}
                                </div>
                            </Link>
                        ))}
                    </div>
                </section>
            )}

            {data.gigs?.length > 0 && (
                <section className="mt-3">
                    <div className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
                        Gigs for you
                    </div>
                    <div className="mt-1 space-y-1">
                        {data.gigs.slice(0, 2).map((g) => (
                            <Link
                                key={g.id}
                                to="/gigs"
                                className="block rounded-xl px-2 py-2 text-sm hover:bg-accent"
                            >
                                <div className="font-semibold">{g.title}</div>
                                <div className="line-clamp-1 text-xs text-muted-foreground">
                                    {g.why}
                                </div>
                            </Link>
                        ))}
                    </div>
                </section>
            )}

            {data.creators?.length > 0 && (
                <section className="mt-3">
                    <div className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
                        Follow
                    </div>
                    <div className="mt-1 space-y-1">
                        {data.creators.slice(0, 2).map((c) => (
                            <Link
                                key={c.username}
                                to={`/u/${c.username}`}
                                className="block rounded-xl px-2 py-2 text-sm hover:bg-accent"
                            >
                                <div className="font-semibold">@{c.username}</div>
                                <div className="line-clamp-1 text-xs text-muted-foreground">
                                    {c.why}
                                </div>
                            </Link>
                        ))}
                    </div>
                </section>
            )}
        </div>
    );
}

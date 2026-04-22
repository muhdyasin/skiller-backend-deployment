import { useEffect, useState } from "react";
import { api } from "../lib/api";
import PostCard from "../components/PostCard";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Feed() {
    const { user } = useAuth();
    const [posts, setPosts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [creators, setCreators] = useState([]);

    const load = async () => {
        try {
            const [feedRes, usersRes] = await Promise.all([
                api.get("/posts/feed"),
                api.get("/users?limit=8"),
            ]);
            setPosts(feedRes.data);
            setCreators(usersRes.data.filter((u) => u.username !== user?.username).slice(0, 6));
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        load();
    }, [user?.id]); // eslint-disable-line

    return (
        <div className="mx-auto grid max-w-6xl grid-cols-1 gap-10 px-4 py-6 lg:grid-cols-[1fr_280px]" data-testid="feed-page">
            <div className="mx-auto w-full max-w-xl">
                <div className="mb-6 flex items-baseline justify-between">
                    <h1 className="font-display text-2xl font-bold tracking-tight">Your feed</h1>
                    <Link to="/explore" className="text-sm text-muted-foreground hover:underline">
                        Explore more →
                    </Link>
                </div>
                {loading ? (
                    <div className="py-20 text-center text-muted-foreground">Loading feed…</div>
                ) : posts.length === 0 ? (
                    <div className="py-20 text-center text-muted-foreground">No posts yet. Be the first to share.</div>
                ) : (
                    <div className="space-y-2">
                        {posts.map((p) => (
                            <PostCard key={p.id} post={p} onUpdated={load} />
                        ))}
                    </div>
                )}
            </div>

            <aside className="hidden lg:block">
                <div className="sticky top-6 space-y-6">
                    <div>
                        <div className="mb-3 text-xs font-bold uppercase tracking-[0.2em] text-muted-foreground">
                            Creators to follow
                        </div>
                        <div className="space-y-3">
                            {creators.map((c) => (
                                <Link
                                    key={c.id}
                                    to={`/u/${c.username}`}
                                    className="flex items-center gap-3 rounded-xl p-2 hover:bg-accent"
                                >
                                    <img
                                        src={c.avatar_url || `https://api.dicebear.com/9.x/initials/svg?seed=${c.name}`}
                                        alt=""
                                        className="h-10 w-10 rounded-full border border-border object-cover"
                                    />
                                    <div className="min-w-0 flex-1">
                                        <div className="truncate text-sm font-semibold">{c.username}</div>
                                        <div className="truncate text-xs text-muted-foreground">{c.name}</div>
                                    </div>
                                </Link>
                            ))}
                        </div>
                    </div>
                    <div className="rounded-2xl border border-border p-4">
                        <div className="font-display text-lg font-bold">Get paid to learn.</div>
                        <p className="mt-1 text-sm text-muted-foreground">
                            Browse open gigs matched to your skills.
                        </p>
                        <Link
                            to="/gigs"
                            className="mt-3 inline-flex text-sm font-semibold text-primary hover:underline"
                        >
                            See gigs →
                        </Link>
                    </div>
                </div>
            </aside>
        </div>
    );
}

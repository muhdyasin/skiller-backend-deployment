import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { Heart, MessageCircle } from "lucide-react";

export default function Explore() {
    const [posts, setPosts] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        api
            .get("/posts/explore")
            .then((r) => setPosts(r.data))
            .finally(() => setLoading(false));
    }, []);

    return (
        <div className="mx-auto max-w-6xl px-4 py-6" data-testid="explore-page">
            <div className="mb-6 flex items-baseline justify-between">
                <h1 className="font-display text-2xl font-bold tracking-tight md:text-3xl">
                    Explore
                </h1>
                <div className="text-sm text-muted-foreground">{posts.length} posts</div>
            </div>

            {loading ? (
                <div className="py-20 text-center text-muted-foreground">Loading…</div>
            ) : (
                <div className="grid grid-cols-2 gap-1 md:grid-cols-3 md:gap-4">
                    {posts.map((p) => (
                        <Link
                            key={p.id}
                            to={`/u/${p.author?.username || ""}`}
                            className="group relative block aspect-square overflow-hidden rounded-none md:rounded-xl"
                            data-testid={`explore-tile-${p.id}`}
                        >
                            <img
                                src={p.media}
                                alt={p.caption}
                                className="absolute inset-0 h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
                                loading="lazy"
                            />
                            <div className="absolute inset-0 bg-black/0 transition-colors group-hover:bg-black/40" />
                            <div className="absolute inset-0 hidden items-center justify-center gap-6 text-white group-hover:flex">
                                <div className="flex items-center gap-1 font-semibold">
                                    <Heart size={18} className="fill-white" /> {p.like_count}
                                </div>
                                <div className="flex items-center gap-1 font-semibold">
                                    <MessageCircle size={18} /> {p.comment_count}
                                </div>
                            </div>
                        </Link>
                    ))}
                </div>
            )}
        </div>
    );
}

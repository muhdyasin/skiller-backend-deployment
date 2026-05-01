import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Heart, MessageCircle, Play } from "lucide-react";
import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { fileSrc } from "../lib/upload";
import StoryBar from "../components/StoryBar";

const CATEGORIES = ["All", "Design", "Code", "Product", "Reels", "Career"];

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

function VideoPoster({ src }) {
    const [thumb, setThumb] = useState(null);
    useEffect(() => {
        let cancelled = false;
        const v = document.createElement("video");
        v.crossOrigin = "anonymous";
        v.preload = "metadata";
        v.src = src;
        v.muted = true;
        v.playsInline = true;
        v.addEventListener("loadeddata", () => {
            try {
                v.currentTime = Math.min(0.5, v.duration / 4);
            } catch {}
        });
        v.addEventListener("seeked", () => {
            if (cancelled) return;
            const c = document.createElement("canvas");
            c.width = 320;
            c.height = 180;
            try {
                c.getContext("2d").drawImage(v, 0, 0, c.width, c.height);
                setThumb(c.toDataURL("image/jpeg", 0.7));
            } catch {}
        });
        return () => {
            cancelled = true;
            v.src = "";
        };
    }, [src]);
    return thumb ? (
        <img src={thumb} alt="" className="absolute inset-0 h-full w-full object-cover" />
    ) : (
        <video
            src={src}
            preload="metadata"
            muted
            playsInline
            className="absolute inset-0 h-full w-full object-cover"
        />
    );
}

export default function StudentHome() {
    const { user } = useAuth();
    const [posts, setPosts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState("All");

    useEffect(() => {
        api
            .get("/posts/feed?limit=60")
            .then((r) => setPosts(r.data))
            .finally(() => setLoading(false));
    }, [user?.id]);

    const filtered = useMemo(() => {
        if (filter === "All") return posts;
        if (filter === "Reels") return posts.filter((p) => p.media_type === "video");
        const f = filter.toLowerCase();
        return posts.filter((p) =>
            (p.tags || []).some((t) => t.toLowerCase().includes(f) || f.includes(t.toLowerCase())) ||
            (p.caption || "").toLowerCase().includes(f),
        );
    }, [posts, filter]);

    return (
        <div className="mx-auto max-w-7xl px-4 py-6" data-testid="student-home">
            <StoryBar />
            <div className="mb-5 flex flex-wrap items-center gap-2">
                {CATEGORIES.map((c) => (
                    <button
                        key={c}
                        onClick={() => setFilter(c)}
                        data-testid={`home-filter-${c}`}
                        className={`rounded-full border px-4 py-1.5 text-sm transition-colors ${
                            filter === c
                                ? "border-foreground bg-foreground text-background"
                                : "border-border hover:bg-accent"
                        }`}
                    >
                        {c}
                    </button>
                ))}
                <Link
                    to="/reels"
                    className="ml-auto inline-flex items-center gap-1 rounded-full bg-primary px-4 py-1.5 text-sm font-semibold text-primary-foreground hover:bg-primary/90"
                    data-testid="reels-link"
                >
                    <Play size={14} className="fill-current" /> Open Reels
                </Link>
            </div>

            {loading ? (
                <div className="py-20 text-center text-muted-foreground">Loading…</div>
            ) : filtered.length === 0 ? (
                <div className="py-20 text-center text-muted-foreground">
                    Nothing here yet. Try another category.
                </div>
            ) : (
                <div className="grid grid-cols-1 gap-x-4 gap-y-8 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                    {filtered.map((p) => (
                        <Link
                            key={p.id}
                            to={`/p/${p.id}`}
                            className="group block"
                            data-testid={`home-card-${p.id}`}
                        >
                            <div className="relative aspect-video overflow-hidden rounded-xl border border-border bg-secondary">
                                {p.media_type === "video" ? (
                                    <>
                                        <VideoPoster src={fileSrc(p.media)} />
                                        <span className="absolute right-2 bottom-2 grid h-7 w-7 place-items-center rounded-full bg-black/70 text-white">
                                            <Play size={12} className="fill-current" />
                                        </span>
                                    </>
                                ) : (
                                    <img
                                        src={fileSrc(p.media)}
                                        alt=""
                                        className="absolute inset-0 h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
                                        loading="lazy"
                                    />
                                )}
                            </div>
                            <div className="mt-3 flex items-start gap-3">
                                <img
                                    src={
                                        p.author?.avatar_url ||
                                        `https://api.dicebear.com/9.x/initials/svg?seed=${p.author?.name || "S"}`
                                    }
                                    alt=""
                                    className="h-9 w-9 shrink-0 rounded-full border border-border object-cover"
                                />
                                <div className="min-w-0 flex-1">
                                    <div className="line-clamp-2 text-sm font-semibold leading-snug">
                                        {p.caption || "(no caption)"}
                                    </div>
                                    <div className="mt-1 truncate text-xs text-muted-foreground">
                                        @{p.author?.username || "user"} ·{" "}
                                        <span className="inline-flex items-center gap-1">
                                            <Heart size={11} /> {p.like_count}
                                        </span>{" "}
                                        ·{" "}
                                        <span className="inline-flex items-center gap-1">
                                            <MessageCircle size={11} /> {p.comment_count}
                                        </span>{" "}
                                        · {timeAgo(p.created_at)} ago
                                    </div>
                                </div>
                            </div>
                        </Link>
                    ))}
                </div>
            )}
        </div>
    );
}

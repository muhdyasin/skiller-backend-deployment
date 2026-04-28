import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Heart, MessageCircle, Volume2, VolumeX, Play } from "lucide-react";
import { api } from "../lib/api";
import { fileSrc } from "../lib/upload";
import { useAuth } from "../context/AuthContext";
import { toast } from "sonner";

function ReelCard({ post, muted, setMuted, active, onLikeUpdated }) {
    const ref = useRef(null);
    const [liked, setLiked] = useState(post.liked);
    const [likeCount, setLikeCount] = useState(post.like_count);
    const { user } = useAuth();
    const [paused, setPaused] = useState(false);

    useEffect(() => {
        const v = ref.current;
        if (!v) return;
        if (active) {
            v.muted = muted;
            v.play().catch(() => {});
            setPaused(false);
        } else {
            v.pause();
            v.currentTime = 0;
        }
    }, [active, muted]);

    const togglePlay = () => {
        const v = ref.current;
        if (!v) return;
        if (v.paused) {
            v.play().catch(() => {});
            setPaused(false);
        } else {
            v.pause();
            setPaused(true);
        }
    };

    const toggleLike = async (e) => {
        e.stopPropagation();
        if (!user) return toast.error("Sign in to like");
        try {
            const { data } = await api.post(`/posts/${post.id}/like`);
            setLiked(data.liked);
            setLikeCount(data.like_count);
            onLikeUpdated?.();
        } catch {
            toast.error("Could not like");
        }
    };

    return (
        <div
            className="relative h-full w-full snap-start overflow-hidden bg-black"
            data-testid={`reel-${post.id}`}
        >
            <video
                ref={ref}
                src={fileSrc(post.media)}
                className="absolute inset-0 h-full w-full object-cover"
                loop
                playsInline
                onClick={togglePlay}
            />
            {paused && (
                <button
                    onClick={togglePlay}
                    className="absolute inset-0 grid place-items-center bg-black/30 text-white"
                    aria-label="play"
                >
                    <Play size={56} className="fill-current" />
                </button>
            )}

            {/* Bottom overlay */}
            <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/80 to-transparent p-5 text-white">
                <Link
                    to={`/u/${post.author?.username}`}
                    className="flex items-center gap-2"
                >
                    <img
                        src={
                            post.author?.avatar_url ||
                            `https://api.dicebear.com/9.x/initials/svg?seed=${post.author?.name || "S"}`
                        }
                        alt=""
                        className="h-9 w-9 rounded-full border border-white/30 object-cover"
                    />
                    <div className="text-sm font-semibold">@{post.author?.username || "user"}</div>
                </Link>
                {post.caption && (
                    <p className="mt-2 line-clamp-2 max-w-md text-sm leading-relaxed">
                        {post.caption}
                    </p>
                )}
                {post.tags?.length > 0 && (
                    <div className="mt-1 flex flex-wrap gap-2 text-xs text-white/70">
                        {post.tags.slice(0, 5).map((t) => (
                            <span key={t}>#{t}</span>
                        ))}
                    </div>
                )}
            </div>

            {/* Right action rail */}
            <div className="absolute right-3 bottom-24 flex flex-col items-center gap-5 text-white">
                <button
                    onClick={toggleLike}
                    data-testid={`reel-like-${post.id}`}
                    className="grid place-items-center"
                >
                    <span className="grid h-12 w-12 place-items-center rounded-full bg-white/15 backdrop-blur active:scale-90">
                        <Heart size={22} className={liked ? "fill-destructive text-destructive" : ""} />
                    </span>
                    <span className="mt-1 text-xs font-semibold">{likeCount}</span>
                </button>
                <Link to={`/p/${post.id}`} className="grid place-items-center" data-testid={`reel-comments-${post.id}`}>
                    <span className="grid h-12 w-12 place-items-center rounded-full bg-white/15 backdrop-blur">
                        <MessageCircle size={22} />
                    </span>
                    <span className="mt-1 text-xs font-semibold">{post.comment_count}</span>
                </Link>
                <button
                    onClick={() => setMuted((m) => !m)}
                    className="grid h-10 w-10 place-items-center rounded-full bg-white/15 backdrop-blur"
                    aria-label="mute"
                >
                    {muted ? <VolumeX size={18} /> : <Volume2 size={18} />}
                </button>
            </div>
        </div>
    );
}

export default function Reels() {
    const [posts, setPosts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [muted, setMuted] = useState(true);
    const [activeIdx, setActiveIdx] = useState(0);
    const containerRef = useRef(null);

    const load = async () => {
        try {
            const { data } = await api.get("/posts/reels?limit=30");
            setPosts(data);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        load();
    }, []);

    useEffect(() => {
        const c = containerRef.current;
        if (!c) return;
        const onScroll = () => {
            const idx = Math.round(c.scrollTop / c.clientHeight);
            setActiveIdx(idx);
        };
        c.addEventListener("scroll", onScroll, { passive: true });
        return () => c.removeEventListener("scroll", onScroll);
    }, [posts.length]);

    if (loading) {
        return <div className="grid h-screen place-items-center text-muted-foreground">Loading reels…</div>;
    }
    if (posts.length === 0) {
        return (
            <div className="grid h-[80vh] place-items-center text-center text-muted-foreground">
                No reels yet. Upload a vertical video to start your reels feed.
            </div>
        );
    }

    return (
        <div className="-mt-6" data-testid="reels-page">
            <div
                ref={containerRef}
                className="mx-auto h-[calc(100vh-72px)] max-w-md snap-y snap-mandatory overflow-y-auto rounded-2xl bg-black md:h-[calc(100vh-32px)]"
                style={{ scrollSnapType: "y mandatory" }}
            >
                {posts.map((p, i) => (
                    <div key={p.id} className="relative h-full w-full snap-start">
                        <ReelCard
                            post={p}
                            muted={muted}
                            setMuted={setMuted}
                            active={i === activeIdx}
                            onLikeUpdated={() => {}}
                        />
                    </div>
                ))}
            </div>
        </div>
    );
}

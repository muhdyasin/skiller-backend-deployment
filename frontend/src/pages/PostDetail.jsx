import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { Heart, Send, Bookmark } from "lucide-react";
import { Helmet } from "react-helmet-async";
import { api, formatApiError } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { toast } from "sonner";
import { fileSrc } from "../lib/upload";

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

export default function PostDetail() {
    const { postId } = useParams();
    const { user } = useAuth();
    const [post, setPost] = useState(null);
    const [comment, setComment] = useState("");

    const load = async () => {
        try {
            const { data } = await api.get(`/posts/${postId}`);
            setPost(data);
        } catch (err) {
            toast.error(formatApiError(err.response?.data?.detail));
        }
    };

    useEffect(() => {
        load();
    }, [postId]);

    const toggleLike = async () => {
        if (!user) return toast.error("Sign in to like");
        const { data } = await api.post(`/posts/${postId}/like`);
        setPost((p) => ({ ...p, liked: data.liked, like_count: data.like_count }));
    };

    const sendComment = async (e) => {
        e.preventDefault();
        if (!user) return toast.error("Sign in to comment");
        if (!comment.trim()) return;
        const { data } = await api.post(`/posts/${postId}/comments`, { text: comment.trim() });
        setPost((p) => ({ ...p, comments: [...(p.comments || []), data] }));
        setComment("");
    };

    if (!post)
        return (
            <div className="py-20 text-center text-muted-foreground">Loading post…</div>
        );

    const author = post.author || {};

    return (
        <div className="mx-auto max-w-5xl px-4 py-6" data-testid="post-detail-page">
            <Helmet>
                <title>{post.caption ? post.caption.slice(0, 60) : `Post by @${author.username || "creator"}`}</title>
                <meta name="description" content={(post.caption || `Post by @${author.username || "creator"} on Skiller`).slice(0, 160)} />
                <meta property="og:type" content={post.media_type === "video" ? "video.other" : "article"} />
                <meta property="og:title" content={post.caption ? post.caption.slice(0, 80) : `Post by @${author.username || "creator"}`} />
                <meta property="og:description" content={(post.caption || `Skiller post by @${author.username || "creator"}`).slice(0, 200)} />
                <meta property="og:image" content={fileSrc(post.media) || "https://images.unsplash.com/photo-1648111320024-3a08e28d20ff?w=1200&q=80"} />
                <meta name="twitter:card" content="summary_large_image" />
                <meta name="twitter:image" content={fileSrc(post.media) || ""} />
                {author.username && <meta name="twitter:creator" content={`@${author.username}`} />}
            </Helmet>
            <div className="grid grid-cols-1 gap-6 overflow-hidden rounded-2xl border border-border md:grid-cols-[1fr_360px]">
                <div className="bg-black">
                    {post.media_type === "video" ? (
                        <video
                            src={fileSrc(post.media)}
                            controls
                            className="aspect-square w-full object-contain"
                        />
                    ) : (
                        <img
                            src={fileSrc(post.media)}
                            alt={post.caption}
                            className="aspect-square w-full bg-black object-contain"
                        />
                    )}
                </div>
                <aside className="flex max-h-[80vh] flex-col">
                    <div className="flex items-center gap-3 border-b border-border p-4">
                        <Link to={`/u/${author.username}`} className="flex items-center gap-3">
                            <img
                                src={
                                    author.avatar_url ||
                                    `https://api.dicebear.com/9.x/initials/svg?seed=${author.name || "S"}`
                                }
                                alt=""
                                className="h-10 w-10 rounded-full border border-border object-cover"
                            />
                            <div>
                                <div className="text-sm font-semibold">{author.username}</div>
                                <div className="text-xs text-muted-foreground">{author.name}</div>
                            </div>
                        </Link>
                    </div>
                    <div className="flex-1 space-y-3 overflow-auto p-4">
                        {post.caption && (
                            <div className="text-sm">
                                <span className="font-semibold">{author.username}</span>{" "}
                                <span>{post.caption}</span>
                            </div>
                        )}
                        {(post.comments || []).map((c) => (
                            <div key={c.id} className="text-sm">
                                <span className="font-semibold">{c.username}</span>{" "}
                                <span>{c.text}</span>
                                <div className="text-xs text-muted-foreground">
                                    {timeAgo(c.created_at)} ago
                                </div>
                            </div>
                        ))}
                    </div>
                    <div className="border-t border-border p-4">
                        <div className="mb-3 flex items-center gap-4">
                            <button
                                onClick={toggleLike}
                                data-testid="post-detail-like-btn"
                                className="active:scale-90"
                            >
                                <Heart
                                    size={22}
                                    className={
                                        post.liked
                                            ? "fill-destructive text-destructive animate-pop"
                                            : ""
                                    }
                                />
                            </button>
                            <button>
                                <Send size={22} />
                            </button>
                            <button className="ml-auto">
                                <Bookmark size={22} />
                            </button>
                        </div>
                        <div className="text-sm font-semibold">
                            {post.like_count} {post.like_count === 1 ? "like" : "likes"}
                        </div>
                        <div className="text-xs text-muted-foreground">
                            {timeAgo(post.created_at)} ago
                        </div>
                        <form
                            onSubmit={sendComment}
                            className="mt-3 flex items-center gap-2 border-t border-border pt-3"
                        >
                            <input
                                value={comment}
                                onChange={(e) => setComment(e.target.value)}
                                placeholder="Add a comment…"
                                data-testid="post-detail-comment-input"
                                className="flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
                            />
                            <button
                                type="submit"
                                disabled={!comment.trim()}
                                data-testid="post-detail-comment-submit"
                                className="text-sm font-semibold text-primary disabled:opacity-40"
                            >
                                Post
                            </button>
                        </form>
                    </div>
                </aside>
            </div>
        </div>
    );
}

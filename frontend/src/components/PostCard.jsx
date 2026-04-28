import { Link, useNavigate } from "react-router-dom";
import { useState } from "react";
import { Heart, MessageCircle, Send, Bookmark } from "lucide-react";
import { api } from "../lib/api";
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

export default function PostCard({ post, onUpdated }) {
    const { user } = useAuth();
    const navigate = useNavigate();
    const [liked, setLiked] = useState(post.liked);
    const [likeCount, setLikeCount] = useState(post.like_count);
    const [comments, setComments] = useState(post.comments || []);
    const [commentText, setCommentText] = useState("");
    const [showAllComments, setShowAllComments] = useState(false);

    const toggleLike = async () => {
        if (!user) return toast.error("Sign in to like posts");
        try {
            const { data } = await api.post(`/posts/${post.id}/like`);
            setLiked(data.liked);
            setLikeCount(data.like_count);
            onUpdated?.();
        } catch {
            toast.error("Could not like post");
        }
    };

    const addComment = async (e) => {
        e.preventDefault();
        if (!user) return toast.error("Sign in to comment");
        if (!commentText.trim()) return;
        try {
            const { data } = await api.post(`/posts/${post.id}/comments`, {
                text: commentText.trim(),
            });
            setComments((c) => [...c, data]);
            setCommentText("");
        } catch {
            toast.error("Could not add comment");
        }
    };

    const author = post.author || {};
    const visibleComments = showAllComments ? comments : comments.slice(-2);

    return (
        <article
            className="border-b border-border pb-6"
            data-testid={`post-${post.id}`}
        >
            <div className="flex items-center gap-3 py-3">
                <Link to={`/u/${author.username}`} className="flex items-center gap-3">
                    <img
                        src={
                            author.avatar_url ||
                            `https://api.dicebear.com/9.x/initials/svg?seed=${encodeURIComponent(author.name || "S")}`
                        }
                        alt={author.name}
                        className="h-10 w-10 rounded-full border border-border object-cover"
                    />
                    <div>
                        <div className="flex items-center gap-2 text-sm font-semibold leading-tight">
                            {author.username}
                            {author.level && (
                                <span className="rounded-full border border-border px-1.5 text-[10px] font-bold text-muted-foreground">
                                    L{author.level.level}
                                </span>
                            )}
                        </div>
                        <div className="text-xs text-muted-foreground">
                            {author.name} · {timeAgo(post.created_at)}
                        </div>
                    </div>
                </Link>
            </div>

            {post.media ? (
                <Link to={`/p/${post.id}`}>
                    {post.media_type === "video" ? (
                        <video
                            src={fileSrc(post.media)}
                            controls
                            className="w-full rounded-2xl border border-border bg-black"
                        />
                    ) : (
                        <img
                            src={fileSrc(post.media)}
                            alt={post.caption || "post"}
                            className="aspect-[4/5] w-full rounded-2xl border border-border object-cover"
                            loading="lazy"
                        />
                    )}
                </Link>
            ) : null}

            <div className="mt-3 flex items-center gap-4 text-foreground">
                <button
                    onClick={toggleLike}
                    data-testid={`like-btn-${post.id}`}
                    aria-label="like"
                    className="transition-transform active:scale-90"
                >
                    <Heart
                        size={24}
                        className={liked ? "fill-destructive text-destructive animate-pop" : ""}
                    />
                </button>
                <button
                    onClick={() => navigate(`/p/${post.id}`)}
                    aria-label="comment"
                    className="active:scale-90"
                    data-testid={`comment-btn-${post.id}`}
                >
                    <MessageCircle size={24} />
                </button>
                <button aria-label="share" className="active:scale-90">
                    <Send size={24} />
                </button>
                <button aria-label="bookmark" className="ml-auto active:scale-90">
                    <Bookmark size={24} />
                </button>
            </div>

            <div
                className="mt-2 text-sm font-semibold"
                data-testid={`like-count-${post.id}`}
            >
                {likeCount} {likeCount === 1 ? "like" : "likes"}
            </div>
            {post.caption && (
                <p className="mt-1 text-sm leading-relaxed">
                    <Link
                        to={`/u/${author.username}`}
                        className="font-semibold hover:underline"
                    >
                        {author.username}
                    </Link>{" "}
                    {post.caption}
                </p>
            )}
            {post.tags?.length > 0 && (
                <div className="mt-1 flex flex-wrap gap-1 text-sm text-primary">
                    {post.tags.map((t) => (
                        <span key={t}>#{t}</span>
                    ))}
                </div>
            )}

            {comments.length > 2 && !showAllComments && (
                <button
                    onClick={() => setShowAllComments(true)}
                    className="mt-2 text-sm text-muted-foreground hover:underline"
                >
                    View all {comments.length} comments
                </button>
            )}
            <div className="mt-2 space-y-1">
                {visibleComments.map((c) => (
                    <div key={c.id} className="text-sm">
                        <span className="font-semibold">{c.username}</span>{" "}
                        <span>{c.text}</span>
                    </div>
                ))}
            </div>

            <form
                onSubmit={addComment}
                className="mt-3 flex items-center gap-2 border-t border-border pt-3"
            >
                <input
                    type="text"
                    value={commentText}
                    onChange={(e) => setCommentText(e.target.value)}
                    placeholder="Add a comment…"
                    data-testid={`comment-input-${post.id}`}
                    className="flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
                />
                <button
                    type="submit"
                    disabled={!commentText.trim()}
                    data-testid={`comment-submit-${post.id}`}
                    className="text-sm font-semibold text-primary disabled:opacity-40"
                >
                    Post
                </button>
            </form>
        </article>
    );
}

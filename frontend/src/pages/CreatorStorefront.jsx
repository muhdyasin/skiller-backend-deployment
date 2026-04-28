import { useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { api, formatApiError } from "../lib/api";
import { fileSrc } from "../lib/upload";
import { useAuth } from "../context/AuthContext";
import { Button } from "../components/ui/button";
import { toast } from "sonner";
import {
    BookOpen,
    Briefcase,
    Film,
    Grid3x3,
    Share2,
    ArrowLeft,
} from "lucide-react";

export default function CreatorStorefront() {
    const { username } = useParams();
    const { user: currentUser } = useAuth();
    const navigate = useNavigate();
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [tab, setTab] = useState("courses");

    useEffect(() => {
        let cancel = false;
        (async () => {
            try {
                setLoading(true);
                const res = await api.get(`/c/${username}`);
                if (!cancel) setData(res.data);
            } catch (err) {
                if (!cancel) {
                    setData(null);
                    if (err.response?.status === 404) {
                        toast.error("Creator not found");
                    } else {
                        toast.error(formatApiError(err.response?.data?.detail));
                    }
                }
            } finally {
                if (!cancel) setLoading(false);
            }
        })();
        return () => {
            cancel = true;
        };
    }, [username]);

    useEffect(() => {
        if (!data?.user?.name) return;
        const prev = document.title;
        document.title = `${data.user.name} (@${data.user.username}) — Skiller`;
        return () => {
            document.title = prev;
        };
    }, [data]);

    const follow = async () => {
        if (!currentUser) {
            toast.error("Sign in to follow");
            navigate("/login");
            return;
        }
        try {
            await api.post(`/users/${data.user.id}/follow`);
            const res = await api.get(`/c/${username}`);
            setData(res.data);
        } catch {
            toast.error("Could not update follow");
        }
    };

    const share = async () => {
        const url = window.location.href;
        try {
            if (navigator.share) {
                await navigator.share({
                    title: `${data.user.name} on Skiller`,
                    text: data.user.bio || `Check out @${data.user.username} on Skiller`,
                    url,
                });
            } else {
                await navigator.clipboard.writeText(url);
                toast.success("Link copied to clipboard");
            }
        } catch {
            // user cancelled — ignore
        }
    };

    if (loading)
        return (
            <div className="py-20 text-center text-muted-foreground" data-testid="storefront-loading">
                Loading creator…
            </div>
        );
    if (!data)
        return (
            <div className="py-20 text-center text-muted-foreground" data-testid="storefront-not-found">
                Creator not found.{" "}
                <Link to="/explore" className="text-primary underline">
                    Browse creators
                </Link>
            </div>
        );

    const { user, stats, level, badges, courses, gigs, reels, posts, is_following, is_self } = data;

    const tabs = [
        { key: "courses", label: "Courses", icon: BookOpen, count: courses.length },
        { key: "gigs", label: "Gigs", icon: Briefcase, count: gigs.length },
        { key: "reels", label: "Reels", icon: Film, count: reels.length },
        { key: "posts", label: "Posts", icon: Grid3x3, count: posts.length },
    ];

    return (
        <div className="mx-auto max-w-5xl px-4 py-6" data-testid="creator-storefront">
            {/* Hero */}
            <div className="overflow-hidden rounded-3xl border border-border bg-gradient-to-br from-primary/10 via-background to-background">
                <div className="flex flex-col gap-6 p-6 md:flex-row md:items-center md:p-10">
                    <img
                        src={
                            user.avatar_url ||
                            `https://api.dicebear.com/9.x/initials/svg?seed=${user.name}`
                        }
                        alt=""
                        className="h-24 w-24 shrink-0 rounded-2xl border border-border object-cover md:h-32 md:w-32"
                        data-testid="storefront-avatar"
                    />
                    <div className="flex-1">
                        <div className="text-xs font-bold uppercase tracking-widest text-primary">
                            Creator on Skiller
                        </div>
                        <h1
                            className="font-display text-3xl font-extrabold leading-tight md:text-4xl"
                            data-testid="storefront-name"
                        >
                            {user.name}
                        </h1>
                        <div className="mt-1 text-sm text-muted-foreground" data-testid="storefront-username">
                            @{user.username}
                        </div>
                        {user.bio && (
                            <p className="mt-3 max-w-2xl text-sm leading-relaxed text-foreground/90">
                                {user.bio}
                            </p>
                        )}
                        <div className="mt-4 flex flex-wrap items-center gap-3 text-sm">
                            <Stat label="followers" value={stats.followers} />
                            <Stat label="courses" value={stats.courses} />
                            <Stat label="gigs" value={stats.gigs} />
                            {level && (
                                <span className="inline-flex items-center gap-1 rounded-full border border-border bg-background px-3 py-1 text-xs font-bold">
                                    L{level.level} · {level.name}
                                </span>
                            )}
                        </div>
                        <div className="mt-5 flex flex-wrap items-center gap-2">
                            {!is_self && (
                                <Button
                                    onClick={follow}
                                    variant={is_following ? "outline" : "default"}
                                    className="rounded-full"
                                    data-testid="storefront-follow-btn"
                                >
                                    {is_following ? "Following" : "Follow"}
                                </Button>
                            )}
                            <Button
                                variant="outline"
                                onClick={share}
                                className="rounded-full"
                                data-testid="storefront-share-btn"
                            >
                                <Share2 size={14} className="mr-1.5" /> Share
                            </Button>
                            <Link
                                to={`/u/${user.username}`}
                                className="rounded-full border border-border bg-background px-4 py-2 text-sm font-medium hover:bg-accent"
                                data-testid="storefront-profile-link"
                            >
                                Social profile →
                            </Link>
                        </div>
                        {badges?.length > 0 && (
                            <div className="mt-4 flex flex-wrap gap-1.5" data-testid="storefront-badges">
                                {badges.slice(0, 6).map((b) => (
                                    <span
                                        key={b.key}
                                        title={b.desc}
                                        className="inline-flex items-center gap-1 rounded-full bg-secondary px-2.5 py-1 text-[11px] font-medium"
                                    >
                                        <span>{b.icon}</span> {b.title}
                                    </span>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* Tabs */}
            <div className="sticky top-0 z-10 mt-6 flex gap-1 overflow-x-auto rounded-full border border-border bg-background/90 p-1 backdrop-blur">
                {tabs.map(({ key, label, icon: Icon, count }) => (
                    <button
                        key={key}
                        onClick={() => setTab(key)}
                        data-testid={`storefront-tab-${key}`}
                        className={`flex shrink-0 items-center gap-1.5 rounded-full px-4 py-2 text-sm font-semibold transition-colors ${
                            tab === key
                                ? "bg-primary text-primary-foreground"
                                : "text-foreground hover:bg-accent"
                        }`}
                    >
                        <Icon size={14} />
                        {label}
                        <span className="rounded-full bg-background/30 px-1.5 text-[10px] font-bold">
                            {count}
                        </span>
                    </button>
                ))}
            </div>

            {/* Panels */}
            <div className="mt-6">
                {tab === "courses" && <CoursesGrid items={courses} />}
                {tab === "gigs" && <GigsList items={gigs} />}
                {tab === "reels" && <ReelsGrid items={reels} />}
                {tab === "posts" && <PostsGrid items={posts} />}
            </div>

            <div className="mt-12 flex justify-center">
                <Link
                    to="/explore"
                    className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
                >
                    <ArrowLeft size={14} /> Discover more creators
                </Link>
            </div>
        </div>
    );
}

function Stat({ label, value }) {
    return (
        <span className="inline-flex items-baseline gap-1" data-testid={`storefront-stat-${label}`}>
            <span className="font-bold">{value}</span>
            <span className="text-xs text-muted-foreground">{label}</span>
        </span>
    );
}

function Empty({ msg }) {
    return (
        <div className="rounded-2xl border border-dashed border-border py-16 text-center text-sm text-muted-foreground">
            {msg}
        </div>
    );
}

function CoursesGrid({ items }) {
    if (items.length === 0) return <Empty msg="No courses yet from this creator." />;
    return (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3" data-testid="storefront-courses">
            {items.map((c) => (
                <Link
                    key={c.id}
                    to="/courses"
                    className="group overflow-hidden rounded-2xl border border-border bg-card transition-shadow hover:shadow-lg"
                    data-testid={`storefront-course-${c.id}`}
                >
                    <div className="aspect-video overflow-hidden bg-secondary">
                        <img
                            src={fileSrc(c.thumbnail)}
                            alt=""
                            className="h-full w-full object-cover transition-transform group-hover:scale-105"
                            loading="lazy"
                        />
                    </div>
                    <div className="p-4">
                        <div className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
                            {c.category}
                        </div>
                        <div className="mt-1 line-clamp-2 font-display text-base font-bold">
                            {c.title}
                        </div>
                        <div className="mt-2 flex items-center justify-between text-xs">
                            <span className="text-muted-foreground">{c.lessons} lessons</span>
                            <span className="font-bold text-primary">
                                ₹{(c.price || 0).toLocaleString("en-IN")}
                            </span>
                        </div>
                        {c.enrollments > 0 && (
                            <div className="mt-2 text-[11px] text-muted-foreground">
                                {c.enrollments} enrolled
                            </div>
                        )}
                    </div>
                </Link>
            ))}
        </div>
    );
}

function GigsList({ items }) {
    if (items.length === 0) return <Empty msg="No open gigs right now." />;
    return (
        <div className="space-y-3" data-testid="storefront-gigs">
            {items.map((g) => (
                <Link
                    key={g.id}
                    to="/gigs"
                    className="block rounded-2xl border border-border bg-card p-5 transition-colors hover:bg-accent/40"
                    data-testid={`storefront-gig-${g.id}`}
                >
                    <div className="flex flex-wrap items-start justify-between gap-3">
                        <div className="min-w-0 flex-1">
                            <div className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
                                {g.category} · {g.location}
                            </div>
                            <div className="mt-1 font-display text-lg font-bold">{g.title}</div>
                            <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">
                                {g.description}
                            </p>
                            {g.skills?.length > 0 && (
                                <div className="mt-2 flex flex-wrap gap-1">
                                    {g.skills.slice(0, 5).map((s) => (
                                        <span
                                            key={s}
                                            className="rounded-full bg-secondary px-2 py-0.5 text-[10px] font-medium"
                                        >
                                            {s}
                                        </span>
                                    ))}
                                </div>
                            )}
                        </div>
                        <div className="text-right">
                            <div className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
                                Budget
                            </div>
                            <div className="font-display text-xl font-extrabold text-primary">
                                ₹{(g.budget || 0).toLocaleString("en-IN")}
                            </div>
                        </div>
                    </div>
                </Link>
            ))}
        </div>
    );
}

function ReelsGrid({ items }) {
    if (items.length === 0) return <Empty msg="No reels yet." />;
    return (
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:gap-3" data-testid="storefront-reels">
            {items.map((r) => (
                <Link
                    key={r.id}
                    to={`/p/${r.id}`}
                    className="relative aspect-[9/16] overflow-hidden rounded-xl border border-border bg-black"
                    data-testid={`storefront-reel-${r.id}`}
                >
                    <video
                        src={fileSrc(r.media)}
                        className="h-full w-full object-cover"
                        muted
                        playsInline
                        preload="metadata"
                    />
                    <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/80 to-transparent p-2 text-xs text-white">
                        <div className="line-clamp-2">{r.caption || "(no caption)"}</div>
                    </div>
                </Link>
            ))}
        </div>
    );
}

function PostsGrid({ items }) {
    if (items.length === 0) return <Empty msg="No posts yet." />;
    return (
        <div className="grid grid-cols-3 gap-1 md:gap-3" data-testid="storefront-posts">
            {items.map((p) => (
                <Link
                    key={p.id}
                    to={`/p/${p.id}`}
                    className="aspect-square overflow-hidden rounded-none md:rounded-xl"
                    data-testid={`storefront-post-${p.id}`}
                >
                    <img
                        src={fileSrc(p.media)}
                        alt=""
                        className="h-full w-full object-cover transition-transform hover:scale-105"
                        loading="lazy"
                    />
                </Link>
            ))}
        </div>
    );
}

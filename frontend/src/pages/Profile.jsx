import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api, formatApiError } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { Button } from "../components/ui/button";
import { toast } from "sonner";
import { Grid3x3, Settings } from "lucide-react";

export default function Profile() {
    const { username } = useParams();
    const { user: currentUser, refresh } = useAuth();
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [editing, setEditing] = useState(false);
    const [form, setForm] = useState({ name: "", bio: "", avatar_url: "" });

    const load = async () => {
        try {
            setLoading(true);
            const res = await api.get(`/users/${username}`);
            setData(res.data);
            setForm({
                name: res.data.user.name || "",
                bio: res.data.user.bio || "",
                avatar_url: res.data.user.avatar_url || "",
            });
        } catch (err) {
            toast.error(formatApiError(err.response?.data?.detail));
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        load();
    }, [username]);

    const follow = async () => {
        if (!currentUser) return toast.error("Sign in to follow");
        try {
            await api.post(`/users/${data.user.id}/follow`);
            load();
        } catch {
            toast.error("Could not update follow");
        }
    };

    const saveProfile = async (e) => {
        e.preventDefault();
        try {
            await api.patch("/users/me", form);
            toast.success("Profile saved");
            setEditing(false);
            await refresh();
            load();
        } catch (err) {
            toast.error(formatApiError(err.response?.data?.detail));
        }
    };

    if (loading)
        return <div className="py-20 text-center text-muted-foreground">Loading profile…</div>;
    if (!data)
        return <div className="py-20 text-center text-muted-foreground">User not found.</div>;

    const { user, posts, post_count, follower_count, following_count, is_following, is_self, level, badges } = data;

    return (
        <div className="mx-auto max-w-4xl px-4 py-6" data-testid="profile-page">
            <header className="flex flex-col gap-6 border-b border-border pb-8 md:flex-row md:items-center">
                <img
                    src={user.avatar_url || `https://api.dicebear.com/9.x/initials/svg?seed=${user.name}`}
                    alt=""
                    className="h-24 w-24 rounded-full border border-border object-cover md:h-32 md:w-32"
                />
                <div className="flex-1">
                    <div className="flex flex-wrap items-center gap-3">
                        <h1 className="font-display text-2xl font-bold">{user.username}</h1>
                        {is_self ? (
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={() => setEditing((e) => !e)}
                                className="rounded-full"
                                data-testid="edit-profile-btn"
                            >
                                <Settings size={14} className="mr-1" /> Edit profile
                            </Button>
                        ) : (
                            <Button
                                onClick={follow}
                                size="sm"
                                variant={is_following ? "outline" : "default"}
                                className="rounded-full"
                                data-testid="follow-btn"
                            >
                                {is_following ? "Following" : "Follow"}
                            </Button>
                        )}
                        {is_self && currentUser?.role === "student" && (
                            <Button
                                size="sm"
                                onClick={async () => {
                                    try {
                                        await api.post("/users/me/upgrade-role", { role: "creator" });
                                        toast.success("You're a creator now!");
                                        await refresh();
                                        load();
                                    } catch {
                                        toast.error("Could not upgrade");
                                    }
                                }}
                                className="rounded-full"
                                data-testid="upgrade-creator-btn"
                            >
                                Become a creator
                            </Button>
                        )}
                        {(user.role === "creator" || user.role === "admin") && (
                            <Link
                                to={`/c/${user.username}`}
                                className="rounded-full border border-border bg-background px-3 py-1.5 text-xs font-semibold hover:bg-accent"
                                data-testid="view-storefront-link"
                            >
                                View storefront →
                            </Link>
                        )}
                    </div>
                    <div className="mt-4 flex items-center gap-6 text-sm">
                        <div>
                            <span className="font-bold">{post_count}</span>{" "}
                            <span className="text-muted-foreground">posts</span>
                        </div>
                        <div data-testid="follower-count">
                            <span className="font-bold">{follower_count}</span>{" "}
                            <span className="text-muted-foreground">followers</span>
                        </div>
                        <div>
                            <span className="font-bold">{following_count}</span>{" "}
                            <span className="text-muted-foreground">following</span>
                        </div>
                    </div>
                    <div className="mt-3 text-sm font-semibold">{user.name}</div>
                    <p className="mt-1 max-w-xl text-sm text-muted-foreground">{user.bio || "No bio yet."}</p>
                    {level && (
                        <div className="mt-3 inline-flex items-center gap-2 rounded-full border border-border px-3 py-1 text-xs">
                            <span className="font-bold">L{level.level} · {level.name}</span>
                            <span className="text-muted-foreground">{level.xp} XP</span>
                            {user.streak > 0 && (
                                <span className="ml-1 rounded-full bg-orange-500/10 px-2 py-0.5 font-semibold text-orange-500">
                                    🔥 {user.streak}d streak
                                </span>
                            )}
                        </div>
                    )}
                    {badges?.length > 0 && (
                        <div className="mt-3 flex flex-wrap gap-2" data-testid="profile-badges">
                            {badges.map((b) => (
                                <span
                                    key={b.key}
                                    title={b.desc}
                                    className="inline-flex items-center gap-1.5 rounded-full bg-secondary px-3 py-1 text-xs font-medium"
                                >
                                    <span>{b.icon}</span> {b.title}
                                </span>
                            ))}
                        </div>
                    )}
                </div>
            </header>

            {editing && (
                <form
                    onSubmit={saveProfile}
                    className="mt-6 space-y-3 rounded-2xl border border-border p-4"
                    data-testid="edit-profile-form"
                >
                    <div>
                        <label className="text-sm font-medium">Name</label>
                        <input
                            className="mt-1 w-full rounded-xl border border-input bg-background px-3 py-2 text-sm"
                            value={form.name}
                            onChange={(e) => setForm({ ...form, name: e.target.value })}
                        />
                    </div>
                    <div>
                        <label className="text-sm font-medium">Bio</label>
                        <textarea
                            className="mt-1 w-full rounded-xl border border-input bg-background px-3 py-2 text-sm"
                            rows={3}
                            value={form.bio}
                            onChange={(e) => setForm({ ...form, bio: e.target.value })}
                        />
                    </div>
                    <div>
                        <label className="text-sm font-medium">Avatar URL</label>
                        <input
                            className="mt-1 w-full rounded-xl border border-input bg-background px-3 py-2 text-sm"
                            value={form.avatar_url}
                            onChange={(e) => setForm({ ...form, avatar_url: e.target.value })}
                            placeholder="https://…"
                        />
                    </div>
                    <div className="flex justify-end gap-2">
                        <Button type="button" variant="ghost" onClick={() => setEditing(false)} className="rounded-full">
                            Cancel
                        </Button>
                        <Button type="submit" className="rounded-full" data-testid="save-profile-btn">
                            Save
                        </Button>
                    </div>
                </form>
            )}

            <div className="mt-6">
                <div className="mb-4 flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-muted-foreground">
                    <Grid3x3 size={14} /> Posts
                </div>
                {posts.length === 0 ? (
                    <div className="py-12 text-center text-muted-foreground">No posts yet.</div>
                ) : (
                    <div className="grid grid-cols-3 gap-1 md:gap-3">
                        {posts.map((p) => (
                            <Link
                                key={p.id}
                                to={`/p/${p.id}`}
                                className="aspect-square overflow-hidden rounded-none md:rounded-xl"
                            >
                                <img
                                    src={p.media}
                                    alt=""
                                    className="h-full w-full object-cover transition-transform hover:scale-105"
                                    loading="lazy"
                                />
                            </Link>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}

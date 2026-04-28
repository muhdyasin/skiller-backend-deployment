import { useEffect, useState, useRef } from "react";
import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import {
    Tabs,
    TabsList,
    TabsTrigger,
    TabsContent,
} from "../components/ui/tabs";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogFooter,
    DialogDescription,
} from "../components/ui/dialog";
import {
    BarChart3,
    Heart,
    MessageCircle,
    Users,
    BookOpen,
    Megaphone,
    Trash2,
    Pause,
    Play,
    Plus,
    ImagePlus,
    TrendingUp,
} from "lucide-react";
import { toast } from "sonner";
import { uploadFile, fileSrc } from "../lib/upload";
import { Link } from "react-router-dom";

function Stat({ label, value, icon: Icon }) {
    return (
        <div className="rounded-2xl border border-border p-4">
            <div className="flex items-center justify-between">
                <div className="text-xs uppercase tracking-widest text-muted-foreground">
                    {label}
                </div>
                {Icon && <Icon size={14} className="text-muted-foreground" />}
            </div>
            <div className="mt-1 font-display text-2xl font-bold">{value}</div>
        </div>
    );
}

export default function Dashboard() {
    const { user } = useAuth();
    const [stats, setStats] = useState(null);
    const [posts, setPosts] = useState([]);
    const [courses, setCourses] = useState([]);
    const [ads, setAds] = useState([]);

    const [courseOpen, setCourseOpen] = useState(false);
    const [adOpen, setAdOpen] = useState(false);

    const loadAll = async () => {
        const [s, p, c, a] = await Promise.all([
            api.get("/dashboard/stats"),
            api.get("/dashboard/posts"),
            api.get("/dashboard/courses"),
            api.get("/ads/mine"),
        ]);
        setStats(s.data);
        setPosts(p.data);
        setCourses(c.data);
        setAds(a.data);
    };

    useEffect(() => {
        loadAll().catch(() => {});
    }, [user?.id]);

    const deletePost = async (id) => {
        if (!window.confirm("Delete this post?")) return;
        try {
            await api.delete(`/posts/${id}`);
            toast.success("Post deleted");
            loadAll();
        } catch {
            toast.error("Could not delete");
        }
    };

    const deleteCourse = async (id) => {
        if (!window.confirm("Delete this course?")) return;
        try {
            await api.delete(`/courses/${id}`);
            toast.success("Course deleted");
            loadAll();
        } catch {
            toast.error("Could not delete");
        }
    };

    const toggleAd = async (ad) => {
        const next = ad.status === "active" ? "paused" : "active";
        try {
            await api.patch(`/ads/${ad.id}/status`, { status: next });
            loadAll();
        } catch {
            toast.error("Could not update");
        }
    };

    const deleteAd = async (id) => {
        if (!window.confirm("Delete this ad?")) return;
        try {
            await api.delete(`/ads/${id}`);
            toast.success("Ad deleted");
            loadAll();
        } catch {
            toast.error("Could not delete");
        }
    };

    return (
        <div className="mx-auto max-w-6xl px-4 py-6" data-testid="dashboard-page">
            <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
                <div>
                    <h1 className="font-display text-3xl font-bold tracking-tight">
                        Creator Dashboard
                    </h1>
                    <p className="mt-1 text-sm text-muted-foreground">
                        Manage your content, courses and ad campaigns from one place.
                    </p>
                </div>
                <div className="flex gap-2">
                    <Button
                        onClick={() => setCourseOpen(true)}
                        variant="outline"
                        className="rounded-full"
                        data-testid="new-course-btn"
                    >
                        <Plus size={14} className="mr-1" /> New course
                    </Button>
                    <Button
                        onClick={() => setAdOpen(true)}
                        className="rounded-full"
                        data-testid="new-ad-btn"
                    >
                        <Megaphone size={14} className="mr-1" /> Run an ad
                    </Button>
                </div>
            </div>

            {stats && (
                <div className="mb-6 grid grid-cols-2 gap-3 md:grid-cols-4">
                    <Stat label="Posts" value={stats.posts} icon={BarChart3} />
                    <Stat label="Likes" value={stats.likes} icon={Heart} />
                    <Stat label="Comments" value={stats.comments} icon={MessageCircle} />
                    <Stat label="Followers" value={stats.followers} icon={Users} />
                    <Stat label="Courses" value={stats.courses} icon={BookOpen} />
                    <Stat label="Enrollments" value={stats.enrollments} icon={TrendingUp} />
                    <Stat label="XP" value={`${stats.xp} (L${stats.level.level})`} />
                    <Stat label="Active ads" value={stats.active_ads} icon={Megaphone} />
                </div>
            )}

            <Tabs defaultValue="overview" className="w-full">
                <TabsList
                    className="w-full justify-start overflow-x-auto rounded-full bg-secondary p-1"
                    data-testid="dashboard-tabs"
                >
                    <TabsTrigger value="overview" className="rounded-full">
                        Overview
                    </TabsTrigger>
                    <TabsTrigger value="posts" className="rounded-full">
                        Posts
                    </TabsTrigger>
                    <TabsTrigger value="courses" className="rounded-full">
                        Courses
                    </TabsTrigger>
                    <TabsTrigger value="ads" className="rounded-full">
                        Ads
                    </TabsTrigger>
                </TabsList>

                <TabsContent value="overview" className="mt-6">
                    {stats && (
                        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                            <div className="rounded-2xl border border-border p-5">
                                <div className="text-xs uppercase tracking-widest text-muted-foreground">
                                    Ad performance
                                </div>
                                <div className="mt-3 grid grid-cols-3 gap-3">
                                    <div>
                                        <div className="text-xs text-muted-foreground">Impr.</div>
                                        <div className="font-display text-xl font-bold">
                                            {stats.ad_impressions.toLocaleString()}
                                        </div>
                                    </div>
                                    <div>
                                        <div className="text-xs text-muted-foreground">Clicks</div>
                                        <div className="font-display text-xl font-bold">
                                            {stats.ad_clicks.toLocaleString()}
                                        </div>
                                    </div>
                                    <div>
                                        <div className="text-xs text-muted-foreground">CTR</div>
                                        <div className="font-display text-xl font-bold">
                                            {stats.ad_ctr}%
                                        </div>
                                    </div>
                                </div>
                                <div className="mt-3 text-xs text-muted-foreground">
                                    Spend: ₹{stats.ad_spend.toLocaleString("en-IN")}
                                </div>
                            </div>
                            <div className="rounded-2xl border border-border p-5">
                                <div className="text-xs uppercase tracking-widest text-muted-foreground">
                                    Quick actions
                                </div>
                                <div className="mt-3 grid grid-cols-2 gap-2">
                                    <Link
                                        to="/upload"
                                        className="rounded-xl border border-border px-3 py-2 text-sm hover:bg-accent"
                                    >
                                        + New post
                                    </Link>
                                    <button
                                        onClick={() => setCourseOpen(true)}
                                        className="rounded-xl border border-border px-3 py-2 text-left text-sm hover:bg-accent"
                                    >
                                        + New course
                                    </button>
                                    <button
                                        onClick={() => setAdOpen(true)}
                                        className="rounded-xl border border-border px-3 py-2 text-left text-sm hover:bg-accent"
                                    >
                                        + Run an ad
                                    </button>
                                    <Link
                                        to="/leaderboard"
                                        className="rounded-xl border border-border px-3 py-2 text-sm hover:bg-accent"
                                    >
                                        View leaderboard
                                    </Link>
                                </div>
                            </div>
                        </div>
                    )}
                </TabsContent>

                <TabsContent value="posts" className="mt-6">
                    {posts.length === 0 ? (
                        <div className="py-12 text-center text-sm text-muted-foreground">
                            You haven't posted yet. Head to{" "}
                            <Link to="/upload" className="text-primary underline">
                                Upload
                            </Link>
                            .
                        </div>
                    ) : (
                        <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-4">
                            {posts.map((p) => (
                                <div key={p.id} className="overflow-hidden rounded-2xl border border-border">
                                    <Link to={`/p/${p.id}`} className="block aspect-square">
                                        <img
                                            src={fileSrc(p.media)}
                                            alt=""
                                            className="h-full w-full object-cover"
                                        />
                                    </Link>
                                    <div className="flex items-center justify-between p-2 text-xs">
                                        <div className="flex items-center gap-3 text-muted-foreground">
                                            <span className="flex items-center gap-1">
                                                <Heart size={12} /> {(p.likes || []).length}
                                            </span>
                                            <span className="flex items-center gap-1">
                                                <MessageCircle size={12} /> {(p.comments || []).length}
                                            </span>
                                        </div>
                                        <button
                                            onClick={() => deletePost(p.id)}
                                            data-testid={`delete-post-${p.id}`}
                                            className="text-muted-foreground hover:text-destructive"
                                        >
                                            <Trash2 size={14} />
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </TabsContent>

                <TabsContent value="courses" className="mt-6">
                    {courses.length === 0 ? (
                        <div className="py-12 text-center text-sm text-muted-foreground">
                            No courses yet. Click "New course" to publish your first one.
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
                            {courses.map((c) => (
                                <div key={c.id} className="overflow-hidden rounded-2xl border border-border">
                                    <img
                                        src={fileSrc(c.thumbnail)}
                                        alt=""
                                        className="aspect-video w-full object-cover"
                                    />
                                    <div className="p-4">
                                        <div className="text-xs text-muted-foreground">{c.category}</div>
                                        <div className="font-display text-base font-bold">{c.title}</div>
                                        <div className="mt-2 flex items-center justify-between">
                                            <div className="text-sm">
                                                ₹{(c.price || 0).toLocaleString("en-IN")} ·{" "}
                                                {c.lessons} lessons
                                            </div>
                                            <button
                                                onClick={() => deleteCourse(c.id)}
                                                className="text-muted-foreground hover:text-destructive"
                                                data-testid={`delete-course-${c.id}`}
                                            >
                                                <Trash2 size={14} />
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </TabsContent>

                <TabsContent value="ads" className="mt-6">
                    {ads.length === 0 ? (
                        <div className="py-12 text-center text-sm text-muted-foreground">
                            No ad campaigns yet. Click "Run an ad" to launch one.
                        </div>
                    ) : (
                        <div className="space-y-3">
                            {ads.map((a) => (
                                <div
                                    key={a.id}
                                    className="flex flex-col gap-4 rounded-2xl border border-border p-4 md:flex-row md:items-center"
                                    data-testid={`my-ad-${a.id}`}
                                >
                                    {a.media && (
                                        <img
                                            src={fileSrc(a.media)}
                                            alt=""
                                            className="h-20 w-20 rounded-xl object-cover"
                                        />
                                    )}
                                    <div className="flex-1">
                                        <div className="flex flex-wrap items-center gap-2">
                                            <span className="font-display text-base font-bold">
                                                {a.title}
                                            </span>
                                            <span
                                                className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase ${
                                                    a.status === "active"
                                                        ? "bg-primary/10 text-primary"
                                                        : "bg-secondary text-muted-foreground"
                                                }`}
                                            >
                                                {a.status}
                                            </span>
                                        </div>
                                        <div className="mt-1 text-xs text-muted-foreground">
                                            ₹{a.daily_budget}/day · {a.duration_days} days
                                        </div>
                                        <div className="mt-2 flex flex-wrap gap-3 text-xs">
                                            <span>Impr <b>{a.impressions}</b></span>
                                            <span>Clicks <b>{a.clicks}</b></span>
                                            <span>
                                                CTR <b>
                                                    {a.impressions
                                                        ? ((a.clicks / a.impressions) * 100).toFixed(1)
                                                        : 0}
                                                    %
                                                </b>
                                            </span>
                                            <span>Spend <b>₹{a.spend}</b></span>
                                        </div>
                                    </div>
                                    <div className="flex gap-2">
                                        <Button
                                            size="sm"
                                            variant="outline"
                                            onClick={() => toggleAd(a)}
                                            className="rounded-full"
                                            data-testid={`toggle-ad-${a.id}`}
                                        >
                                            {a.status === "active" ? (
                                                <>
                                                    <Pause size={12} className="mr-1" /> Pause
                                                </>
                                            ) : (
                                                <>
                                                    <Play size={12} className="mr-1" /> Resume
                                                </>
                                            )}
                                        </Button>
                                        <Button
                                            size="sm"
                                            variant="ghost"
                                            onClick={() => deleteAd(a.id)}
                                            className="rounded-full text-destructive hover:text-destructive"
                                        >
                                            <Trash2 size={12} />
                                        </Button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </TabsContent>
            </Tabs>

            <NewCourseDialog open={courseOpen} setOpen={setCourseOpen} onCreated={loadAll} />
            <NewAdDialog open={adOpen} setOpen={setAdOpen} onCreated={loadAll} />
        </div>
    );
}

function NewCourseDialog({ open, setOpen, onCreated }) {
    const [form, setForm] = useState({
        title: "",
        description: "",
        price: 999,
        lessons: 5,
        category: "Development",
    });
    const [thumbnail, setThumbnail] = useState("");
    const [submitting, setSubmitting] = useState(false);
    const fileRef = useRef(null);

    const upload = async (f) => {
        if (!f) return;
        try {
            const r = await uploadFile(f);
            setThumbnail(r.url);
            toast.success("Thumbnail uploaded");
        } catch {
            toast.error("Upload failed");
        }
    };

    const submit = async (e) => {
        e.preventDefault();
        setSubmitting(true);
        try {
            await api.post("/courses", { ...form, thumbnail });
            toast.success("Course published");
            setOpen(false);
            setForm({ title: "", description: "", price: 999, lessons: 5, category: "Development" });
            setThumbnail("");
            onCreated?.();
        } catch (err) {
            toast.error(err.response?.data?.detail || "Failed");
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={setOpen}>
            <DialogContent data-testid="new-course-dialog">
                <DialogHeader>
                    <DialogTitle>Publish a new course</DialogTitle>
                    <DialogDescription>
                        Add a title, description, price and a thumbnail.
                    </DialogDescription>
                </DialogHeader>
                <form onSubmit={submit} className="space-y-3">
                    <div className="space-y-1">
                        <Label>Title</Label>
                        <Input
                            value={form.title}
                            onChange={(e) => setForm({ ...form, title: e.target.value })}
                            required
                            className="rounded-xl"
                            data-testid="course-title-input"
                        />
                    </div>
                    <div className="space-y-1">
                        <Label>Description</Label>
                        <Textarea
                            value={form.description}
                            onChange={(e) => setForm({ ...form, description: e.target.value })}
                            rows={3}
                            className="rounded-xl"
                        />
                    </div>
                    <div className="grid grid-cols-3 gap-2">
                        <div className="space-y-1">
                            <Label>Price ₹</Label>
                            <Input
                                type="number"
                                value={form.price}
                                onChange={(e) => setForm({ ...form, price: +e.target.value })}
                                className="rounded-xl"
                            />
                        </div>
                        <div className="space-y-1">
                            <Label>Lessons</Label>
                            <Input
                                type="number"
                                value={form.lessons}
                                onChange={(e) => setForm({ ...form, lessons: +e.target.value })}
                                className="rounded-xl"
                            />
                        </div>
                        <div className="space-y-1">
                            <Label>Category</Label>
                            <Input
                                value={form.category}
                                onChange={(e) => setForm({ ...form, category: e.target.value })}
                                className="rounded-xl"
                            />
                        </div>
                    </div>
                    <div className="space-y-1">
                        <Label>Thumbnail</Label>
                        <div className="flex items-center gap-3">
                            {thumbnail && (
                                <img
                                    src={fileSrc(thumbnail)}
                                    alt=""
                                    className="h-14 w-20 rounded-lg object-cover"
                                />
                            )}
                            <Button
                                type="button"
                                variant="outline"
                                onClick={() => fileRef.current?.click()}
                                className="rounded-full"
                            >
                                <ImagePlus size={14} className="mr-1" />
                                {thumbnail ? "Replace" : "Upload"}
                            </Button>
                            <input
                                ref={fileRef}
                                type="file"
                                accept="image/*"
                                hidden
                                onChange={(e) => upload(e.target.files?.[0])}
                            />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button type="button" variant="ghost" onClick={() => setOpen(false)} className="rounded-full">
                            Cancel
                        </Button>
                        <Button
                            type="submit"
                            disabled={submitting}
                            className="rounded-full"
                            data-testid="course-submit-btn"
                        >
                            {submitting ? "Publishing…" : "Publish"}
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
}

function NewAdDialog({ open, setOpen, onCreated }) {
    const [form, setForm] = useState({
        title: "",
        caption: "",
        cta_label: "Learn more",
        cta_url: "",
        daily_budget: 500,
        duration_days: 7,
    });
    const [media, setMedia] = useState("");
    const [submitting, setSubmitting] = useState(false);
    const fileRef = useRef(null);

    const upload = async (f) => {
        if (!f) return;
        try {
            const r = await uploadFile(f);
            setMedia(r.url);
            toast.success("Ad creative uploaded");
        } catch {
            toast.error("Upload failed");
        }
    };

    const submit = async (e) => {
        e.preventDefault();
        if (!media) return toast.error("Add a creative image first");
        setSubmitting(true);
        try {
            await api.post("/ads", { ...form, media });
            toast.success("Ad campaign launched");
            setOpen(false);
            setForm({ title: "", caption: "", cta_label: "Learn more", cta_url: "", daily_budget: 500, duration_days: 7 });
            setMedia("");
            onCreated?.();
        } catch (err) {
            toast.error(err.response?.data?.detail || "Failed");
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={setOpen}>
            <DialogContent data-testid="new-ad-dialog">
                <DialogHeader>
                    <DialogTitle>Launch an ad campaign</DialogTitle>
                    <DialogDescription>
                        Promote a course, gig or post. Set budget and duration.
                    </DialogDescription>
                </DialogHeader>
                <form onSubmit={submit} className="space-y-3">
                    <div className="space-y-1">
                        <Label>Headline</Label>
                        <Input
                            value={form.title}
                            onChange={(e) => setForm({ ...form, title: e.target.value })}
                            required
                            className="rounded-xl"
                            data-testid="ad-title-input"
                        />
                    </div>
                    <div className="space-y-1">
                        <Label>Caption</Label>
                        <Textarea
                            value={form.caption}
                            onChange={(e) => setForm({ ...form, caption: e.target.value })}
                            rows={2}
                            className="rounded-xl"
                        />
                    </div>
                    <div className="space-y-1">
                        <Label>Creative (image)</Label>
                        <div className="flex items-center gap-3">
                            {media && (
                                <img
                                    src={fileSrc(media)}
                                    alt=""
                                    className="h-14 w-14 rounded-lg object-cover"
                                />
                            )}
                            <Button
                                type="button"
                                variant="outline"
                                onClick={() => fileRef.current?.click()}
                                className="rounded-full"
                                data-testid="ad-upload-btn"
                            >
                                <ImagePlus size={14} className="mr-1" />
                                {media ? "Replace" : "Upload"}
                            </Button>
                            <input
                                ref={fileRef}
                                type="file"
                                accept="image/*"
                                hidden
                                onChange={(e) => upload(e.target.files?.[0])}
                            />
                        </div>
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                        <div className="space-y-1">
                            <Label>CTA label</Label>
                            <Input
                                value={form.cta_label}
                                onChange={(e) => setForm({ ...form, cta_label: e.target.value })}
                                className="rounded-xl"
                            />
                        </div>
                        <div className="space-y-1">
                            <Label>CTA URL</Label>
                            <Input
                                value={form.cta_url}
                                onChange={(e) => setForm({ ...form, cta_url: e.target.value })}
                                placeholder="https://…"
                                className="rounded-xl"
                            />
                        </div>
                        <div className="space-y-1">
                            <Label>Daily budget ₹</Label>
                            <Input
                                type="number"
                                value={form.daily_budget}
                                onChange={(e) => setForm({ ...form, daily_budget: +e.target.value })}
                                className="rounded-xl"
                            />
                        </div>
                        <div className="space-y-1">
                            <Label>Duration (days)</Label>
                            <Input
                                type="number"
                                value={form.duration_days}
                                onChange={(e) => setForm({ ...form, duration_days: +e.target.value })}
                                className="rounded-xl"
                            />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button type="button" variant="ghost" onClick={() => setOpen(false)} className="rounded-full">
                            Cancel
                        </Button>
                        <Button
                            type="submit"
                            disabled={submitting}
                            className="rounded-full"
                            data-testid="ad-submit-btn"
                        >
                            {submitting ? "Launching…" : "Launch ad"}
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
}

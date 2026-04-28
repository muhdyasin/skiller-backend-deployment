import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
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
import { Plus, Mail, Trash2, Briefcase, BookOpen } from "lucide-react";
import { toast } from "sonner";

export default function CRM() {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [openGig, setOpenGig] = useState(false);

    const load = async () => {
        try {
            const r = await api.get("/dashboard/crm");
            setData(r.data);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        load();
    }, []);

    const setStatus = async (appId, status) => {
        try {
            await api.patch(`/gigs/applications/${appId}/status`, { status });
            toast.success(`Marked ${status}`);
            load();
        } catch {
            toast.error("Could not update");
        }
    };

    const deleteGig = async (id) => {
        if (!window.confirm("Delete this gig and all applications?")) return;
        try {
            await api.delete(`/gigs/${id}`);
            toast.success("Gig deleted");
            load();
        } catch {
            toast.error("Could not delete");
        }
    };

    if (loading) return <div className="py-20 text-center text-muted-foreground">Loading CRM…</div>;
    if (!data) return <div className="py-20 text-center text-muted-foreground">No data.</div>;

    return (
        <div className="mx-auto max-w-6xl px-4 py-6" data-testid="crm-page">
            <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
                <div>
                    <h1 className="font-display text-3xl font-bold tracking-tight">CRM</h1>
                    <p className="mt-1 text-sm text-muted-foreground">
                        Manage applicants and enrolled students. Reach out, shortlist and hire.
                    </p>
                </div>
                <div className="flex gap-2">
                    <Link
                        to="/dashboard"
                        className="rounded-full border border-border px-4 py-2 text-sm hover:bg-accent"
                    >
                        ← Dashboard
                    </Link>
                    <Button onClick={() => setOpenGig(true)} className="rounded-full" data-testid="new-gig-btn">
                        <Plus size={14} className="mr-1" /> Post a gig
                    </Button>
                </div>
            </div>

            <div className="mb-6 grid grid-cols-2 gap-3 md:grid-cols-4">
                <Stat label="Gigs" value={data.summary.gigs} icon={Briefcase} />
                <Stat label="Applications" value={data.summary.applications} icon={Mail} />
                <Stat label="Courses" value={data.summary.courses} icon={BookOpen} />
                <Stat label="Enrollments" value={data.summary.enrollments} icon={BookOpen} />
            </div>

            <Tabs defaultValue="gigs" className="w-full">
                <TabsList className="rounded-full bg-secondary p-1" data-testid="crm-tabs">
                    <TabsTrigger value="gigs" className="rounded-full" data-testid="crm-tab-gigs">
                        Gigs & Applicants
                    </TabsTrigger>
                    <TabsTrigger value="courses" className="rounded-full" data-testid="crm-tab-courses">
                        Course enrollments
                    </TabsTrigger>
                </TabsList>

                <TabsContent value="gigs" className="mt-6 space-y-6">
                    {data.gigs.length === 0 ? (
                        <div className="rounded-2xl border border-dashed border-border p-10 text-center text-sm text-muted-foreground">
                            You haven't posted any gig. Click "Post a gig" to start.
                        </div>
                    ) : (
                        data.gigs.map((b) => (
                            <div
                                key={b.gig.id}
                                className="overflow-hidden rounded-2xl border border-border"
                                data-testid={`crm-gig-${b.gig.id}`}
                            >
                                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border p-4">
                                    <div>
                                        <div className="font-display text-base font-bold">{b.gig.title}</div>
                                        <div className="mt-1 text-xs text-muted-foreground">
                                            {b.gig.category} · ₹{(b.gig.budget || 0).toLocaleString("en-IN")} · {b.applications.length} applicants
                                        </div>
                                    </div>
                                    <button
                                        onClick={() => deleteGig(b.gig.id)}
                                        className="text-muted-foreground hover:text-destructive"
                                        data-testid={`crm-delete-gig-${b.gig.id}`}
                                    >
                                        <Trash2 size={16} />
                                    </button>
                                </div>
                                {b.applications.length === 0 ? (
                                    <div className="px-4 py-8 text-center text-sm text-muted-foreground">
                                        No applications yet.
                                    </div>
                                ) : (
                                    <div className="divide-y divide-border/60">
                                        {b.applications.map((a) => (
                                            <div
                                                key={a.id}
                                                className="flex flex-col gap-3 p-4 md:flex-row md:items-center"
                                                data-testid={`crm-app-${a.id}`}
                                            >
                                                <img
                                                    src={
                                                        a.avatar_url ||
                                                        `https://api.dicebear.com/9.x/initials/svg?seed=${a.name}`
                                                    }
                                                    alt=""
                                                    className="h-10 w-10 rounded-full border border-border object-cover"
                                                />
                                                <div className="min-w-0 flex-1">
                                                    <Link
                                                        to={`/u/${a.username}`}
                                                        className="text-sm font-semibold hover:underline"
                                                    >
                                                        @{a.username}
                                                    </Link>
                                                    <div className="text-xs text-muted-foreground">{a.name} · {a.email}</div>
                                                    {a.message && (
                                                        <p className="mt-1 line-clamp-2 text-sm">{a.message}</p>
                                                    )}
                                                </div>
                                                <span
                                                    className={`rounded-full px-2 py-0.5 text-[11px] font-bold uppercase ${
                                                        a.status === "hired"
                                                            ? "bg-primary/10 text-primary"
                                                            : a.status === "shortlisted"
                                                              ? "bg-amber-500/10 text-amber-600"
                                                              : a.status === "rejected"
                                                                ? "bg-secondary text-muted-foreground line-through"
                                                                : "bg-secondary text-muted-foreground"
                                                    }`}
                                                >
                                                    {a.status}
                                                </span>
                                                <div className="flex gap-1">
                                                    <a
                                                        href={`mailto:${a.email}`}
                                                        className="grid h-8 w-8 place-items-center rounded-full border border-border hover:bg-accent"
                                                        title="Email"
                                                    >
                                                        <Mail size={14} />
                                                    </a>
                                                    <button
                                                        onClick={() => setStatus(a.id, "shortlisted")}
                                                        className="rounded-full border border-border px-3 py-1 text-xs hover:bg-accent"
                                                        data-testid={`crm-shortlist-${a.id}`}
                                                    >
                                                        Shortlist
                                                    </button>
                                                    <button
                                                        onClick={() => setStatus(a.id, "hired")}
                                                        className="rounded-full bg-primary px-3 py-1 text-xs font-semibold text-primary-foreground hover:bg-primary/90"
                                                        data-testid={`crm-hire-${a.id}`}
                                                    >
                                                        Hire
                                                    </button>
                                                    <button
                                                        onClick={() => setStatus(a.id, "rejected")}
                                                        className="rounded-full border border-border px-3 py-1 text-xs hover:bg-accent"
                                                    >
                                                        Reject
                                                    </button>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        ))
                    )}
                </TabsContent>

                <TabsContent value="courses" className="mt-6 space-y-6">
                    {data.courses.length === 0 ? (
                        <div className="rounded-2xl border border-dashed border-border p-10 text-center text-sm text-muted-foreground">
                            You haven't published any course yet.
                        </div>
                    ) : (
                        data.courses.map((b) => (
                            <div key={b.course.id} className="overflow-hidden rounded-2xl border border-border">
                                <div className="border-b border-border p-4">
                                    <div className="font-display text-base font-bold">{b.course.title}</div>
                                    <div className="mt-1 text-xs text-muted-foreground">
                                        {b.course.category} · {b.enrollments.length} enrollments
                                    </div>
                                </div>
                                {b.enrollments.length === 0 ? (
                                    <div className="px-4 py-8 text-center text-sm text-muted-foreground">
                                        No enrollments yet.
                                    </div>
                                ) : (
                                    <div className="divide-y divide-border/60">
                                        {b.enrollments.map((e) => (
                                            <div key={e.id} className="flex items-center gap-3 p-4">
                                                <img
                                                    src={
                                                        e.user?.avatar_url ||
                                                        `https://api.dicebear.com/9.x/initials/svg?seed=${e.user?.name}`
                                                    }
                                                    alt=""
                                                    className="h-9 w-9 rounded-full border border-border object-cover"
                                                />
                                                <div className="min-w-0 flex-1">
                                                    <Link
                                                        to={`/u/${e.user?.username}`}
                                                        className="text-sm font-semibold hover:underline"
                                                    >
                                                        @{e.user?.username}
                                                    </Link>
                                                    <div className="text-xs text-muted-foreground">{e.user?.email}</div>
                                                </div>
                                                <a
                                                    href={`mailto:${e.user?.email}`}
                                                    className="grid h-8 w-8 place-items-center rounded-full border border-border hover:bg-accent"
                                                >
                                                    <Mail size={14} />
                                                </a>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        ))
                    )}
                </TabsContent>
            </Tabs>

            <NewGigDialog open={openGig} setOpen={setOpenGig} onCreated={load} />
        </div>
    );
}

function Stat({ label, value, icon: Icon }) {
    return (
        <div className="rounded-2xl border border-border p-4">
            <div className="flex items-center justify-between">
                <div className="text-xs uppercase tracking-widest text-muted-foreground">{label}</div>
                {Icon && <Icon size={14} className="text-muted-foreground" />}
            </div>
            <div className="mt-1 font-display text-2xl font-bold">{value}</div>
        </div>
    );
}

function NewGigDialog({ open, setOpen, onCreated }) {
    const [form, setForm] = useState({
        title: "",
        description: "",
        budget: 10000,
        location: "Remote",
        category: "Development",
        skills: "",
    });
    const [submitting, setSubmitting] = useState(false);

    const submit = async (e) => {
        e.preventDefault();
        setSubmitting(true);
        try {
            const skills = form.skills
                .split(/[,\s]+/)
                .map((s) => s.trim())
                .filter(Boolean);
            await api.post("/gigs", { ...form, skills });
            toast.success("Gig posted");
            setOpen(false);
            setForm({
                title: "",
                description: "",
                budget: 10000,
                location: "Remote",
                category: "Development",
                skills: "",
            });
            onCreated?.();
        } catch (err) {
            toast.error(err.response?.data?.detail || "Failed");
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={setOpen}>
            <DialogContent data-testid="new-gig-dialog">
                <DialogHeader>
                    <DialogTitle>Post a new gig</DialogTitle>
                    <DialogDescription>
                        Describe the work, set a budget and the skills you need.
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
                            data-testid="gig-title-input"
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
                    <div className="grid grid-cols-2 gap-2">
                        <div className="space-y-1">
                            <Label>Budget ₹</Label>
                            <Input
                                type="number"
                                value={form.budget}
                                onChange={(e) => setForm({ ...form, budget: +e.target.value })}
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
                        <div className="space-y-1">
                            <Label>Location</Label>
                            <Input
                                value={form.location}
                                onChange={(e) => setForm({ ...form, location: e.target.value })}
                                className="rounded-xl"
                            />
                        </div>
                        <div className="space-y-1">
                            <Label>Skills</Label>
                            <Input
                                value={form.skills}
                                onChange={(e) => setForm({ ...form, skills: e.target.value })}
                                placeholder="React, Tailwind"
                                className="rounded-xl"
                            />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button type="button" variant="ghost" onClick={() => setOpen(false)} className="rounded-full">
                            Cancel
                        </Button>
                        <Button type="submit" disabled={submitting} className="rounded-full" data-testid="gig-submit-btn">
                            {submitting ? "Posting…" : "Post gig"}
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
}

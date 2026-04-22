import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { Button } from "../components/ui/button";
import { MapPin, Tag, IndianRupee } from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "../context/AuthContext";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogFooter,
} from "../components/ui/dialog";
import { Textarea } from "../components/ui/textarea";

export default function Gigs() {
    const { user } = useAuth();
    const [gigs, setGigs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState("All");
    const [applyOpen, setApplyOpen] = useState(false);
    const [activeGig, setActiveGig] = useState(null);
    const [message, setMessage] = useState("");
    const [submitting, setSubmitting] = useState(false);

    useEffect(() => {
        api
            .get("/gigs")
            .then((r) => setGigs(r.data))
            .finally(() => setLoading(false));
    }, []);

    const cats = ["All", ...new Set(gigs.map((g) => g.category))];
    const filtered = filter === "All" ? gigs : gigs.filter((g) => g.category === filter);

    const openApply = (g) => {
        if (!user) return toast.error("Sign in to apply for gigs");
        setActiveGig(g);
        setMessage("");
        setApplyOpen(true);
    };

    const submitApply = async () => {
        if (!activeGig) return;
        setSubmitting(true);
        try {
            await api.post(`/gigs/${activeGig.id}/apply`, { message });
            toast.success("Application sent!");
            setApplyOpen(false);
        } catch {
            toast.error("Could not submit application");
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="mx-auto max-w-6xl px-4 py-6" data-testid="gigs-page">
            <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
                <div>
                    <h1 className="font-display text-2xl font-bold tracking-tight md:text-3xl">
                        Open Gigs
                    </h1>
                    <p className="mt-1 text-sm text-muted-foreground">
                        Real projects. Real budgets. Apply with one click.
                    </p>
                </div>
                <div className="flex flex-wrap gap-2">
                    {cats.map((c) => (
                        <button
                            key={c}
                            onClick={() => setFilter(c)}
                            data-testid={`gig-filter-${c}`}
                            className={`rounded-full border px-4 py-1.5 text-sm transition-colors ${
                                filter === c
                                    ? "border-primary bg-primary text-primary-foreground"
                                    : "border-border hover:bg-accent"
                            }`}
                        >
                            {c}
                        </button>
                    ))}
                </div>
            </div>

            {loading ? (
                <div className="py-20 text-center text-muted-foreground">Loading gigs…</div>
            ) : (
                <div className="space-y-3">
                    {filtered.map((g) => (
                        <article
                            key={g.id}
                            className="flex flex-col gap-4 rounded-2xl border border-border p-5 transition-all hover:border-primary/40 md:flex-row md:items-center"
                            data-testid={`gig-${g.id}`}
                        >
                            <div className="flex-1">
                                <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                                    <span className="rounded-full bg-secondary px-2 py-0.5 font-semibold">
                                        {g.category}
                                    </span>
                                    <span className="flex items-center gap-1">
                                        <MapPin size={12} /> {g.location}
                                    </span>
                                </div>
                                <h3 className="mt-2 font-display text-lg font-bold leading-tight">
                                    {g.title}
                                </h3>
                                <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">
                                    {g.description}
                                </p>
                                <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
                                    {g.skills.map((s) => (
                                        <span
                                            key={s}
                                            className="inline-flex items-center gap-1 rounded-full border border-border px-2 py-0.5"
                                        >
                                            <Tag size={10} /> {s}
                                        </span>
                                    ))}
                                </div>
                            </div>
                            <div className="flex items-center justify-between gap-4 md:flex-col md:items-end">
                                <div className="text-right">
                                    <div className="text-xs text-muted-foreground">Budget</div>
                                    <div className="flex items-center font-display text-xl font-bold">
                                        <IndianRupee size={16} />
                                        {g.budget.toLocaleString("en-IN")}
                                    </div>
                                </div>
                                <Button
                                    onClick={() => openApply(g)}
                                    className="rounded-full"
                                    data-testid={`apply-gig-${g.id}`}
                                >
                                    Apply
                                </Button>
                            </div>
                        </article>
                    ))}
                </div>
            )}

            <Dialog open={applyOpen} onOpenChange={setApplyOpen}>
                <DialogContent data-testid="apply-dialog">
                    <DialogHeader>
                        <DialogTitle>
                            Apply · {activeGig?.title}
                        </DialogTitle>
                    </DialogHeader>
                    <div>
                        <Textarea
                            rows={5}
                            placeholder="Why you? Links, experience, timeline."
                            value={message}
                            onChange={(e) => setMessage(e.target.value)}
                            data-testid="apply-message-input"
                            className="rounded-xl"
                        />
                    </div>
                    <DialogFooter>
                        <Button variant="ghost" onClick={() => setApplyOpen(false)} className="rounded-full">
                            Cancel
                        </Button>
                        <Button
                            onClick={submitApply}
                            disabled={submitting}
                            className="rounded-full"
                            data-testid="apply-submit-btn"
                        >
                            {submitting ? "Sending…" : "Send application"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}

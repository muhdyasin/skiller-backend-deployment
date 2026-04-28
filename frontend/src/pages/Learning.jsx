import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { fileSrc } from "../lib/upload";
import { BookOpen, Briefcase, Trophy, Flame } from "lucide-react";

export default function Learning() {
    const [data, setData] = useState({
        enrolled: [],
        applications: [],
        xp: null,
    });
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        Promise.all([
            api.get("/users/me/enrollments").catch(() => ({ data: [] })),
            api.get("/users/me/applications").catch(() => ({ data: [] })),
            api.get("/users/me/xp"),
        ])
            .then(([e, a, x]) => {
                setData({
                    enrolled: e.data || [],
                    applications: a.data || [],
                    xp: x.data,
                });
            })
            .finally(() => setLoading(false));
    }, []);

    if (loading)
        return <div className="py-20 text-center text-muted-foreground">Loading…</div>;

    const xp = data.xp;

    return (
        <div className="mx-auto max-w-5xl px-4 py-6" data-testid="learning-page">
            <h1 className="font-display text-3xl font-bold tracking-tight">My Learning</h1>
            <p className="mt-1 text-sm text-muted-foreground">
                Your courses, gigs and progress — all in one place.
            </p>

            {xp && (
                <section className="mt-6 grid grid-cols-2 gap-3 md:grid-cols-4">
                    <Stat label="Level" value={`L${xp.level.level} · ${xp.level.name}`} icon={Trophy} />
                    <Stat label="Total XP" value={xp.xp} icon={Trophy} />
                    <Stat label="Streak" value={`${xp.streak}d`} icon={Flame} />
                    <Stat label="Badges" value={xp.earned_badges.length} icon={Trophy} />
                </section>
            )}

            <section className="mt-8">
                <div className="mb-3 flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-muted-foreground">
                    <BookOpen size={14} /> Enrolled courses
                </div>
                {data.enrolled.length === 0 ? (
                    <div className="rounded-2xl border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
                        You haven't enrolled in a course yet.{" "}
                        <Link to="/courses" className="font-semibold text-primary hover:underline">
                            Browse courses
                        </Link>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
                        {data.enrolled.map((c) => (
                            <Link
                                key={c.id}
                                to="/courses"
                                className="overflow-hidden rounded-2xl border border-border transition-colors hover:border-primary/40"
                            >
                                <img
                                    src={fileSrc(c.thumbnail)}
                                    alt=""
                                    className="aspect-video w-full object-cover"
                                />
                                <div className="p-3">
                                    <div className="text-xs text-muted-foreground">{c.category}</div>
                                    <div className="font-display text-base font-bold">{c.title}</div>
                                    <div className="mt-1 text-xs text-muted-foreground">{c.lessons} lessons · by {c.instructor}</div>
                                </div>
                            </Link>
                        ))}
                    </div>
                )}
            </section>

            <section className="mt-10">
                <div className="mb-3 flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-muted-foreground">
                    <Briefcase size={14} /> Gig applications
                </div>
                {data.applications.length === 0 ? (
                    <div className="rounded-2xl border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
                        You haven't applied to any gig yet.{" "}
                        <Link to="/gigs" className="font-semibold text-primary hover:underline">
                            Browse gigs
                        </Link>
                    </div>
                ) : (
                    <div className="space-y-3">
                        {data.applications.map((a) => (
                            <div
                                key={a.id}
                                className="flex items-center justify-between rounded-2xl border border-border p-4"
                            >
                                <div>
                                    <div className="font-display text-base font-bold">
                                        {a.gig?.title || "Gig"}
                                    </div>
                                    <div className="mt-1 text-xs text-muted-foreground">
                                        {a.gig?.category} · ₹{(a.gig?.budget || 0).toLocaleString("en-IN")}
                                    </div>
                                </div>
                                <span
                                    className={`rounded-full px-3 py-1 text-xs font-semibold ${
                                        a.status === "hired"
                                            ? "bg-primary/10 text-primary"
                                            : a.status === "shortlisted"
                                              ? "bg-amber-500/10 text-amber-600"
                                              : a.status === "rejected"
                                                ? "bg-secondary text-muted-foreground"
                                                : "bg-secondary text-muted-foreground"
                                    }`}
                                >
                                    {a.status}
                                </span>
                            </div>
                        ))}
                    </div>
                )}
            </section>

            {xp?.earned_badges?.length > 0 && (
                <section className="mt-10">
                    <div className="mb-3 text-xs font-bold uppercase tracking-widest text-muted-foreground">
                        Your badges
                    </div>
                    <div className="flex flex-wrap gap-2">
                        {xp.earned_badges.map((b) => (
                            <span
                                key={b.key}
                                title={b.desc}
                                className="inline-flex items-center gap-1.5 rounded-full bg-secondary px-3 py-1 text-sm"
                            >
                                <span>{b.icon}</span> {b.title}
                            </span>
                        ))}
                    </div>
                </section>
            )}
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
            <div className="mt-1 font-display text-xl font-bold">{value}</div>
        </div>
    );
}

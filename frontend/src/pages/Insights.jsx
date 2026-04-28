import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { fileSrc } from "../lib/upload";
import {
    BarChart3,
    Heart,
    MessageCircle,
    Users,
    BookOpen,
    Megaphone,
    TrendingUp,
} from "lucide-react";

function MiniBars({ values, color = "hsl(var(--primary))" }) {
    const max = Math.max(1, ...values);
    return (
        <div className="flex items-end gap-0.5 h-16">
            {values.map((v, i) => (
                <div
                    key={i}
                    className="flex-1 rounded-sm transition-colors"
                    style={{
                        height: `${(v / max) * 100}%`,
                        backgroundColor: v ? color : "hsl(var(--border))",
                        minHeight: 2,
                    }}
                    title={`${v}`}
                />
            ))}
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

export default function Insights() {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        api
            .get("/dashboard/insights")
            .then((r) => setData(r.data))
            .finally(() => setLoading(false));
    }, []);

    if (loading)
        return <div className="py-20 text-center text-muted-foreground">Loading insights…</div>;
    if (!data)
        return <div className="py-20 text-center text-muted-foreground">No data available.</div>;

    return (
        <div className="mx-auto max-w-6xl px-4 py-6" data-testid="insights-page">
            <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
                <div>
                    <h1 className="font-display text-3xl font-bold tracking-tight">Insights</h1>
                    <p className="mt-1 text-sm text-muted-foreground">
                        Last 30 days of your performance — posts, courses and ads.
                    </p>
                </div>
                <Link
                    to="/dashboard"
                    className="rounded-full border border-border px-4 py-2 text-sm hover:bg-accent"
                >
                    ← Back to dashboard
                </Link>
            </div>

            <div className="mb-6 grid grid-cols-2 gap-3 md:grid-cols-4">
                <Stat label="Posts" value={data.totals.posts} icon={BarChart3} />
                <Stat label="Likes" value={data.totals.likes} icon={Heart} />
                <Stat label="Comments" value={data.totals.comments} icon={MessageCircle} />
                <Stat label="Followers" value={data.followers} icon={Users} />
            </div>

            <section className="grid grid-cols-1 gap-4 md:grid-cols-3">
                <ChartCard label="Posts (30d)" values={data.series.posts} />
                <ChartCard label="Likes (30d)" values={data.series.likes} />
                <ChartCard label="Comments (30d)" values={data.series.comments} />
            </section>

            <section className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-2">
                <div>
                    <div className="mb-3 text-xs font-bold uppercase tracking-widest text-muted-foreground">
                        Top posts
                    </div>
                    {data.top_posts.length === 0 ? (
                        <div className="rounded-2xl border border-dashed border-border p-6 text-center text-sm text-muted-foreground">
                            Post your first content to see top performers.
                        </div>
                    ) : (
                        <div className="space-y-2">
                            {data.top_posts.map((p, i) => (
                                <Link
                                    key={p.id}
                                    to={`/p/${p.id}`}
                                    className="flex items-center gap-3 rounded-2xl border border-border p-3 hover:border-primary/40"
                                >
                                    <div className="font-display text-lg font-bold text-muted-foreground">#{i + 1}</div>
                                    <img
                                        src={fileSrc(p.media)}
                                        alt=""
                                        className="h-12 w-12 rounded-md object-cover"
                                    />
                                    <div className="min-w-0 flex-1">
                                        <div className="line-clamp-1 text-sm font-semibold">
                                            {p.caption || "(no caption)"}
                                        </div>
                                        <div className="text-xs text-muted-foreground">
                                            <Heart size={11} className="inline" /> {p.likes} ·{" "}
                                            <MessageCircle size={11} className="inline" /> {p.comments}
                                        </div>
                                    </div>
                                </Link>
                            ))}
                        </div>
                    )}
                </div>
                <div>
                    <div className="mb-3 text-xs font-bold uppercase tracking-widest text-muted-foreground">
                        Top courses
                    </div>
                    {data.top_courses.length === 0 ? (
                        <div className="rounded-2xl border border-dashed border-border p-6 text-center text-sm text-muted-foreground">
                            Publish a course to see enrolment data.
                        </div>
                    ) : (
                        <div className="space-y-2">
                            {data.top_courses.map((c, i) => (
                                <div
                                    key={c.id}
                                    className="flex items-center gap-3 rounded-2xl border border-border p-3"
                                >
                                    <div className="font-display text-lg font-bold text-muted-foreground">#{i + 1}</div>
                                    <img src={fileSrc(c.thumbnail)} alt="" className="h-12 w-16 rounded-md object-cover" />
                                    <div className="min-w-0 flex-1">
                                        <div className="line-clamp-1 text-sm font-semibold">{c.title}</div>
                                        <div className="text-xs text-muted-foreground">
                                            <BookOpen size={11} className="inline" /> {c.enrollments} enrolments · ₹{(c.price || 0).toLocaleString("en-IN")}
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </section>

            <section className="mt-8">
                <div className="mb-3 flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-muted-foreground">
                    <Megaphone size={14} /> Ads (lifetime)
                </div>
                <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
                    <Stat label="Campaigns" value={data.ads.campaigns} />
                    <Stat label="Active" value={data.ads.active} />
                    <Stat label="Impressions" value={data.ads.impressions.toLocaleString("en-IN")} />
                    <Stat label="Clicks" value={data.ads.clicks} />
                    <Stat
                        label="CTR / Spend"
                        value={`${data.ads.ctr}% · ₹${data.ads.spend.toLocaleString("en-IN")}`}
                        icon={TrendingUp}
                    />
                </div>
            </section>
        </div>
    );
}

function ChartCard({ label, values }) {
    return (
        <div className="rounded-2xl border border-border p-4">
            <div className="text-xs uppercase tracking-widest text-muted-foreground">{label}</div>
            <div className="mt-2">
                <MiniBars values={values} />
            </div>
            <div className="mt-2 text-xs text-muted-foreground">
                Total: <b>{values.reduce((a, b) => a + b, 0)}</b>
            </div>
        </div>
    );
}

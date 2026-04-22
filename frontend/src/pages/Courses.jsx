import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { Star, Users, PlayCircle } from "lucide-react";
import { Button } from "../components/ui/button";

export default function Courses() {
    const [courses, setCourses] = useState([]);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState("All");

    useEffect(() => {
        api
            .get("/courses")
            .then((r) => setCourses(r.data))
            .finally(() => setLoading(false));
    }, []);

    const categories = ["All", ...new Set(courses.map((c) => c.category))];
    const filtered =
        filter === "All" ? courses : courses.filter((c) => c.category === filter);

    return (
        <div className="mx-auto max-w-6xl px-4 py-6" data-testid="courses-page">
            <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
                <div>
                    <h1 className="font-display text-2xl font-bold tracking-tight md:text-3xl">
                        Courses
                    </h1>
                    <p className="mt-1 text-sm text-muted-foreground">
                        Creator-led programs. Learn from people who ship.
                    </p>
                </div>
                <div className="flex flex-wrap gap-2">
                    {categories.map((c) => (
                        <button
                            key={c}
                            onClick={() => setFilter(c)}
                            data-testid={`filter-${c}`}
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
                <div className="py-20 text-center text-muted-foreground">Loading courses…</div>
            ) : (
                <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
                    {filtered.map((c) => (
                        <article
                            key={c.id}
                            className="group overflow-hidden rounded-2xl border border-border transition-all hover:-translate-y-1 hover:border-primary/40"
                            data-testid={`course-${c.id}`}
                        >
                            <div className="relative aspect-video overflow-hidden bg-muted">
                                <img
                                    src={c.thumbnail}
                                    alt={c.title}
                                    className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
                                />
                                <span className="absolute left-3 top-3 rounded-full bg-background/90 px-2 py-0.5 text-xs font-semibold">
                                    {c.category}
                                </span>
                            </div>
                            <div className="p-5">
                                <div className="flex items-center gap-3 text-xs text-muted-foreground">
                                    <span className="flex items-center gap-1">
                                        <PlayCircle size={14} /> {c.lessons} lessons
                                    </span>
                                    <span className="flex items-center gap-1">
                                        <Users size={14} /> {c.students}
                                    </span>
                                    <span className="flex items-center gap-1">
                                        <Star size={14} className="fill-primary text-primary" /> {c.rating}
                                    </span>
                                </div>
                                <h3 className="mt-2 font-display text-lg font-bold leading-tight">
                                    {c.title}
                                </h3>
                                <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">
                                    {c.description}
                                </p>
                                <div className="mt-4 flex items-center justify-between">
                                    <div>
                                        <div className="text-xs text-muted-foreground">by {c.instructor}</div>
                                        <div className="font-display text-lg font-bold">
                                            ₹{c.price.toLocaleString("en-IN")}
                                        </div>
                                    </div>
                                    <Button className="rounded-full" data-testid={`enroll-${c.id}`}>
                                        Enroll
                                    </Button>
                                </div>
                            </div>
                        </article>
                    ))}
                </div>
            )}
        </div>
    );
}

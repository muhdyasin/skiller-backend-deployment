import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../lib/api";
import { fileSrc } from "../lib/upload";
import SearchBar from "../components/SearchBar";

export default function Search() {
    const [params] = useSearchParams();
    const q = params.get("q") || "";
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (!q.trim()) {
            setData(null);
            return;
        }
        setLoading(true);
        api
            .get(`/search?q=${encodeURIComponent(q.trim())}&limit=20`)
            .then((r) => setData(r.data))
            .finally(() => setLoading(false));
    }, [q]);

    return (
        <div className="mx-auto max-w-5xl px-4 py-6" data-testid="search-page">
            <div className="mb-6">
                <h1 className="font-display text-3xl font-bold tracking-tight">Search</h1>
                <div className="mt-3">
                    <SearchBar />
                </div>
            </div>

            {!q.trim() ? (
                <div className="py-20 text-center text-sm text-muted-foreground">
                    Type something above to find people, posts, courses and gigs.
                </div>
            ) : loading ? (
                <div className="py-20 text-center text-muted-foreground">Searching for "{q}"…</div>
            ) : !data ? null : (
                <div className="space-y-10">
                    {data.users.length > 0 && (
                        <Block label={`People · ${data.counts.users}`}>
                            <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
                                {data.users.map((u) => (
                                    <Link
                                        key={u.id}
                                        to={`/u/${u.username}`}
                                        className="flex items-center gap-3 rounded-2xl border border-border p-4 transition-colors hover:border-primary/40"
                                        data-testid={`search-result-user-${u.username}`}
                                    >
                                        <img
                                            src={u.avatar_url || `https://api.dicebear.com/9.x/initials/svg?seed=${u.name}`}
                                            alt=""
                                            className="h-12 w-12 rounded-full border border-border object-cover"
                                        />
                                        <div className="min-w-0 flex-1">
                                            <div className="truncate text-sm font-semibold">{u.username}</div>
                                            <div className="truncate text-xs text-muted-foreground">{u.name}</div>
                                            {u.bio && (
                                                <div className="mt-1 line-clamp-1 text-xs text-muted-foreground">{u.bio}</div>
                                            )}
                                        </div>
                                        {u.level && (
                                            <span className="rounded-full border border-border px-2 py-0.5 text-[10px] font-bold">
                                                L{u.level.level}
                                            </span>
                                        )}
                                    </Link>
                                ))}
                            </div>
                        </Block>
                    )}

                    {data.courses.length > 0 && (
                        <Block label={`Courses · ${data.counts.courses}`}>
                            <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
                                {data.courses.map((c) => (
                                    <Link
                                        key={c.id}
                                        to="/courses"
                                        className="overflow-hidden rounded-2xl border border-border transition-colors hover:border-primary/40"
                                    >
                                        <img src={fileSrc(c.thumbnail)} alt="" className="aspect-video w-full object-cover" />
                                        <div className="p-3">
                                            <div className="text-xs text-muted-foreground">{c.category}</div>
                                            <div className="font-display text-base font-bold">{c.title}</div>
                                            <div className="mt-1 text-xs text-muted-foreground">
                                                ₹{(c.price || 0).toLocaleString("en-IN")} · by {c.instructor}
                                            </div>
                                        </div>
                                    </Link>
                                ))}
                            </div>
                        </Block>
                    )}

                    {data.gigs.length > 0 && (
                        <Block label={`Gigs · ${data.counts.gigs}`}>
                            <div className="space-y-3">
                                {data.gigs.map((g) => (
                                    <Link
                                        key={g.id}
                                        to="/gigs"
                                        className="block rounded-2xl border border-border p-4 transition-colors hover:border-primary/40"
                                    >
                                        <div className="flex items-center justify-between">
                                            <div>
                                                <div className="font-display text-base font-bold">{g.title}</div>
                                                <div className="mt-1 text-xs text-muted-foreground">
                                                    {g.category} · {g.location}
                                                </div>
                                            </div>
                                            <div className="font-display text-lg font-bold">
                                                ₹{(g.budget || 0).toLocaleString("en-IN")}
                                            </div>
                                        </div>
                                    </Link>
                                ))}
                            </div>
                        </Block>
                    )}

                    {data.posts.length > 0 && (
                        <Block label={`Posts · ${data.counts.posts}`}>
                            <div className="grid grid-cols-2 gap-1 md:grid-cols-3 md:gap-4">
                                {data.posts.map((p) => (
                                    <Link
                                        key={p.id}
                                        to={`/p/${p.id}`}
                                        className="aspect-square overflow-hidden rounded-md md:rounded-2xl"
                                    >
                                        <img
                                            src={fileSrc(p.media)}
                                            alt=""
                                            className="h-full w-full object-cover transition-transform hover:scale-105"
                                        />
                                    </Link>
                                ))}
                            </div>
                        </Block>
                    )}

                    {data.users.length === 0 &&
                        data.courses.length === 0 &&
                        data.gigs.length === 0 &&
                        data.posts.length === 0 && (
                            <div className="py-16 text-center text-sm text-muted-foreground">
                                No matches for "{q}". Try another search.
                            </div>
                        )}
                </div>
            )}
        </div>
    );
}

function Block({ label, children }) {
    return (
        <section>
            <div className="mb-3 text-xs font-bold uppercase tracking-widest text-muted-foreground">
                {label}
            </div>
            {children}
        </section>
    );
}

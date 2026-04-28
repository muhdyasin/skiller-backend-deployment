import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Search as SearchIcon, X } from "lucide-react";
import { api } from "../lib/api";
import { fileSrc } from "../lib/upload";

export default function SearchBar({ compact, autoFocus }) {
    const [q, setQ] = useState("");
    const [results, setResults] = useState(null);
    const [open, setOpen] = useState(false);
    const [loading, setLoading] = useState(false);
    const ref = useRef(null);
    const navigate = useNavigate();

    useEffect(() => {
        if (!q.trim()) {
            setResults(null);
            return;
        }
        setLoading(true);
        const t = setTimeout(async () => {
            try {
                const { data } = await api.get(`/search?q=${encodeURIComponent(q.trim())}&limit=5`);
                setResults(data);
            } catch {
                setResults(null);
            } finally {
                setLoading(false);
            }
        }, 250);
        return () => clearTimeout(t);
    }, [q]);

    useEffect(() => {
        const onClick = (e) => {
            if (ref.current && !ref.current.contains(e.target)) setOpen(false);
        };
        if (open) document.addEventListener("mousedown", onClick);
        return () => document.removeEventListener("mousedown", onClick);
    }, [open]);

    const goSearch = () => {
        if (!q.trim()) return;
        navigate(`/search?q=${encodeURIComponent(q.trim())}`);
        setOpen(false);
    };

    const handleKey = (e) => {
        if (e.key === "Enter") goSearch();
        else if (e.key === "Escape") setOpen(false);
    };

    return (
        <div ref={ref} className={`relative ${compact ? "w-full" : "w-full max-w-md"}`}>
            <div className="relative">
                <SearchIcon
                    size={16}
                    className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
                />
                <input
                    type="text"
                    autoFocus={autoFocus}
                    value={q}
                    onChange={(e) => {
                        setQ(e.target.value);
                        setOpen(true);
                    }}
                    onFocus={() => q.trim() && setOpen(true)}
                    onKeyDown={handleKey}
                    placeholder="Search creators, posts, courses, gigs"
                    data-testid="search-input"
                    className="h-10 w-full rounded-full border border-border bg-secondary/60 pl-9 pr-9 text-sm outline-none ring-primary placeholder:text-muted-foreground focus:bg-background focus:ring-2"
                />
                {q && (
                    <button
                        onClick={() => {
                            setQ("");
                            setResults(null);
                        }}
                        className="absolute right-2 top-1/2 -translate-y-1/2 grid h-6 w-6 place-items-center rounded-full hover:bg-accent"
                        data-testid="search-clear-btn"
                    >
                        <X size={12} />
                    </button>
                )}
            </div>

            {open && q.trim() && (
                <div
                    className="absolute left-0 right-0 top-12 z-50 max-h-[60vh] overflow-auto rounded-2xl border border-border bg-popover shadow-xl"
                    data-testid="search-dropdown"
                >
                    {loading && !results && (
                        <div className="px-4 py-6 text-center text-sm text-muted-foreground">Searching…</div>
                    )}
                    {results && (
                        <div className="divide-y divide-border/60">
                            {results.users.length > 0 && (
                                <Section label="People">
                                    {results.users.map((u) => (
                                        <button
                                            key={u.id}
                                            onClick={() => {
                                                navigate(`/u/${u.username}`);
                                                setOpen(false);
                                            }}
                                            className="flex w-full items-center gap-3 px-4 py-2 text-left hover:bg-accent"
                                            data-testid={`search-user-${u.username}`}
                                        >
                                            <img
                                                src={u.avatar_url || `https://api.dicebear.com/9.x/initials/svg?seed=${u.name}`}
                                                alt=""
                                                className="h-9 w-9 rounded-full border border-border object-cover"
                                            />
                                            <div className="min-w-0 flex-1">
                                                <div className="truncate text-sm font-semibold">{u.username}</div>
                                                <div className="truncate text-xs text-muted-foreground">{u.name}</div>
                                            </div>
                                            {u.level && (
                                                <span className="rounded-full border border-border px-2 py-0.5 text-[10px] font-bold">
                                                    L{u.level.level}
                                                </span>
                                            )}
                                        </button>
                                    ))}
                                </Section>
                            )}
                            {results.courses.length > 0 && (
                                <Section label="Courses">
                                    {results.courses.map((c) => (
                                        <button
                                            key={c.id}
                                            onClick={() => {
                                                navigate("/courses");
                                                setOpen(false);
                                            }}
                                            className="flex w-full items-center gap-3 px-4 py-2 text-left hover:bg-accent"
                                        >
                                            <img
                                                src={fileSrc(c.thumbnail)}
                                                alt=""
                                                className="h-9 w-12 rounded-md object-cover"
                                            />
                                            <div className="min-w-0 flex-1">
                                                <div className="truncate text-sm font-semibold">{c.title}</div>
                                                <div className="truncate text-xs text-muted-foreground">
                                                    {c.category} · ₹{(c.price || 0).toLocaleString("en-IN")}
                                                </div>
                                            </div>
                                        </button>
                                    ))}
                                </Section>
                            )}
                            {results.gigs.length > 0 && (
                                <Section label="Gigs">
                                    {results.gigs.map((g) => (
                                        <button
                                            key={g.id}
                                            onClick={() => {
                                                navigate("/gigs");
                                                setOpen(false);
                                            }}
                                            className="flex w-full items-center gap-3 px-4 py-2 text-left hover:bg-accent"
                                        >
                                            <div className="grid h-9 w-9 place-items-center rounded-md bg-primary/10 text-xs font-bold text-primary">
                                                ₹
                                            </div>
                                            <div className="min-w-0 flex-1">
                                                <div className="truncate text-sm font-semibold">{g.title}</div>
                                                <div className="truncate text-xs text-muted-foreground">
                                                    {g.category} · ₹{(g.budget || 0).toLocaleString("en-IN")}
                                                </div>
                                            </div>
                                        </button>
                                    ))}
                                </Section>
                            )}
                            {results.posts.length > 0 && (
                                <Section label="Posts">
                                    {results.posts.map((p) => (
                                        <button
                                            key={p.id}
                                            onClick={() => {
                                                navigate(`/p/${p.id}`);
                                                setOpen(false);
                                            }}
                                            className="flex w-full items-center gap-3 px-4 py-2 text-left hover:bg-accent"
                                        >
                                            <img
                                                src={fileSrc(p.media)}
                                                alt=""
                                                className="h-9 w-9 rounded-md object-cover"
                                            />
                                            <div className="min-w-0 flex-1">
                                                <div className="truncate text-sm">{p.caption || "(no caption)"}</div>
                                                <div className="truncate text-xs text-muted-foreground">
                                                    @{p.author?.username || "user"}
                                                </div>
                                            </div>
                                        </button>
                                    ))}
                                </Section>
                            )}
                            {results.users.length === 0 &&
                                results.courses.length === 0 &&
                                results.gigs.length === 0 &&
                                results.posts.length === 0 && (
                                    <div className="px-4 py-8 text-center text-sm text-muted-foreground">
                                        No results for "{q}"
                                    </div>
                                )}
                            <button
                                onClick={goSearch}
                                className="block w-full px-4 py-3 text-center text-sm font-semibold text-primary hover:bg-accent"
                            >
                                See all results →
                            </button>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

function Section({ label, children }) {
    return (
        <div>
            <div className="bg-secondary/60 px-4 py-1 text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
                {label}
            </div>
            {children}
        </div>
    );
}

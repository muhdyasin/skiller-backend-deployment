import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Plus, Search, Users, MessageCircle } from "lucide-react";
import { api, formatApiError } from "../lib/api";
import { Button } from "../components/ui/button";
import { toast } from "sonner";
import { useAuth } from "../context/AuthContext";

export default function Community() {
    const { user } = useAuth();
    const [groups, setGroups] = useState([]);
    const [loading, setLoading] = useState(true);
    const [query, setQuery] = useState("");
    const [creating, setCreating] = useState(false);
    const [showNew, setShowNew] = useState(false);

    const load = async () => {
        try {
            setLoading(true);
            const res = await api.get("/community/groups");
            setGroups(res.data || []);
        } catch (err) {
            toast.error(formatApiError(err.response?.data?.detail));
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        load();
    }, []);

    const filtered = groups.filter((g) =>
        (g.display_name || "").toLowerCase().includes(query.toLowerCase()),
    );

    return (
        <div className="mx-auto max-w-4xl px-4 py-6" data-testid="community-page">
            <div className="flex items-center justify-between">
                <h1 className="font-display text-2xl font-extrabold">Community</h1>
                <Button
                    onClick={() => setShowNew(true)}
                    className="rounded-full"
                    data-testid="new-group-btn"
                >
                    <Plus size={14} className="mr-1.5" /> New
                </Button>
            </div>
            <p className="mt-1 text-sm text-muted-foreground">
                Group chats and DMs — share posts, courses & gigs with your circle.
            </p>

            <div className="relative mt-4">
                <Search size={14} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                <input
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="Search chats"
                    className="h-10 w-full rounded-full border border-border bg-secondary/60 pl-9 pr-3 text-sm outline-none focus:bg-background focus:ring-2 focus:ring-primary"
                    data-testid="community-search"
                />
            </div>

            {loading ? (
                <div className="mt-8 space-y-2">
                    {Array.from({ length: 4 }).map((_, i) => (
                        <div key={i} className="h-16 animate-pulse rounded-2xl bg-secondary/40" />
                    ))}
                </div>
            ) : filtered.length === 0 ? (
                <div className="mt-12 rounded-2xl border border-dashed border-border py-16 text-center" data-testid="community-empty">
                    <MessageCircle className="mx-auto text-muted-foreground" size={28} />
                    <div className="mt-2 text-sm font-semibold">No chats yet</div>
                    <p className="mt-1 text-xs text-muted-foreground">
                        Start a DM with a creator or build a group with your community.
                    </p>
                    <Button
                        onClick={() => setShowNew(true)}
                        className="mt-4 rounded-full"
                        data-testid="empty-new-group-btn"
                    >
                        <Plus size={14} className="mr-1.5" /> Start a chat
                    </Button>
                </div>
            ) : (
                <ul className="mt-4 divide-y divide-border rounded-2xl border border-border bg-card" data-testid="community-list">
                    {filtered.map((g) => (
                        <li key={g.id}>
                            <Link
                                to={`/community/${g.id}`}
                                className="flex items-center gap-3 px-4 py-3 hover:bg-accent/50"
                                data-testid={`community-row-${g.id}`}
                            >
                                <img
                                    src={g.display_avatar || `https://api.dicebear.com/9.x/initials/svg?seed=${g.display_name}`}
                                    alt=""
                                    className="h-12 w-12 shrink-0 rounded-full border border-border object-cover"
                                />
                                <div className="min-w-0 flex-1">
                                    <div className="flex items-center justify-between gap-2">
                                        <div className="truncate font-semibold">
                                            {g.display_name}
                                            {g.is_dm && (
                                                <span className="ml-2 rounded-full bg-secondary px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-widest text-muted-foreground">
                                                    DM
                                                </span>
                                            )}
                                            {!g.is_dm && (
                                                <span className="ml-2 inline-flex items-center gap-0.5 rounded-full bg-secondary px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-widest text-muted-foreground">
                                                    <Users size={10} /> {(g.members || []).length}
                                                </span>
                                            )}
                                        </div>
                                        <div className="text-[10px] text-muted-foreground">
                                            {g.last_message_at && new Date(g.last_message_at).toLocaleDateString("en-IN", { day: "2-digit", month: "short" })}
                                        </div>
                                    </div>
                                    <div className="flex items-center justify-between gap-2">
                                        <div className="truncate text-xs text-muted-foreground">
                                            {g.last_message_preview || "No messages yet"}
                                        </div>
                                        {g.unread > 0 && (
                                            <span className="rounded-full bg-primary px-2 py-0.5 text-[10px] font-bold text-primary-foreground" data-testid={`community-unread-${g.id}`}>
                                                {g.unread}
                                            </span>
                                        )}
                                    </div>
                                </div>
                            </Link>
                        </li>
                    ))}
                </ul>
            )}

            {showNew && (
                <NewGroupDialog
                    onClose={() => setShowNew(false)}
                    onCreated={async () => {
                        setShowNew(false);
                        await load();
                    }}
                    creating={creating}
                    setCreating={setCreating}
                />
            )}
        </div>
    );
}

function NewGroupDialog({ onClose, onCreated, creating, setCreating }) {
    const [mode, setMode] = useState("group");
    const [name, setName] = useState("");
    const [usernamesText, setUsernamesText] = useState("");
    const inputRef = useRef(null);

    useEffect(() => {
        inputRef.current?.focus();
    }, [mode]);

    const submit = async (e) => {
        e.preventDefault();
        const usernames = usernamesText
            .split(/[, ]+/)
            .map((u) => u.replace("@", "").trim().toLowerCase())
            .filter(Boolean);
        if (mode === "dm" && usernames.length !== 1) {
            return toast.error("Enter one username for DM");
        }
        if (mode === "group" && (!name.trim() || usernames.length === 0)) {
            return toast.error("Group name + at least 1 member required");
        }
        try {
            setCreating(true);
            await api.post("/community/groups", {
                name: mode === "dm" ? "DM" : name.trim(),
                is_dm: mode === "dm",
                member_usernames: usernames,
            });
            toast.success(mode === "dm" ? "DM ready" : "Group created");
            await onCreated();
        } catch (err) {
            toast.error(formatApiError(err.response?.data?.detail));
        } finally {
            setCreating(false);
        }
    };

    return (
        <div
            className="fixed inset-0 z-50 grid place-items-end bg-black/40 p-0 md:place-items-center md:p-6"
            onClick={onClose}
        >
            <div
                onClick={(e) => e.stopPropagation()}
                className="w-full max-w-md rounded-t-3xl bg-background p-6 md:rounded-3xl"
                data-testid="new-group-dialog"
            >
                <div className="mb-4 flex gap-1 rounded-full bg-secondary/50 p-1">
                    <button
                        onClick={() => setMode("group")}
                        className={`flex-1 rounded-full px-3 py-2 text-sm font-semibold ${mode === "group" ? "bg-primary text-primary-foreground" : ""}`}
                        data-testid="mode-group"
                    >
                        Group
                    </button>
                    <button
                        onClick={() => setMode("dm")}
                        className={`flex-1 rounded-full px-3 py-2 text-sm font-semibold ${mode === "dm" ? "bg-primary text-primary-foreground" : ""}`}
                        data-testid="mode-dm"
                    >
                        Direct message
                    </button>
                </div>

                <form onSubmit={submit} className="space-y-3">
                    {mode === "group" && (
                        <input
                            ref={inputRef}
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            placeholder="Group name"
                            className="h-11 w-full rounded-2xl border border-input bg-background px-4 text-sm outline-none focus:ring-2 focus:ring-primary"
                            data-testid="new-group-name"
                            required
                        />
                    )}
                    <input
                        ref={mode === "dm" ? inputRef : null}
                        value={usernamesText}
                        onChange={(e) => setUsernamesText(e.target.value)}
                        placeholder={mode === "dm" ? "@username" : "Comma-separated @usernames"}
                        className="h-11 w-full rounded-2xl border border-input bg-background px-4 text-sm outline-none focus:ring-2 focus:ring-primary"
                        data-testid="new-group-usernames"
                        required
                    />
                    <div className="flex justify-end gap-2 pt-2">
                        <Button type="button" variant="ghost" onClick={onClose} className="rounded-full">
                            Cancel
                        </Button>
                        <Button type="submit" disabled={creating} className="rounded-full" data-testid="new-group-submit">
                            {creating ? "Creating…" : mode === "dm" ? "Start DM" : "Create group"}
                        </Button>
                    </div>
                </form>
            </div>
        </div>
    );
}

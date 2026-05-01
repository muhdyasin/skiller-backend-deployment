import { useEffect, useRef, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { ArrowLeft, Image as ImageIcon, Send, Smile, CheckCheck, Users } from "lucide-react";
import { api, API, formatApiError } from "../lib/api";
import { fileSrc, uploadFile } from "../lib/upload";
import { useAuth } from "../context/AuthContext";
import { toast } from "sonner";

const REACTIONS = ["❤️", "🔥", "👍", "😂", "😮", "🙏"];

export default function GroupChat() {
    const { groupId } = useParams();
    const { user } = useAuth();
    const navigate = useNavigate();
    const [group, setGroup] = useState(null);
    const [messages, setMessages] = useState([]);
    const [text, setText] = useState("");
    const [sending, setSending] = useState(false);
    const [typingUsers, setTypingUsers] = useState({}); // user_id -> {username, until}
    const [reactPicker, setReactPicker] = useState(null);
    const fileRef = useRef(null);
    const scrollerRef = useRef(null);
    const wsRef = useRef(null);
    const typingDebounce = useRef(null);

    const scrollToBottom = (smooth = true) => {
        const el = scrollerRef.current;
        if (!el) return;
        el.scrollTo({ top: el.scrollHeight, behavior: smooth ? "smooth" : "auto" });
    };

    const load = async () => {
        try {
            const [g, m] = await Promise.all([
                api.get(`/community/groups/${groupId}`),
                api.get(`/community/groups/${groupId}/messages?limit=80`),
            ]);
            setGroup(g.data);
            setMessages(m.data);
            await api.post(`/community/groups/${groupId}/read`, {});
            setTimeout(() => scrollToBottom(false), 50);
        } catch (err) {
            toast.error(formatApiError(err.response?.data?.detail));
            navigate("/community");
        }
    };

    useEffect(() => {
        load();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [groupId]);

    // WebSocket for realtime
    useEffect(() => {
        if (!user) return;
        const token = localStorage.getItem("skiller_token");
        if (!token) return;
        const wsUrl = `${API.replace(/^http/, "ws")}/ws?token=${token}`;
        let active = true;
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;
        ws.onmessage = (evt) => {
            if (!active) return;
            try {
                const m = JSON.parse(evt.data);
                if (m.type === "group_message" && m.data?.group_id === groupId) {
                    setMessages((prev) => {
                        if (prev.find((x) => x.id === m.data.id)) return prev;
                        return [...prev, m.data];
                    });
                    setTimeout(() => scrollToBottom(true), 30);
                    if (m.data.sender_id !== user.id) {
                        api.post(`/community/groups/${groupId}/read`, {}).catch(() => {});
                    }
                } else if (m.type === "group_reaction" && m.data?.group_id === groupId) {
                    setMessages((prev) =>
                        prev.map((msg) =>
                            msg.id === m.data.message_id
                                ? { ...msg, reactions: m.data.reactions }
                                : msg,
                        ),
                    );
                } else if (m.type === "group_read" && m.data?.group_id === groupId) {
                    setMessages((prev) =>
                        prev.map((msg) =>
                            msg.read_by?.includes(m.data.user_id)
                                ? msg
                                : { ...msg, read_by: [...(msg.read_by || []), m.data.user_id] },
                        ),
                    );
                } else if (m.type === "group_typing" && m.data?.group_id === groupId) {
                    setTypingUsers((prev) => ({
                        ...prev,
                        [m.data.user_id]: m.data.typing
                            ? { username: m.data.username, until: Date.now() + 3500 }
                            : null,
                    }));
                }
            } catch {
                /* ignore */
            }
        };
        ws.onerror = () => {};
        ws.onclose = () => {};
        // GC stale typing state every 1s
        const gc = setInterval(() => {
            setTypingUsers((prev) => {
                const out = {};
                for (const [k, v] of Object.entries(prev)) {
                    if (v && v.until > Date.now()) out[k] = v;
                }
                return out;
            });
        }, 1000);
        return () => {
            active = false;
            clearInterval(gc);
            try {
                ws.close();
            } catch {
                /* ignore */
            }
        };
    }, [groupId, user?.id]);

    const send = async (e) => {
        e?.preventDefault?.();
        const t = text.trim();
        if (!t) return;
        setSending(true);
        try {
            await api.post(`/community/groups/${groupId}/messages`, { type: "text", text: t });
            setText("");
        } catch (err) {
            toast.error(formatApiError(err.response?.data?.detail));
        } finally {
            setSending(false);
        }
    };

    const sendImage = async (e) => {
        const file = e.target.files?.[0];
        if (!file) return;
        try {
            toast.message("Uploading…");
            const up = await uploadFile(file);
            await api.post(`/community/groups/${groupId}/messages`, {
                type: "image",
                media: up.url || up.path,
            });
        } catch (err) {
            toast.error(formatApiError(err.response?.data?.detail));
        } finally {
            e.target.value = "";
        }
    };

    const onType = (v) => {
        setText(v);
        if (typingDebounce.current) clearTimeout(typingDebounce.current);
        api.post(`/community/groups/${groupId}/typing`, { typing: true }).catch(() => {});
        typingDebounce.current = setTimeout(() => {
            api.post(`/community/groups/${groupId}/typing`, { typing: false }).catch(() => {});
        }, 2500);
    };

    const react = async (messageId, emoji) => {
        setReactPicker(null);
        try {
            await api.post(
                `/community/groups/${groupId}/messages/${messageId}/react`,
                { emoji },
            );
        } catch (err) {
            toast.error(formatApiError(err.response?.data?.detail));
        }
    };

    if (!group) {
        return (
            <div className="grid h-[60vh] place-items-center text-muted-foreground" data-testid="chat-loading">
                Loading chat…
            </div>
        );
    }

    const otherTyping = Object.values(typingUsers).filter(Boolean);

    return (
        <div className="mx-auto flex h-[calc(100vh-7rem)] max-w-3xl flex-col px-0 md:h-[calc(100vh-2rem)] md:px-4 md:py-4" data-testid="group-chat">
            {/* Header */}
            <header className="sticky top-0 z-10 flex items-center gap-3 border-b border-border bg-background/95 px-4 py-3 backdrop-blur md:rounded-t-2xl md:border md:border-border">
                <Link
                    to="/community"
                    className="grid h-9 w-9 place-items-center rounded-full hover:bg-accent"
                    data-testid="chat-back-btn"
                >
                    <ArrowLeft size={18} />
                </Link>
                <img
                    src={group.display_avatar || `https://api.dicebear.com/9.x/initials/svg?seed=${group.display_name}`}
                    alt=""
                    className="h-10 w-10 rounded-full border border-border object-cover"
                />
                <div className="min-w-0 flex-1">
                    <div className="truncate font-semibold" data-testid="chat-name">
                        {group.display_name}
                    </div>
                    <div className="truncate text-[11px] text-muted-foreground">
                        {otherTyping.length > 0 ? (
                            <span className="text-primary">{otherTyping[0].username} typing…</span>
                        ) : group.is_dm ? (
                            "Direct message"
                        ) : (
                            <span className="inline-flex items-center gap-1">
                                <Users size={10} /> {group.members?.length} members
                            </span>
                        )}
                    </div>
                </div>
            </header>

            {/* Messages */}
            <div
                ref={scrollerRef}
                className="flex-1 overflow-y-auto bg-secondary/20 px-3 py-4 md:border-x md:border-border"
                data-testid="chat-messages"
            >
                {messages.length === 0 ? (
                    <div className="grid h-full place-items-center text-sm text-muted-foreground">
                        No messages yet — say hi 👋
                    </div>
                ) : (
                    <ul className="space-y-1.5">
                        {messages.map((m, i) => {
                            const mine = m.sender_id === user?.id;
                            const showAvatar = !mine && (i === 0 || messages[i - 1].sender_id !== m.sender_id);
                            const reactions = m.reactions || {};
                            const reactKeys = Object.keys(reactions).filter((k) => reactions[k]?.length > 0);
                            const readByOthers = (m.read_by || []).filter((uid) => uid !== user?.id);
                            return (
                                <li
                                    key={m.id}
                                    className={`flex items-end gap-1.5 ${mine ? "justify-end" : "justify-start"}`}
                                    data-testid={`msg-${m.id}`}
                                >
                                    {!mine && (
                                        <div className="w-7 shrink-0">
                                            {showAvatar && (
                                                <img
                                                    src={m.sender?.avatar_url || `https://api.dicebear.com/9.x/initials/svg?seed=${m.sender?.name}`}
                                                    alt=""
                                                    className="h-7 w-7 rounded-full border border-border object-cover"
                                                />
                                            )}
                                        </div>
                                    )}
                                    <div className={`group relative max-w-[78%] ${mine ? "items-end" : "items-start"}`}>
                                        {!mine && showAvatar && !group.is_dm && (
                                            <div className="mb-0.5 px-1 text-[10px] font-bold text-primary">
                                                @{m.sender?.username}
                                            </div>
                                        )}
                                        <div
                                            className={`rounded-2xl px-3 py-2 text-sm shadow-sm ${
                                                mine
                                                    ? "bg-primary text-primary-foreground"
                                                    : "bg-background"
                                            }`}
                                        >
                                            {m.type === "text" && <span className="whitespace-pre-wrap break-words">{m.text}</span>}
                                            {m.type === "image" && (
                                                <img
                                                    src={fileSrc(m.media)}
                                                    alt=""
                                                    className="max-h-72 rounded-xl object-cover"
                                                />
                                            )}
                                            {m.type === "share" && m.share && (
                                                <Link
                                                    to={shareLink(m.share)}
                                                    className="block rounded-xl bg-secondary/40 p-2 text-xs"
                                                >
                                                    <div className="font-bold uppercase tracking-widest text-muted-foreground">
                                                        Shared {m.share.kind}
                                                    </div>
                                                    <div className="mt-0.5 truncate">{m.share.title || m.share.id}</div>
                                                </Link>
                                            )}
                                            <div className={`mt-0.5 flex items-center justify-end gap-1 text-[9px] ${
                                                mine ? "text-primary-foreground/80" : "text-muted-foreground"
                                            }`}>
                                                {new Date(m.created_at).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })}
                                                {mine && (
                                                    <CheckCheck
                                                        size={12}
                                                        className={readByOthers.length > 0 ? "text-sky-300" : ""}
                                                        data-testid={readByOthers.length > 0 ? "read-receipt" : undefined}
                                                    />
                                                )}
                                            </div>
                                        </div>
                                        {/* Reaction badges */}
                                        {reactKeys.length > 0 && (
                                            <div className={`mt-0.5 flex gap-1 ${mine ? "justify-end" : "justify-start"}`}>
                                                {reactKeys.map((k) => (
                                                    <span
                                                        key={k}
                                                        className="inline-flex items-center gap-0.5 rounded-full bg-background px-1.5 py-0.5 text-[10px] shadow"
                                                    >
                                                        {k} {reactions[k].length}
                                                    </span>
                                                ))}
                                            </div>
                                        )}
                                        {/* Hover/long-press react picker */}
                                        <button
                                            onClick={() => setReactPicker(reactPicker === m.id ? null : m.id)}
                                            className={`absolute ${mine ? "-left-7" : "-right-7"} top-1 hidden h-6 w-6 place-items-center rounded-full bg-background text-muted-foreground shadow group-hover:grid`}
                                            data-testid={`react-toggle-${m.id}`}
                                        >
                                            <Smile size={12} />
                                        </button>
                                        {reactPicker === m.id && (
                                            <div
                                                className={`absolute z-10 ${mine ? "right-0" : "left-0"} -top-9 flex gap-0.5 rounded-full border border-border bg-background p-1 shadow-lg`}
                                            >
                                                {REACTIONS.map((emo) => (
                                                    <button
                                                        key={emo}
                                                        onClick={() => react(m.id, emo)}
                                                        className="grid h-8 w-8 place-items-center rounded-full text-base transition-transform hover:scale-125"
                                                        data-testid={`react-${m.id}-${emo}`}
                                                    >
                                                        {emo}
                                                    </button>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                </li>
                            );
                        })}
                    </ul>
                )}
                {otherTyping.length > 0 && (
                    <div className="ml-9 mt-2 inline-flex items-center gap-1 rounded-full bg-background px-3 py-1 text-xs text-muted-foreground shadow">
                        <span className="flex gap-0.5">
                            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-primary [animation-delay:-0.3s]" />
                            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-primary [animation-delay:-0.15s]" />
                            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-primary" />
                        </span>
                    </div>
                )}
            </div>

            {/* Composer */}
            <form
                onSubmit={send}
                className="sticky bottom-0 flex items-center gap-2 border-t border-border bg-background/95 px-3 py-2.5 backdrop-blur md:rounded-b-2xl md:border md:border-t-0 md:border-border"
                data-testid="chat-composer"
            >
                <button
                    type="button"
                    onClick={() => fileRef.current?.click()}
                    className="grid h-10 w-10 shrink-0 place-items-center rounded-full hover:bg-accent"
                    data-testid="chat-attach-btn"
                >
                    <ImageIcon size={18} />
                </button>
                <input ref={fileRef} type="file" accept="image/*" onChange={sendImage} className="hidden" />
                <input
                    value={text}
                    onChange={(e) => onType(e.target.value)}
                    placeholder="Message"
                    className="h-10 flex-1 rounded-full border border-input bg-background px-4 text-sm outline-none focus:ring-2 focus:ring-primary"
                    data-testid="chat-input"
                />
                <button
                    type="submit"
                    disabled={sending || !text.trim()}
                    className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-primary text-primary-foreground disabled:opacity-50"
                    data-testid="chat-send-btn"
                >
                    <Send size={16} />
                </button>
            </form>
        </div>
    );
}

function shareLink(s) {
    if (!s) return "#";
    if (s.kind === "post") return `/p/${s.id}`;
    if (s.kind === "course") return `/courses`;
    if (s.kind === "gig") return `/gigs`;
    if (s.kind === "creator") return `/c/${s.id}`;
    return "#";
}

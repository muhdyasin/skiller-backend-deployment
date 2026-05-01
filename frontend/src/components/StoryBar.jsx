import { useEffect, useRef, useState } from "react";
import { Plus, X, ChevronLeft, ChevronRight } from "lucide-react";
import { api, formatApiError } from "../lib/api";
import { fileSrc, uploadFile } from "../lib/upload";
import { useAuth } from "../context/AuthContext";
import { toast } from "sonner";

export default function StoryBar() {
    const { user } = useAuth();
    const [groups, setGroups] = useState([]);
    const [loading, setLoading] = useState(true);
    const [viewing, setViewing] = useState(null); // {groupIndex, storyIndex}
    const fileRef = useRef(null);

    const load = async () => {
        try {
            setLoading(true);
            const res = await api.get("/stories/feed");
            setGroups(res.data || []);
        } catch {
            // silently
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (user) load();
    }, [user?.id]);

    if (!user) return null;

    const onPickFile = async (e) => {
        const file = e.target.files?.[0];
        if (!file) return;
        try {
            toast.message("Uploading story…");
            const up = await uploadFile(file);
            await api.post("/stories", {
                media: up.url || up.path,
                media_type: file.type.startsWith("video/") ? "video" : "image",
            });
            toast.success("Story posted — visible for 24h");
            await load();
        } catch (err) {
            toast.error(formatApiError(err.response?.data?.detail) || "Could not post story");
        } finally {
            e.target.value = "";
        }
    };

    return (
        <>
            <div
                className="flex items-start gap-3 overflow-x-auto px-4 pb-3 pt-1 md:px-0 [&::-webkit-scrollbar]:hidden"
                style={{ scrollbarWidth: "none" }}
                data-testid="story-bar"
            >
                {/* Add story */}
                <button
                    type="button"
                    onClick={() => fileRef.current?.click()}
                    className="flex w-16 shrink-0 flex-col items-center gap-1.5"
                    data-testid="add-story-btn"
                >
                    <span className="relative grid h-16 w-16 place-items-center rounded-full border-2 border-dashed border-border bg-secondary/50 transition-colors hover:bg-secondary">
                        <img
                            src={user.avatar_url || `https://api.dicebear.com/9.x/initials/svg?seed=${user.name}`}
                            alt=""
                            className="h-14 w-14 rounded-full border-2 border-background object-cover"
                        />
                        <span className="absolute -bottom-0.5 -right-0.5 grid h-6 w-6 place-items-center rounded-full bg-primary text-primary-foreground ring-2 ring-background">
                            <Plus size={14} />
                        </span>
                    </span>
                    <span className="text-[10px] font-semibold text-muted-foreground">Your story</span>
                </button>
                <input
                    ref={fileRef}
                    type="file"
                    accept="image/*,video/*"
                    onChange={onPickFile}
                    className="hidden"
                    data-testid="story-file-input"
                />

                {loading ? (
                    Array.from({ length: 5 }).map((_, i) => (
                        <div key={i} className="h-16 w-16 shrink-0 animate-pulse rounded-full bg-secondary/50" />
                    ))
                ) : (
                    groups.map((g, gi) => (
                        <button
                            key={g.user?.id || gi}
                            type="button"
                            onClick={() => setViewing({ gi, si: 0 })}
                            className="flex w-16 shrink-0 flex-col items-center gap-1.5"
                            data-testid={`story-bubble-${g.user?.username}`}
                        >
                            <span
                                className={`grid h-16 w-16 place-items-center rounded-full p-[2px] ${
                                    g.has_unviewed
                                        ? "bg-gradient-to-br from-primary via-rose-500 to-orange-400"
                                        : "bg-secondary"
                                }`}
                            >
                                <img
                                    src={g.user?.avatar_url || `https://api.dicebear.com/9.x/initials/svg?seed=${g.user?.name}`}
                                    alt=""
                                    className="h-full w-full rounded-full border-2 border-background object-cover"
                                />
                            </span>
                            <span className="max-w-[60px] truncate text-[10px] font-semibold">
                                @{g.user?.username || "user"}
                            </span>
                        </button>
                    ))
                )}
            </div>

            {viewing && (
                <StoryViewer
                    groups={groups}
                    init={viewing}
                    onClose={() => setViewing(null)}
                    onAdvance={(next) => {
                        if (!next) {
                            setViewing(null);
                            load();
                        } else {
                            setViewing(next);
                        }
                    }}
                />
            )}
        </>
    );
}

function StoryViewer({ groups, init, onClose, onAdvance }) {
    const [pos, setPos] = useState(init);
    const group = groups[pos.gi];
    const story = group?.stories?.[pos.si];
    const [progress, setProgress] = useState(0);

    useEffect(() => {
        if (!story) return;
        // mark viewed
        api.post(`/stories/${story.id}/view`).catch(() => {});
        setProgress(0);
        const start = Date.now();
        const dur = story.media_type === "video" ? 12000 : 5000;
        const t = setInterval(() => {
            const p = Math.min(1, (Date.now() - start) / dur);
            setProgress(p);
            if (p >= 1) {
                clearInterval(t);
                advance(1);
            }
        }, 50);
        return () => clearInterval(t);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [pos.gi, pos.si]);

    const advance = (delta) => {
        const g = groups[pos.gi];
        const nextSi = pos.si + delta;
        if (nextSi >= 0 && nextSi < g.stories.length) {
            onAdvance({ gi: pos.gi, si: nextSi });
            setPos({ gi: pos.gi, si: nextSi });
            return;
        }
        const nextGi = pos.gi + delta;
        if (nextGi >= 0 && nextGi < groups.length) {
            const newSi = delta > 0 ? 0 : groups[nextGi].stories.length - 1;
            onAdvance({ gi: nextGi, si: newSi });
            setPos({ gi: nextGi, si: newSi });
            return;
        }
        onAdvance(null);
    };

    if (!story || !group) return null;

    const remainingHrs = Math.max(
        0,
        Math.round((new Date(story.expires_at).getTime() - Date.now()) / 3600000),
    );

    return (
        <div
            className="fixed inset-0 z-[60] flex items-center justify-center bg-black/95 backdrop-blur-sm"
            data-testid="story-viewer"
            onClick={onClose}
        >
            <div
                className="relative h-full w-full max-w-md md:h-[90vh] md:rounded-3xl md:overflow-hidden"
                onClick={(e) => e.stopPropagation()}
            >
                {/* Progress segments */}
                <div className="absolute left-0 right-0 top-0 z-20 flex gap-1 p-2">
                    {group.stories.map((s, i) => (
                        <span key={s.id} className="h-1 flex-1 overflow-hidden rounded-full bg-white/20">
                            <span
                                className="block h-full bg-white transition-[width] duration-100"
                                style={{
                                    width:
                                        i < pos.si
                                            ? "100%"
                                            : i === pos.si
                                            ? `${progress * 100}%`
                                            : "0%",
                                }}
                            />
                        </span>
                    ))}
                </div>

                {/* Header */}
                <div className="absolute left-0 right-0 top-3 z-20 flex items-center gap-3 px-4 pt-2">
                    <img
                        src={group.user?.avatar_url || `https://api.dicebear.com/9.x/initials/svg?seed=${group.user?.name}`}
                        alt=""
                        className="h-8 w-8 rounded-full border border-white/30 object-cover"
                    />
                    <div className="min-w-0 flex-1 text-white">
                        <div className="text-sm font-semibold">@{group.user?.username}</div>
                        <div className="text-[11px] text-white/70">
                            Expires in {remainingHrs}h · {new Date(story.created_at).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })}
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="grid h-8 w-8 place-items-center rounded-full bg-white/10 text-white"
                        data-testid="story-close-btn"
                    >
                        <X size={16} />
                    </button>
                </div>

                {/* Media */}
                <div className="absolute inset-0 grid place-items-center bg-black">
                    {story.media_type === "video" ? (
                        <video
                            src={fileSrc(story.media)}
                            autoPlay
                            playsInline
                            className="h-full w-full object-contain"
                        />
                    ) : (
                        <img src={fileSrc(story.media)} alt="" className="h-full w-full object-contain" />
                    )}
                </div>

                {/* Caption */}
                {story.caption && (
                    <div className="absolute inset-x-0 bottom-16 z-10 px-6 text-center">
                        <p className="inline-block rounded-2xl bg-black/50 px-4 py-2 text-sm text-white backdrop-blur">
                            {story.caption}
                        </p>
                    </div>
                )}

                {/* Tap zones */}
                <button
                    onClick={() => advance(-1)}
                    className="absolute bottom-0 left-0 top-12 z-10 w-1/3 text-white/60"
                    aria-label="Previous"
                >
                    <ChevronLeft size={24} className="ml-3" />
                </button>
                <button
                    onClick={() => advance(1)}
                    className="absolute bottom-0 right-0 top-12 z-10 w-1/3 text-right text-white/60"
                    aria-label="Next"
                >
                    <ChevronRight size={24} className="ml-auto mr-3" />
                </button>
            </div>
        </div>
    );
}

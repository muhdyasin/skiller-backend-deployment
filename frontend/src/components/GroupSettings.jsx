import { useEffect, useState } from "react";
import { X, UserPlus, LogOut, Trash2, Check, Camera } from "lucide-react";
import { api, formatApiError } from "../lib/api";
import { Button } from "./ui/button";
import { uploadFile } from "../lib/upload";
import { toast } from "sonner";
import { useAuth } from "../context/AuthContext";
import { useNavigate } from "react-router-dom";

export default function GroupSettings({ group, onClose, onUpdated }) {
    const { user } = useAuth();
    const navigate = useNavigate();
    const [name, setName] = useState(group.name || "");
    const [desc, setDesc] = useState(group.description || "");
    const [avatar, setAvatar] = useState(group.avatar_url || "");
    const [newMember, setNewMember] = useState("");
    const [saving, setSaving] = useState(false);

    const isAdmin = (group.admins || []).includes(user?.id);
    const isDM = !!group.is_dm;

    const save = async () => {
        if (!isAdmin) return;
        try {
            setSaving(true);
            await api.patch(`/community/groups/${group.id}`, {
                name: name.trim(),
                description: desc.trim(),
                avatar_url: avatar.trim(),
            });
            toast.success("Group updated");
            onUpdated && (await onUpdated());
        } catch (err) {
            toast.error(formatApiError(err.response?.data?.detail));
        } finally {
            setSaving(false);
        }
    };

    const uploadAvatar = async (e) => {
        const file = e.target.files?.[0];
        if (!file) return;
        try {
            toast.message("Uploading…");
            const up = await uploadFile(file);
            setAvatar(up.url || up.path);
        } catch {
            toast.error("Upload failed");
        } finally {
            e.target.value = "";
        }
    };

    const addMember = async () => {
        const uname = newMember.replace("@", "").trim().toLowerCase();
        if (!uname) return;
        try {
            await api.post(`/community/groups/${group.id}/members`, { username: uname });
            toast.success(`@${uname} added`);
            setNewMember("");
            onUpdated && (await onUpdated());
        } catch (err) {
            toast.error(formatApiError(err.response?.data?.detail));
        }
    };

    const removeMember = async (memberId) => {
        try {
            await api.delete(`/community/groups/${group.id}/members/${memberId}`);
            toast.success("Removed");
            onUpdated && (await onUpdated());
        } catch (err) {
            toast.error(formatApiError(err.response?.data?.detail));
        }
    };

    const leave = async () => {
        if (!window.confirm(isDM ? "Close this DM?" : "Leave this group?")) return;
        try {
            await api.delete(`/community/groups/${group.id}/members/${user.id}`);
            toast.success(isDM ? "DM closed" : "You left the group");
            navigate("/community");
        } catch (err) {
            toast.error(formatApiError(err.response?.data?.detail));
        }
    };

    return (
        <div
            className="fixed inset-0 z-50 grid place-items-end bg-black/40 md:place-items-center md:p-6"
            onClick={onClose}
            data-testid="group-settings-overlay"
        >
            <div
                onClick={(e) => e.stopPropagation()}
                className="max-h-[90vh] w-full max-w-md overflow-y-auto rounded-t-3xl bg-background p-6 md:rounded-3xl"
                data-testid="group-settings-dialog"
            >
                <div className="flex items-center justify-between">
                    <h2 className="font-display text-xl font-bold">
                        {isDM ? "Chat details" : "Group details"}
                    </h2>
                    <button
                        onClick={onClose}
                        className="grid h-8 w-8 place-items-center rounded-full hover:bg-accent"
                        data-testid="group-settings-close"
                    >
                        <X size={16} />
                    </button>
                </div>

                {!isDM && (
                    <>
                        {/* Avatar */}
                        <div className="mt-4 flex items-center gap-3">
                            <div className="relative">
                                <img
                                    src={
                                        avatar ||
                                        `https://api.dicebear.com/9.x/initials/svg?seed=${name || "Group"}`
                                    }
                                    alt=""
                                    className="h-16 w-16 rounded-full border border-border object-cover"
                                />
                                {isAdmin && (
                                    <label className="absolute -bottom-1 -right-1 grid h-7 w-7 cursor-pointer place-items-center rounded-full bg-primary text-primary-foreground">
                                        <Camera size={12} />
                                        <input
                                            type="file"
                                            accept="image/*"
                                            onChange={uploadAvatar}
                                            className="hidden"
                                            data-testid="group-avatar-input"
                                        />
                                    </label>
                                )}
                            </div>
                            <div className="min-w-0 flex-1">
                                <input
                                    value={name}
                                    onChange={(e) => setName(e.target.value)}
                                    disabled={!isAdmin}
                                    placeholder="Group name"
                                    className="w-full rounded-xl border border-input bg-background px-3 py-2 text-sm font-semibold outline-none disabled:opacity-70"
                                    data-testid="group-name-input"
                                />
                            </div>
                        </div>

                        <textarea
                            value={desc}
                            onChange={(e) => setDesc(e.target.value)}
                            disabled={!isAdmin}
                            placeholder="Description (what's this group about?)"
                            rows={2}
                            className="mt-3 w-full rounded-xl border border-input bg-background px-3 py-2 text-sm outline-none disabled:opacity-70"
                            data-testid="group-desc-input"
                        />

                        {isAdmin && (
                            <Button
                                onClick={save}
                                disabled={saving}
                                className="mt-3 w-full rounded-full"
                                data-testid="group-save-btn"
                            >
                                <Check size={14} className="mr-1.5" />
                                {saving ? "Saving…" : "Save changes"}
                            </Button>
                        )}

                        {/* Members */}
                        <div className="mt-5">
                            <div className="mb-2 flex items-center justify-between text-xs font-bold uppercase tracking-widest text-muted-foreground">
                                <span>Members · {group.member_objs?.length || 0}</span>
                            </div>
                            <ul className="divide-y divide-border rounded-2xl border border-border" data-testid="group-members-list">
                                {(group.member_objs || []).map((m) => {
                                    const isAdminMember = (group.admins || []).includes(m.id);
                                    return (
                                        <li key={m.id} className="flex items-center gap-3 px-3 py-2 text-sm">
                                            <img
                                                src={m.avatar_url || `https://api.dicebear.com/9.x/initials/svg?seed=${m.name}`}
                                                alt=""
                                                className="h-8 w-8 rounded-full border border-border object-cover"
                                            />
                                            <div className="min-w-0 flex-1">
                                                <div className="truncate text-sm font-semibold">@{m.username}</div>
                                                <div className="truncate text-xs text-muted-foreground">
                                                    {m.name} {isAdminMember && <span className="ml-1 rounded-full bg-primary/10 px-1.5 py-0.5 text-[9px] font-bold text-primary">admin</span>}
                                                </div>
                                            </div>
                                            {isAdmin && m.id !== user.id && (
                                                <button
                                                    onClick={() => removeMember(m.id)}
                                                    className="grid h-8 w-8 place-items-center rounded-full text-rose-500 hover:bg-rose-500/10"
                                                    aria-label="Remove"
                                                    data-testid={`remove-member-${m.username}`}
                                                >
                                                    <Trash2 size={14} />
                                                </button>
                                            )}
                                        </li>
                                    );
                                })}
                            </ul>
                            {isAdmin && (
                                <div className="mt-2 flex items-center gap-2">
                                    <input
                                        value={newMember}
                                        onChange={(e) => setNewMember(e.target.value)}
                                        onKeyDown={(e) => e.key === "Enter" && addMember()}
                                        placeholder="@username to add"
                                        className="h-10 flex-1 rounded-full border border-input bg-background px-3 text-sm outline-none"
                                        data-testid="add-member-input"
                                    />
                                    <Button
                                        onClick={addMember}
                                        className="rounded-full"
                                        size="sm"
                                        data-testid="add-member-btn"
                                    >
                                        <UserPlus size={14} className="mr-1" /> Add
                                    </Button>
                                </div>
                            )}
                        </div>
                    </>
                )}

                <div className="mt-6 border-t border-border pt-4">
                    <Button
                        onClick={leave}
                        variant="outline"
                        className="w-full rounded-full border-rose-500/30 text-rose-600 hover:bg-rose-500/10"
                        data-testid="leave-group-btn"
                    >
                        <LogOut size={14} className="mr-1.5" />
                        {isDM ? "Close chat" : "Leave group"}
                    </Button>
                </div>
            </div>
        </div>
    );
}

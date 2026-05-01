import { useState } from "react";
import { Mail, X } from "lucide-react";
import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { toast } from "sonner";

export default function VerifyEmailBanner() {
    const { user } = useAuth();
    const [hidden, setHidden] = useState(false);
    const [sending, setSending] = useState(false);

    if (!user || user.email_verified || hidden) return null;

    const resend = async () => {
        try {
            setSending(true);
            const { data } = await api.post("/auth/resend-verification");
            if (data.already_verified) {
                toast.success("Already verified — refresh");
            } else {
                toast.success("Verification email sent — check inbox");
            }
        } catch (err) {
            const msg = err.response?.data?.detail || "Could not send — try again";
            toast.error(typeof msg === "string" ? msg : "Could not send");
        } finally {
            setSending(false);
        }
    };

    return (
        <div
            className="mx-auto mb-3 flex max-w-4xl items-center gap-3 rounded-2xl border border-amber-500/30 bg-amber-500/10 px-4 py-2.5 text-sm"
            data-testid="verify-email-banner"
        >
            <Mail size={16} className="shrink-0 text-amber-600 dark:text-amber-400" />
            <div className="flex-1 text-amber-800 dark:text-amber-200">
                <strong>Verify {user.email}</strong> to secure your account and earn +25 XP.
            </div>
            <button
                onClick={resend}
                disabled={sending}
                className="rounded-full border border-amber-500/40 bg-amber-500/20 px-3 py-1 text-xs font-semibold text-amber-900 hover:bg-amber-500/30 dark:text-amber-100 disabled:opacity-50"
                data-testid="resend-verify-btn"
            >
                {sending ? "Sending…" : "Resend email"}
            </button>
            <button
                onClick={() => setHidden(true)}
                className="grid h-6 w-6 place-items-center rounded-full hover:bg-amber-500/20"
                data-testid="verify-banner-close"
                aria-label="Hide"
            >
                <X size={12} />
            </button>
        </div>
    );
}

import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Crown } from "lucide-react";
import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";

export default function TrialBadge({ compact }) {
    const { user } = useAuth();
    const [info, setInfo] = useState(null);

    useEffect(() => {
        let cancel = false;
        if (!user) return;
        api.get("/billing/me")
            .then((r) => {
                if (!cancel) setInfo(r.data);
            })
            .catch(() => {});
        return () => {
            cancel = true;
        };
    }, [user?.id]);

    if (!user || !info) return null;

    const days = info.days_left || 0;
    const isPremium = !!info.is_premium;
    const urgent = isPremium && days <= 7;
    const expired = !isPremium;

    const tone = expired
        ? "border-rose-500/30 bg-rose-500/10 text-rose-600 dark:text-rose-300"
        : urgent
        ? "border-amber-500/30 bg-amber-500/10 text-amber-600 dark:text-amber-300"
        : "border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-300";

    const label = expired ? "Trial expired" : `${days}d ${info.plan === "pro" ? "premium" : "trial"}`;

    if (compact) {
        return (
            <Link
                to="/billing"
                className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-bold ${tone}`}
                data-testid="trial-badge-compact"
            >
                <Crown size={10} />
                {label}
            </Link>
        );
    }

    return (
        <Link
            to="/billing"
            className={`block rounded-2xl border px-3 py-2 text-xs font-semibold ${tone}`}
            data-testid="trial-badge"
        >
            <div className="flex items-center gap-1.5">
                <Crown size={12} />
                <span>{label}</span>
            </div>
            <div className="mt-0.5 text-[10px] opacity-80">
                {expired
                    ? "Reactivate premium tools →"
                    : urgent
                    ? "Renew before expiry →"
                    : "Manage subscription →"}
            </div>
        </Link>
    );
}

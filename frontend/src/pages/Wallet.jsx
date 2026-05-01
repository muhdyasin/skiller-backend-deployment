import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Coins, Users, Copy, ArrowUpRight, ArrowDownRight, Megaphone, BookOpen, Sparkles, Crown } from "lucide-react";
import { api, formatApiError } from "../lib/api";
import { Button } from "../components/ui/button";
import { toast } from "sonner";

const PURPOSES = [
    { id: "ai_credits", label: "AI Credits", icon: Sparkles, hint: "1 token = 1 AI recommendation" },
    { id: "ads", label: "Ad Credits", icon: Megaphone, hint: "Use to run sponsored posts" },
    { id: "course", label: "Course", icon: BookOpen, hint: "Spend on a course of your choice" },
];

export default function Wallet() {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [redeeming, setRedeeming] = useState(false);
    const [purpose, setPurpose] = useState("ai_credits");
    const [amount, setAmount] = useState(50);

    const load = async () => {
        try {
            setLoading(true);
            const res = await api.get("/wallet/me");
            setData(res.data);
        } catch (err) {
            toast.error(formatApiError(err.response?.data?.detail));
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        load();
    }, []);

    const copyLink = async () => {
        if (!data?.referral_code) return;
        const link = `${window.location.origin}/register?ref=${data.referral_code}`;
        try {
            await navigator.clipboard.writeText(link);
            toast.success("Referral link copied");
        } catch {
            toast.error("Could not copy");
        }
    };

    const redeem = async () => {
        if (!amount || amount <= 0) return toast.error("Enter a token amount");
        if (purpose === "course") {
            return toast.error("Open a course page and tap 'Pay with tokens'");
        }
        try {
            setRedeeming(true);
            await api.post("/wallet/redeem", { amount: Number(amount), purpose });
            toast.success(`${amount} tokens redeemed for ${purpose.replace("_", " ")}`);
            await load();
        } catch (err) {
            toast.error(formatApiError(err.response?.data?.detail));
        } finally {
            setRedeeming(false);
        }
    };

    if (loading || !data)
        return <div className="py-20 text-center text-muted-foreground" data-testid="wallet-loading">Loading wallet…</div>;

    const { wallet, ledger, referral_code, reward_per_referral, referrals, stats } = data;

    return (
        <div className="mx-auto max-w-5xl px-4 py-6" data-testid="wallet-page">
            {/* Hero */}
            <div className="overflow-hidden rounded-3xl border border-border bg-gradient-to-br from-primary/15 via-primary/5 to-background p-6 md:p-10">
                <div className="flex flex-wrap items-end justify-between gap-6">
                    <div>
                        <div className="text-xs font-bold uppercase tracking-widest text-primary">
                            Skiller Tokens
                        </div>
                        <div className="mt-1 flex items-end gap-2">
                            <Coins size={36} className="text-primary" />
                            <span className="font-display text-5xl font-extrabold leading-none" data-testid="wallet-balance">
                                {wallet.balance.toLocaleString("en-IN")}
                            </span>
                            <span className="pb-1 text-sm text-muted-foreground">≈ ₹{wallet.balance.toLocaleString("en-IN")}</span>
                        </div>
                        <div className="mt-2 text-xs text-muted-foreground">
                            Earned {wallet.lifetime_earned.toLocaleString("en-IN")} · Spent {wallet.lifetime_spent.toLocaleString("en-IN")}
                        </div>
                    </div>
                    <Link
                        to="/billing"
                        className="rounded-full bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground hover:bg-primary/90"
                        data-testid="wallet-go-billing"
                    >
                        <Crown size={14} className="mr-1.5 inline" /> Subscribe with tokens
                    </Link>
                </div>
            </div>

            {/* Referrals */}
            <div className="mt-6 grid grid-cols-1 gap-6 md:grid-cols-3">
                <div className="rounded-2xl border border-border bg-card p-5 md:col-span-2">
                    <div className="flex items-center gap-2 text-sm font-bold">
                        <Users size={16} className="text-primary" /> Refer friends · earn {reward_per_referral} tokens each
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground">
                        Tokens drop into your wallet when your friend completes their first paid subscription.
                    </p>
                    <div className="mt-3 flex items-center gap-2 rounded-full border border-border bg-secondary/50 px-3 py-2">
                        <code className="flex-1 truncate text-xs" data-testid="referral-code">
                            {window.location.origin}/register?ref={referral_code}
                        </code>
                        <Button
                            size="sm"
                            variant="outline"
                            className="rounded-full"
                            onClick={copyLink}
                            data-testid="copy-referral-btn"
                        >
                            <Copy size={12} className="mr-1" /> Copy
                        </Button>
                    </div>
                    <div className="mt-3 flex gap-3 text-xs">
                        <Stat label="Total" value={stats.total} />
                        <Stat label="Rewarded" value={stats.rewarded} accent />
                        <Stat label="Pending" value={stats.pending} />
                    </div>
                    {referrals.length > 0 && (
                        <ul className="mt-4 space-y-2" data-testid="referral-list">
                            {referrals.slice(0, 5).map((r) => (
                                <li key={r.id} className="flex items-center gap-3 rounded-xl bg-secondary/30 px-3 py-2 text-sm">
                                    <img
                                        src={r.referred?.avatar_url || `https://api.dicebear.com/9.x/initials/svg?seed=${r.referred?.name || "u"}`}
                                        alt=""
                                        className="h-8 w-8 rounded-full border border-border object-cover"
                                    />
                                    <div className="flex-1 truncate">
                                        <div className="truncate text-sm font-semibold">@{r.referred?.username || "unknown"}</div>
                                        <div className="text-xs text-muted-foreground">{r.referred?.name}</div>
                                    </div>
                                    <span className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-widest ${
                                        r.status === "rewarded"
                                            ? "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400"
                                            : "bg-amber-500/15 text-amber-600 dark:text-amber-400"
                                    }`}>
                                        {r.status}
                                    </span>
                                </li>
                            ))}
                        </ul>
                    )}
                </div>

                {/* Redeem */}
                <div className="rounded-2xl border border-border bg-card p-5">
                    <div className="text-sm font-bold">Redeem tokens</div>
                    <p className="mt-1 text-xs text-muted-foreground">1 token = ₹1</p>
                    <div className="mt-3 grid grid-cols-3 gap-1.5">
                        {PURPOSES.map(({ id, label, icon: Icon }) => (
                            <button
                                key={id}
                                onClick={() => setPurpose(id)}
                                className={`flex flex-col items-center gap-1 rounded-xl border px-2 py-2.5 text-[10px] font-semibold transition-colors ${
                                    purpose === id
                                        ? "border-primary bg-primary/10 text-primary"
                                        : "border-border hover:bg-accent"
                                }`}
                                data-testid={`redeem-purpose-${id}`}
                            >
                                <Icon size={14} />
                                {label}
                            </button>
                        ))}
                    </div>
                    <p className="mt-2 text-[10px] text-muted-foreground">
                        {PURPOSES.find((p) => p.id === purpose)?.hint}
                    </p>
                    <div className="mt-3 flex items-center gap-2">
                        <input
                            type="number"
                            min={1}
                            value={amount}
                            onChange={(e) => setAmount(e.target.value)}
                            className="h-10 flex-1 rounded-full border border-input bg-background px-4 text-sm outline-none"
                            data-testid="redeem-amount"
                        />
                        <Button
                            onClick={redeem}
                            disabled={redeeming || wallet.balance < Number(amount) || purpose === "course"}
                            className="rounded-full"
                            data-testid="redeem-btn"
                        >
                            Redeem
                        </Button>
                    </div>
                </div>
            </div>

            {/* Ledger */}
            <div className="mt-6 rounded-2xl border border-border bg-card">
                <div className="border-b border-border px-5 py-3 text-sm font-bold">Recent activity</div>
                {ledger.length === 0 ? (
                    <div className="px-5 py-12 text-center text-sm text-muted-foreground" data-testid="ledger-empty">
                        No activity yet — your token earnings will show here.
                    </div>
                ) : (
                    <ul className="divide-y divide-border" data-testid="ledger-list">
                        {ledger.map((l) => (
                            <li key={l.id} className="flex items-center gap-3 px-5 py-3 text-sm">
                                <span className={`grid h-9 w-9 place-items-center rounded-full ${
                                    l.type === "credit"
                                        ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                                        : "bg-rose-500/10 text-rose-600 dark:text-rose-400"
                                }`}>
                                    {l.type === "credit" ? <ArrowDownRight size={16} /> : <ArrowUpRight size={16} />}
                                </span>
                                <div className="flex-1">
                                    <div className="text-sm font-semibold capitalize">{l.reason.replace("_", " ")}</div>
                                    <div className="text-xs text-muted-foreground">
                                        {new Date(l.created_at).toLocaleString("en-IN")}
                                    </div>
                                </div>
                                <div className={`font-bold ${l.type === "credit" ? "text-emerald-600 dark:text-emerald-400" : "text-rose-600 dark:text-rose-400"}`}>
                                    {l.type === "credit" ? "+" : "−"}{l.amount}
                                </div>
                            </li>
                        ))}
                    </ul>
                )}
            </div>
        </div>
    );
}

function Stat({ label, value, accent }) {
    return (
        <div className={`flex-1 rounded-xl px-3 py-2 text-center ${accent ? "bg-primary/10 text-primary" : "bg-secondary/40"}`}>
            <div className="text-lg font-bold leading-none">{value}</div>
            <div className="mt-1 text-[10px] uppercase tracking-widest text-muted-foreground">{label}</div>
        </div>
    );
}

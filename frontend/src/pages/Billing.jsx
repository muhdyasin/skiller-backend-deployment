import { useEffect, useState } from "react";
import { Crown, Check, Sparkles, Lock, Coins } from "lucide-react";
import { api, formatApiError } from "../lib/api";
import { Button } from "../components/ui/button";
import { toast } from "sonner";
import { useAuth } from "../context/AuthContext";

// Inject the Razorpay Checkout JS once and reuse globally.
let _rzpScriptPromise = null;
function loadRazorpay() {
    if (_rzpScriptPromise) return _rzpScriptPromise;
    _rzpScriptPromise = new Promise((resolve, reject) => {
        if (window.Razorpay) return resolve(window.Razorpay);
        const s = document.createElement("script");
        s.src = "https://checkout.razorpay.com/v1/checkout.js";
        s.async = true;
        s.onload = () => resolve(window.Razorpay);
        s.onerror = () => {
            _rzpScriptPromise = null;
            reject(new Error("Could not load Razorpay"));
        };
        document.body.appendChild(s);
    });
    return _rzpScriptPromise;
}

export default function Billing() {
    const { user } = useAuth();
    const [plans, setPlans] = useState([]);
    const [meta, setMeta] = useState({ trial_days: 30, referral_reward_tokens: 500 });
    const [me, setMe] = useState(null);
    const [wallet, setWallet] = useState(null);
    const [loading, setLoading] = useState(true);
    const [paying, setPaying] = useState(false);

    const load = async () => {
        try {
            setLoading(true);
            const [p, m, w] = await Promise.all([
                api.get("/billing/plans"),
                api.get("/billing/me"),
                api.get("/wallet/me"),
            ]);
            setPlans(p.data.plans);
            setMeta({ trial_days: p.data.trial_days, referral_reward_tokens: p.data.referral_reward_tokens });
            setMe(m.data);
            setWallet(w.data.wallet);
        } catch (err) {
            toast.error(formatApiError(err.response?.data?.detail));
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        load();
    }, []);

    const checkout = async (plan_id, pay_with) => {
        try {
            setPaying(true);
            const { data } = await api.post("/billing/checkout", { plan_id, pay_with });

            if (data.status === "paid") {
                toast.success("Subscription active 🎉");
                await load();
                return;
            }
            if (data.status === "mock") {
                toast.message("Coming soon", { description: data.message });
                return;
            }
            if (data.status === "order_created" && data.provider === "razorpay") {
                const Razorpay = await loadRazorpay();
                if (!Razorpay) {
                    toast.error("Could not open Razorpay checkout");
                    return;
                }
                await new Promise((resolve) => {
                    const rzp = new Razorpay({
                        key: data.key_id,
                        amount: data.amount,
                        currency: data.currency,
                        name: "Skiller",
                        description: data.plan_name,
                        order_id: data.order_id,
                        prefill: {
                            name: data.prefill?.name || user?.name || "",
                            email: data.prefill?.email || user?.email || "",
                        },
                        notes: data.notes || {},
                        theme: { color: "#B91C1C" },
                        modal: {
                            ondismiss: () => {
                                toast.message("Checkout closed");
                                resolve();
                            },
                        },
                        handler: async (response) => {
                            try {
                                const verify = await api.post("/billing/verify-payment", {
                                    razorpay_order_id: response.razorpay_order_id,
                                    razorpay_payment_id: response.razorpay_payment_id,
                                    razorpay_signature: response.razorpay_signature,
                                });
                                if (verify.data.status === "paid" || verify.data.status === "already_paid") {
                                    toast.success("Payment verified · subscription active 🎉");
                                    await load();
                                } else {
                                    toast.error("Verification failed");
                                }
                            } catch (err) {
                                toast.error(formatApiError(err.response?.data?.detail) || "Verification failed");
                            } finally {
                                resolve();
                            }
                        },
                    });
                    rzp.on?.("payment.failed", (resp) => {
                        toast.error(`Payment failed: ${resp.error?.description || "unknown"}`);
                        resolve();
                    });
                    rzp.open();
                });
                return;
            }
            toast.message(data.message || "Unknown response");
        } catch (err) {
            toast.error(formatApiError(err.response?.data?.detail));
        } finally {
            setPaying(false);
        }
    };

    if (loading)
        return <div className="py-20 text-center text-muted-foreground" data-testid="billing-loading">Loading plans…</div>;

    const tokenBalance = wallet?.balance || 0;

    return (
        <div className="mx-auto max-w-5xl px-4 py-6" data-testid="billing-page">
            {/* Status hero */}
            <div className={`overflow-hidden rounded-3xl border p-6 md:p-8 ${
                me?.is_premium
                    ? "border-primary/30 bg-gradient-to-br from-primary/15 via-primary/5 to-background"
                    : "border-border bg-secondary/40"
            }`}>
                <div className="flex flex-wrap items-center justify-between gap-4">
                    <div>
                        <div className="text-xs font-bold uppercase tracking-widest text-primary">
                            Your subscription
                        </div>
                        <h1 className="mt-1 font-display text-2xl font-extrabold md:text-3xl" data-testid="billing-status">
                            {me?.is_premium ? (
                                <>Premium · <span className="text-primary">{me.days_left} days left</span></>
                            ) : (
                                "Trial expired"
                            )}
                        </h1>
                        <p className="mt-1 text-sm text-muted-foreground">
                            {me?.is_premium
                                ? `All premium tools unlocked until ${new Date(me.premium_until).toLocaleDateString("en-IN")}.`
                                : "Reactivate with a Skiller Trial Active plan or use your tokens."}
                        </p>
                    </div>
                    <div className="rounded-2xl border border-border bg-background/80 px-4 py-3 text-right">
                        <div className="flex items-center justify-end gap-1.5 text-xs uppercase tracking-widest text-muted-foreground">
                            <Coins size={12} /> Token wallet
                        </div>
                        <div className="font-display text-2xl font-extrabold" data-testid="billing-token-balance">
                            {tokenBalance.toLocaleString("en-IN")}
                        </div>
                    </div>
                </div>
            </div>

            <div className="mt-6 text-xs font-bold uppercase tracking-widest text-muted-foreground">
                Plans
            </div>
            <div className="mt-2 grid grid-cols-1 gap-4 md:grid-cols-3" data-testid="billing-plans">
                {plans.map((p) => (
                    <div
                        key={p.id}
                        className={`relative rounded-2xl border bg-card p-5 ${
                            p.active ? "border-primary shadow-xl" : "border-border opacity-80"
                        }`}
                        data-testid={`billing-plan-${p.id}`}
                    >
                        {p.active && (
                            <span className="absolute -top-2 right-4 rounded-full bg-primary px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-widest text-primary-foreground">
                                Live
                            </span>
                        )}
                        {p.coming_soon && (
                            <span className="absolute -top-2 right-4 inline-flex items-center gap-1 rounded-full bg-secondary px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
                                <Lock size={10} /> Soon
                            </span>
                        )}
                        <div className="flex items-center gap-2 font-display text-lg font-bold">
                            <Crown size={16} className="text-primary" /> {p.name}
                        </div>
                        <div className="mt-3 flex items-baseline gap-1">
                            <span className="font-display text-3xl font-extrabold">₹{p.price_inr.toLocaleString("en-IN")}</span>
                            <span className="text-xs text-muted-foreground">/ {p.duration_days} days</span>
                        </div>
                        <ul className="mt-4 space-y-1.5 text-sm">
                            {p.perks.map((perk) => (
                                <li key={perk} className="flex items-start gap-2">
                                    <Check size={14} className="mt-0.5 shrink-0 text-emerald-500" />
                                    <span>{perk}</span>
                                </li>
                            ))}
                        </ul>
                        <div className="mt-5 grid grid-cols-1 gap-1.5">
                            <Button
                                disabled={!p.active || paying}
                                onClick={() => checkout(p.id, "razorpay")}
                                className="rounded-full"
                                data-testid={`subscribe-razorpay-${p.id}`}
                            >
                                {p.active ? "Pay with Razorpay" : "Coming soon"}
                            </Button>
                            <Button
                                disabled={!p.active || paying || tokenBalance < p.price_inr}
                                variant="outline"
                                onClick={() => checkout(p.id, "tokens")}
                                className="rounded-full"
                                data-testid={`subscribe-tokens-${p.id}`}
                            >
                                <Coins size={12} className="mr-1.5" />
                                Pay with {p.price_inr.toLocaleString("en-IN")} tokens
                            </Button>
                        </div>
                    </div>
                ))}
            </div>

            <div className="mt-6 rounded-2xl border border-dashed border-border bg-secondary/20 p-5 text-sm">
                <div className="flex items-center gap-2 font-semibold">
                    <Sparkles size={14} className="text-primary" /> Refer & earn
                </div>
                <p className="mt-1 text-xs text-muted-foreground">
                    Earn <strong>{meta.referral_reward_tokens} tokens</strong> (≈ ₹{meta.referral_reward_tokens})
                    every time a friend joins via your code and starts a paid subscription. Tokens redeem here.
                </p>
            </div>
        </div>
    );
}

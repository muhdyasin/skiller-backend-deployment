import { Link } from "react-router-dom";
import { Trophy, Flame } from "lucide-react";

export default function XPBadge({ user, compact }) {
    if (!user) return null;
    const xp = user.xp || 0;
    // approximate level computation (server-canonical), used for sidebar widget only
    const thresholds = [
        [0, "Newbie"], [50, "Spark"], [150, "Apprentice"], [350, "Builder"],
        [750, "Maker"], [1500, "Pro"], [3000, "Mentor"], [6000, "Master"], [12000, "Legend"],
    ];
    let idx = 0;
    for (let i = 0; i < thresholds.length; i++) {
        if (xp >= thresholds[i][0]) idx = i;
    }
    const cur = thresholds[idx][0];
    const next = thresholds[idx + 1]?.[0] ?? cur;
    const progress = next === cur ? 1 : Math.min(1, (xp - cur) / (next - cur));
    const name = thresholds[idx][1];

    if (compact) {
        return (
            <Link
                to="/leaderboard"
                className="flex items-center gap-2 rounded-full border border-border px-3 py-1 text-xs hover:bg-accent"
                data-testid="xp-badge-compact"
            >
                <Trophy size={12} className="text-primary" />
                <span className="font-semibold">L{idx + 1}</span>
                <span className="text-muted-foreground">{xp} XP</span>
            </Link>
        );
    }

    return (
        <Link
            to="/leaderboard"
            className="block rounded-2xl border border-border p-3 transition-colors hover:bg-accent"
            data-testid="xp-badge"
        >
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <div className="grid h-8 w-8 place-items-center rounded-lg bg-primary/10 text-primary">
                        <Trophy size={14} />
                    </div>
                    <div>
                        <div className="text-xs uppercase tracking-widest text-muted-foreground">
                            Level {idx + 1}
                        </div>
                        <div className="font-display text-sm font-bold">{name}</div>
                    </div>
                </div>
                {user.streak > 0 && (
                    <div className="flex items-center gap-1 rounded-full border border-border px-2 py-0.5 text-xs">
                        <Flame size={12} className="text-orange-500" /> {user.streak}d
                    </div>
                )}
            </div>
            <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-secondary">
                <div
                    className="h-full rounded-full bg-primary transition-all"
                    style={{ width: `${progress * 100}%` }}
                />
            </div>
            <div className="mt-1.5 flex items-center justify-between text-[10px] text-muted-foreground">
                <span>{xp} XP</span>
                <span>{next} XP</span>
            </div>
        </Link>
    );
}

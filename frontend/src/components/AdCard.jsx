import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { fileSrc } from "../lib/upload";

export default function AdCard({ ad, onClick }) {
    const handleClick = async () => {
        try {
            await api.post(`/ads/${ad.id}/click`);
        } catch {}
        if (ad.cta_url && ad.cta_url !== "#") window.open(ad.cta_url, "_blank");
        onClick?.();
    };
    return (
        <article
            className="overflow-hidden rounded-2xl border border-primary/20 bg-card"
            data-testid={`ad-${ad.id}`}
        >
            <div className="flex items-center justify-between px-4 py-2 text-xs">
                <div className="flex items-center gap-2">
                    <img
                        src={
                            ad.owner_avatar ||
                            `https://api.dicebear.com/9.x/initials/svg?seed=${ad.owner_name || "S"}`
                        }
                        alt=""
                        className="h-7 w-7 rounded-full border border-border object-cover"
                    />
                    <div>
                        <div className="font-semibold">{ad.owner_username}</div>
                        <div className="text-[10px] uppercase tracking-widest text-muted-foreground">
                            Sponsored
                        </div>
                    </div>
                </div>
                <span className="rounded-full border border-primary/40 px-2 py-0.5 text-primary">
                    Ad
                </span>
            </div>
            {ad.media && (
                <img
                    src={fileSrc(ad.media)}
                    alt={ad.title}
                    className="aspect-[4/5] w-full object-cover"
                />
            )}
            <div className="p-4">
                <div className="font-display text-base font-bold">{ad.title}</div>
                {ad.caption && (
                    <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">
                        {ad.caption}
                    </p>
                )}
                <button
                    onClick={handleClick}
                    data-testid={`ad-cta-${ad.id}`}
                    className="mt-3 w-full rounded-full bg-primary py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90"
                >
                    {ad.cta_label || "Learn more"}
                </button>
            </div>
        </article>
    );
}

export function AdRotator() {
    const [ads, setAds] = useState([]);
    useEffect(() => {
        api
            .get("/ads/active?limit=1")
            .then((r) => setAds(r.data))
            .catch(() => {});
    }, []);
    if (!ads.length) return null;
    return <AdCard ad={ads[0]} />;
}

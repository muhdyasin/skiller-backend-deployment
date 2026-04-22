export const Logo = ({ size = "md", withWord = true }) => {
    const dim = size === "lg" ? 40 : size === "sm" ? 24 : 32;
    return (
        <div className="flex items-center gap-2" data-testid="brand-logo">
            <div
                style={{ width: dim, height: dim }}
                className="relative grid place-items-center rounded-[8px] bg-primary text-primary-foreground"
            >
                <span
                    className="font-display font-black"
                    style={{ fontSize: dim * 0.55, lineHeight: 1 }}
                >
                    S
                </span>
                <span className="absolute -right-1 -bottom-1 h-2 w-2 rounded-full bg-foreground" />
            </div>
            {withWord && (
                <span className="font-display text-xl font-extrabold tracking-tight">
                    skiller
                </span>
            )}
        </div>
    );
};

export default Logo;

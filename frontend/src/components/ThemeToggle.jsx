import { useTheme } from "../context/ThemeContext";
import { Sun, Moon } from "lucide-react";

export default function ThemeToggle({ className = "" }) {
    const { theme, toggle } = useTheme();
    return (
        <button
            onClick={toggle}
            data-testid="public-theme-toggle"
            aria-label="Toggle theme"
            className={`grid h-10 w-10 place-items-center rounded-full border border-border hover:bg-accent transition-colors ${className}`}
        >
            {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
        </button>
    );
}

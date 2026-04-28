import { Link } from "react-router-dom";
import { ArrowRight, Sparkles, Upload, BookOpen, Briefcase } from "lucide-react";
import { Logo } from "../components/Logo";
import { Button } from "../components/ui/button";
import { useTheme } from "../context/ThemeContext";
import { Sun, Moon } from "lucide-react";

const features = [
    { icon: Sparkles, title: "Share your craft", desc: "Post reels, carousels, tutorials. Build a following that learns from you." },
    { icon: Upload, title: "Upload any skill", desc: "Images or videos. Tag it. Ship it. Get discovered." },
    { icon: BookOpen, title: "Learn from the best", desc: "Creator-led courses in design, code, product, marketing & more." },
    { icon: Briefcase, title: "Earn from day one", desc: "Freelance gigs and projects matched to your skills." },
];

export default function Landing() {
    const { theme, toggle } = useTheme();
    return (
        <div className="min-h-screen bg-background text-foreground" data-testid="landing-page">
            <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-6">
                <Logo />
                <div className="flex items-center gap-2">
                    <button
                        onClick={toggle}
                        className="grid h-10 w-10 place-items-center rounded-full hover:bg-accent"
                        data-testid="landing-theme-toggle"
                    >
                        {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
                    </button>
                    <Link to="/login">
                        <Button variant="ghost" className="rounded-full" data-testid="landing-signin-btn">
                            Sign in
                        </Button>
                    </Link>
                    <Link to="/register">
                        <Button className="rounded-full" data-testid="landing-getstarted-btn">
                            Get started
                        </Button>
                    </Link>
                </div>
            </header>

            <section className="mx-auto grid max-w-6xl grid-cols-1 gap-12 px-6 pb-16 pt-10 md:grid-cols-2 md:pt-20">
                <div className="flex flex-col justify-center">
                    <span className="mb-4 inline-flex w-fit items-center gap-2 rounded-full border border-border bg-secondary px-3 py-1 text-xs font-semibold uppercase tracking-widest text-muted-foreground">
                        <span className="h-1.5 w-1.5 rounded-full bg-primary" />
                        India's learn-to-earn social network
                    </span>
                    <h1 className="font-display text-4xl font-black leading-[1.05] tracking-tight sm:text-5xl lg:text-6xl">
                        Learn a skill.
                        <br />
                        <span className="text-primary">Earn from it.</span>
                        <br />
                        Repeat.
                    </h1>
                    <p className="mt-6 max-w-lg text-base leading-relaxed text-muted-foreground md:text-lg">
                        Skiller is where creators, learners and freelancers meet. Post your
                        craft, take world-class courses, land real projects — all in one
                        beautifully minimal space.
                    </p>
                    <div className="mt-8 flex flex-wrap items-center gap-3">
                        <Link to="/register">
                            <Button size="lg" className="rounded-full px-6" data-testid="hero-cta-register">
                                Join Skiller <ArrowRight size={18} className="ml-1" />
                            </Button>
                        </Link>
                        <Link to="/home">
                            <Button size="lg" variant="outline" className="rounded-full px-6" data-testid="hero-cta-feed">
                                Explore the feed
                            </Button>
                        </Link>
                    </div>
                    <div className="mt-10 flex items-center gap-6 text-sm text-muted-foreground">
                        <div>
                            <div className="font-display text-2xl font-bold text-foreground">100K+</div>
                            creators
                        </div>
                        <div className="h-6 w-px bg-border" />
                        <div>
                            <div className="font-display text-2xl font-bold text-foreground">5K+</div>
                            gigs live
                        </div>
                        <div className="h-6 w-px bg-border" />
                        <div>
                            <div className="font-display text-2xl font-bold text-foreground">₹2Cr+</div>
                            earned
                        </div>
                    </div>
                </div>

                <div className="relative">
                    <div className="absolute -inset-4 rounded-3xl bg-primary/5 blur-2xl" />
                    <div className="relative grid grid-cols-2 gap-4">
                        <img
                            src="https://images.unsplash.com/photo-1648111320024-3a08e28d20ff?w=800&q=80"
                            alt=""
                            className="col-span-2 h-64 w-full rounded-2xl border border-border object-cover"
                        />
                        <img
                            src="https://images.pexels.com/photos/6446678/pexels-photo-6446678.jpeg?w=600"
                            alt=""
                            className="h-48 w-full rounded-2xl border border-border object-cover"
                        />
                        <img
                            src="https://images.unsplash.com/photo-1519408469771-2586093c3f14?w=600&q=80"
                            alt=""
                            className="h-48 w-full rounded-2xl border border-border object-cover"
                        />
                    </div>
                </div>
            </section>

            <section className="mx-auto max-w-6xl px-6 py-16">
                <h2 className="font-display text-3xl font-bold tracking-tight md:text-4xl">
                    Four things. One place.
                </h2>
                <div className="mt-10 grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
                    {features.map(({ icon: Icon, title, desc }) => (
                        <div
                            key={title}
                            className="group rounded-2xl border border-border p-6 transition-all hover:-translate-y-1 hover:border-primary/40"
                        >
                            <div className="mb-4 grid h-10 w-10 place-items-center rounded-xl bg-primary/10 text-primary">
                                <Icon size={20} />
                            </div>
                            <div className="font-display text-lg font-bold">{title}</div>
                            <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
                                {desc}
                            </p>
                        </div>
                    ))}
                </div>
            </section>

            <footer className="border-t border-border">
                <div className="mx-auto flex max-w-6xl flex-col items-start justify-between gap-4 px-6 py-8 md:flex-row md:items-center">
                    <Logo />
                    <div className="text-sm text-muted-foreground">
                        © {new Date().getFullYear()} Skiller — made for India.
                    </div>
                </div>
            </footer>
        </div>
    );
}

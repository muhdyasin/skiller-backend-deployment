# Skiller — PRD

## Problem Statement (verbatim)
> https://gamma.app/docs/excue4og8dptp7u — Instagram-like learn-to-earn app called Skiller, with upload section, day/night theme, modern minimalist palette.

## Vision
India's learn-to-earn social network. Two distinct experiences in one app: Students discover skills (YouTube-like) + watch reels + take courses + apply for gigs; Creators/Institutions teach + run courses + post gigs + run a CRM + run ads + see insights.

## Implemented (cumulative through Iteration 5 — Feb 2026)

### v1 — Core social MVP (JWT, feed, posts, follow, like, comment, courses, gigs)
### v2 — Object storage, post-detail, in-app notifications, AI recs, dashboard, ads, gamification
### v3 — Realtime WebSocket notifications, password reset, media URL allowlist
### v4 — Resend email integration, web push (VAPID), search, Indian-red brand, full backend refactor
### v5 (this round) — Role split + YouTube-style student experience
- **Sign-up role choice** — Student vs Creator/Institution selector with per-role copy
- **Role-aware navigation** — sidebar dynamically renders Student or Creator nav; mobile bottom-bar matches
- **Student experience** (YouTube-like):
  - `/home` — category-chip filtered grid of video/image cards
  - `/reels` — vertical-scroll reels feed with autoplay, mute toggle, like + comment overlay
  - `/learning` — enrolled courses + applications + XP/streak/badges hub
  - Creator-only routes (`/dashboard`, `/insights`, `/crm`) guarded with redirect → `/home`
- **Creator/Institution experience**:
  - `/dashboard` — stats grid + Posts/Courses/Ads tabs (existing)
  - `/insights` — 30-day mini-charts (posts/likes/comments) + Top 3 posts + Top 3 courses + ads CTR/spend
  - `/crm` — gigs + applicants table with Shortlist/Hire/Reject actions; courses + enrollments table; mailto links
  - Creators can post their own gigs (`POST /api/gigs` + new gig dialog from CRM)
- **Backend role plumbing** — `RegisterIn.role`, `require_creator` dependency, applications now carry `status` (pending/shortlisted/hired/rejected) with notifications on transition
- **Migrations** — legacy `role:"user"` → `student`; demo accounts → `creator`; reel-style video posts seeded; gig owner_id backfilled

## Demo accounts
- Admin: `admin@skiller.app / Admin@123` (admin)
- Creators: `maya@skiller.app`, `arjun@skiller.app`, `neha@skiller.app` — all `Demo@123`
- New users default to **student** unless they pick "Creator/Institution" at signup
- "Become a creator" button on student profile for one-click upgrade

## Testing
- 122/122 backend pytest passing
- 15/16 frontend e2e initially → fixed creator login redirect → 16/16

### v6 (this round — Feb 2026) — Storefront + Search Scale + Hygiene
- **Per-creator public storefront** at `/c/<username>` (SEO-friendly) — backed by new `GET /api/c/<username>` returning user, stats, level, badges, courses (with enrollment counts), gigs, reels, posts. Hero, follow/share buttons, tabbed catalogue (Courses / Gigs / Reels / Posts), and "Discover more creators" CTA. Open to anonymous visitors.
- Profile page `/u/<username>` now exposes a "View storefront →" link for creators.
- **Mongo text search indexes** (`users_text_idx`, `posts_text_idx`, `courses_text_idx`, `gigs_text_idx`) with hybrid `$text` → regex fallback for partial typeahead queries (in `routers/search.py`).
- **TTL index** on `password_reset_tokens.expires_at_dt` (`expireAfterSeconds=0`) — Mongo auto-deletes expired reset tokens. `forgot_password` now writes both string and datetime fields for compat.
- Compound indexes added: `posts(user_id, created_at)`, `courses(owner_id, created_at)`, `gigs(owner_id, created_at)`, `enrollments(course_id)`, `applications(gig_id)`.
- **SearchBar testid disambiguated** — `search-input` removed; `search-input-mobile` + `search-input-desktop` (and matching clear-btn variants) — based on `compact` prop.

### v7 (this round — May 2026) — Subscription · Tokens · Stories · Community · SEO
- **Free 30-day trial** on every account: `premium_until = signup + 30d`, `plan = "trial"`. Backfilled for all existing users in `seed.py`.
- **Trial badge** in sidebar + mobile topbar that links to `/billing`; turns amber within 7 days, rose-red on expiry.
- **`/billing` page** with single ACTIVE plan (`Skiller Trial Active` ₹299 / 30d), plus locked previews for Quarterly + Yearly. Razorpay/Stripe checkout returns `status=mock` until keys are wired; tokens-checkout (1 token = ₹1) goes live now and extends `premium_until`.
- **Skill-token wallet** with idempotent ledger (`db.token_wallets`, `db.token_ledger`). Endpoints: `/api/wallet/me`, `/api/wallet/redeem` (purposes: `course`, `ads`, `ai_credits`), `/api/wallet/referral-link`.
- **Referral system** — every user gets an 8-char `referral_code`. New users register with `?ref=CODE`; row created in `db.referrals` with `status=pending`. On the referred user's first paid (token) checkout, referrer is credited 500 tokens and status flips to `rewarded`.
- **Stories** (Instagram-style) — `db.stories` with TTL index (24h). `StoryBar` component above `/home` and `/feed`; full-screen `StoryViewer` with progress segments, tap-zone navigation, view-tracking, and 24h-expiry display.
- **Community / WhatsApp clone** (no status bar) — `/community` list + `/community/:groupId` chat. Supports DMs (idempotent — same pair always returns same group) and groups (admins, member-mgmt). Messages: text, image, share. Reactions toggle (one emoji per user with auto-swap), read receipts (double-tick turns blue when others read), typing indicators (WebSocket-broadcast). Real-time via existing `ws_manager`.
- **SEO** — `react-helmet-async` per-page meta on Landing / Storefront / PostDetail. Dynamic OG title, description, image, JSON-LD (Person, Course offers). Strong site-wide defaults in `index.html`. Backend `/api/sitemap.xml` (lists creators + key pages) + `/api/og/c/{username}` (crawler-friendly metadata) + `/robots.txt` + `/sitemap.xml` redirect.
- **3 P1 quick wins**: (a) `/api/search` parallelized via `asyncio.gather` (4 collection lookups concurrent); (b) `PASSWORD_RESET_LINK` log gated behind `APP_ENV != "production"`; (c) backend cleanup of unused-var lint warnings.

## Testing
- 159/159 backend pytest passing (18 new iter7 tests + 141 prior)
- iter7 frontend smoke verified manually; full Playwright sweep pending next agent run.

## Backlog
- P1: `RESEND_API_KEY` to enable real password-reset email delivery (currently logs link to backend log when APP_ENV != "production")
- P1: Razorpay primary + Stripe fallback wiring once keys are provided — replace `status=mock` checkout with real charges
- P1: Migrate auth tokens from `localStorage` → `httpOnly` Secure cookies (XSS protection). Auth playbook trip required first.
- P2: Voice notes in chat, group avatars upload UI, group settings page (rename/leave)
- P2: Email verification on signup
- P2: Server-side rendering for `/c/<username>` so WhatsApp/Slack unfurls work without JS-aware crawlers (currently only Google/LinkedIn read JS-rendered Helmet tags)
- P2: Course detail page + per-course OG (currently only catalogue list)
- P2: Post detail OG image generation (current uses raw media)

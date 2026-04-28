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

## Testing
- 141/141 backend pytest passing (19 new iter6 tests + 122 prior)
- Frontend storefront flow + tab navigation + search-id uniqueness verified at 1920×1080 and 390×844 viewports.

## Backlog
- P1: `RESEND_API_KEY` to enable real password-reset email delivery (currently logs link to backend log)
- P1: Migrate auth tokens from `localStorage` → `httpOnly` Secure cookies (XSS protection). Auth playbook trip required first.
- P1: Gate `PASSWORD_RESET_LINK` info-log behind `APP_ENV != production` (carry-over from iter4)
- P1: Parallelize `/api/search` collection lookups with `asyncio.gather` to halve p95 latency
- P2: Stripe / Razorpay course checkout (revenue!)
- P2: DM messaging
- P2: Email verification on signup
- P2: OG/Twitter meta tags on `/c/<username>` for actual link unfurls (server-rendered or react-helmet)

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

### v7 (Feb 2026) — Subscription · Tokens · Stories · Community · SEO
- **Free 30-day trial** per account (`premium_until = signup + 30d`, `plan="trial"`). Backfilled for all existing users.
- **Trial badge** in sidebar + mobile topbar; amber ≤7d left, rose on expiry.
- **`/billing` page** with `Skiller Trial Active` ₹299/30d (ACTIVE) + locked Quarterly/Yearly previews. Razorpay/Stripe return `status=mock`; tokens-checkout is live.
- **Skill-token wallet** (`db.token_wallets` + `db.token_ledger`). Endpoints: `/api/wallet/me`, `/api/wallet/redeem` (course/ads/ai_credits), `/api/wallet/referral-link`.
- **Referral system** — 8-char codes, `?ref=` capture on signup, **500 tokens** on referee's first paid subscription.
- **Stories** (Instagram-style) with 24h TTL. `StoryBar` on `/home` + `/feed`; full-screen viewer with progress segments, tap-nav, view tracking.
- **Community / WhatsApp clone (no status bar)** — `/community` + `/community/:id` chat. DMs (idempotent) + groups. Text/image/share messages, toggle reactions, blue double-tick read receipts, typing indicators via WebSocket.
- **SEO** — react-helmet-async per-page meta (Landing, Storefront, Post). JSON-LD. `/api/sitemap.xml`, `/api/og/c/{u}`, `robots.txt`.
- **3 quick wins** — parallel `/api/search` (asyncio.gather), APP_ENV-gated dev log, lint cleanup.

### v8 (May 2026) — Voice Notes · Group Settings · Email Verification · SSR Unfurls
- **Email verification (non-blocking)** — new users get `email_verified=false`, receive a verification email (+dev-log link when APP_ENV != production). `/api/auth/verify-email` awards **+25 XP** on success. `/api/auth/resend-verification` with 60s rate-limit. New `/verify-email/:token` page. Global `VerifyEmailBanner` mounts in Layout above all authenticated content (dismissible). Demo users pre-verified.
- **Voice notes in chat** — `VoiceRecorder` component (MediaRecorder API, 2-min cap, waveform preview, discard/send) + `VoiceMessage` playback bubble. `type="voice"` messages persist with `duration_ms`; last-message-preview shows "🎤 Voice note".
- **Group settings UI** — `GroupSettings` dialog (opened from chat header) with rename, description, avatar upload, member add (username input), per-member remove (admin only), leave-group / close-DM. DMs show only "Close chat" (no rename/avatar/members list).
- **SSR OG wrappers for social unfurls** — `/api/share/c/{u}`, `/api/share/u/{u}`, `/api/share/p/{id}` return fully server-rendered HTML with complete OG/Twitter/canonical tags + meta-refresh redirect. WhatsApp/Slack/LinkedIn/iMessage unfurls now show proper preview cards. Storefront Share button emits this URL.
- **Fixed** React 18 StrictMode double-dispatch bug on VerifyEmail — single-shot `useRef` guard + `/auth/me` fallback check.

## Testing
- **179/179 backend pytest passing** (20 new iter8 + 159 prior)
- Frontend: verify-email flow, resend/close banner, group settings, voice recorder mic button, storefront share URL, SSR wrappers all verified by testing_agent_v3 + manual Playwright.

### v9 (this round — May 2026) — Razorpay LIVE (test mode) checkout
- **Razorpay Standard Checkout** wired end-to-end on the `Skiller Trial Active` ₹299 / 30d plan.
  - Backend `POST /api/billing/checkout` with `pay_with=razorpay` creates a real Razorpay Order via `client.order.create({amount, currency, receipt, payment_capture, notes})` and returns `key_id + order_id + amount + currency + plan_name + prefill` to the client.
  - Frontend lazily loads `https://checkout.razorpay.com/v1/checkout.js` once, opens the modal with handler-based flow, prefills name+email, theme=#B91C1C.
  - `POST /api/billing/verify-payment` performs `hmac.compare_digest` on `HMAC-SHA256(order_id|payment_id, secret)` server-side. Invalid signature → 400. Valid → extends `premium_until`, flips `plan='pro'`, fires referral reward, persists `subscription_events`.
  - **Idempotent**: re-verifying the same order_id+payment_id returns `status='already_paid'` (no double-credit).
- Stripe checkout remains mock until Stripe keys arrive.
- **186/186 backend pytest** pass (7 new iter9).

## Backlog
- P1: `RESEND_API_KEY` to deliver real verification & password-reset emails (currently logs when APP_ENV != production)
- P1: Stripe Key ID + Secret → flip Stripe checkout from mock to live (international cards)
- P1: Razorpay webhook endpoint (`POST /api/billing/razorpay-webhook`) for server-side guarantee on payment.captured (currently we trust handler callback). Needs `RAZORPAY_WEBHOOK_SECRET`.
- P1: httpOnly Secure cookie migration for JWT (XSS hardening) — auth playbook trip required
- P2: Voice recorder fallback for browsers without MediaRecorder (iOS Safari < 14.5)
- P2: OG image generator (e.g. 1200×630 dynamic PNG with Indian Red brand frame + name/avatar overlay) for richer unfurls
- P2: Crawl-friendly static sitemap at root `/sitemap.xml` (currently redirects to `/api/sitemap.xml`)
- P2: Stories reactions + views list (who viewed my story)
- P2: Quarterly + Yearly plans flip to active once you decide pricing

## Backlog
- P1: `RESEND_API_KEY` to enable real password-reset email delivery (currently logs link to backend log when APP_ENV != "production")
- P1: Razorpay primary + Stripe fallback wiring once keys are provided — replace `status=mock` checkout with real charges
- P1: Migrate auth tokens from `localStorage` → `httpOnly` Secure cookies (XSS protection). Auth playbook trip required first.
- P2: Voice notes in chat, group avatars upload UI, group settings page (rename/leave)
- P2: Email verification on signup
- P2: Server-side rendering for `/c/<username>` so WhatsApp/Slack unfurls work without JS-aware crawlers (currently only Google/LinkedIn read JS-rendered Helmet tags)
- P2: Course detail page + per-course OG (currently only catalogue list)
- P2: Post detail OG image generation (current uses raw media)

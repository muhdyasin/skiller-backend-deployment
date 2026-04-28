# Skiller — PRD

## Problem Statement (verbatim)
> https://gamma.app/docs/excue4og8dptp7u — Instagram-like learn-to-earn app called Skiller, with upload section, day/night theme, modern minimalist palette.

## Vision
India's Instagram-style learn-to-earn social network. Creators post skill content, run paid courses, run ads; learners discover, follow, level up via XP/badges, and apply for freelance gigs.

## Implemented (cumulative, Iter 1 → 4 — Feb 2026)

### v1 — Core social MVP
- JWT auth, feed, upload (base64), profiles, follow, like, comment
- Courses + Gigs (browse + apply), day/night theme, sidebar/bottom-nav

### v2 — Polish + monetisation hooks
- Public theme toggle on Login/Register
- Object storage (Emergent storage API): POST /api/upload + GET /api/files/{path}
- Post-detail page (/p/:id), in-app notifications (bell + page)
- AI recommendations (Claude Sonnet 4.5)
- Creator/Institution Dashboard with Posts/Courses/Ads CRUD
- Gamification: XP, 9 levels, 10 badges, daily streaks, leaderboard

### v3 — Realtime + security
- Real-time WebSocket notifications (replaces 25s polling)
- Tighter media URL allowlist on POST /api/posts (https/http or /api/files/)
- Dashboard data-testids
- Password reset flow (forgot-password + reset-password) — dev-mode console log

### v4 — Email, Push, Search, Refactor, Brand
- **Email** — `/api/auth/forgot-password` wired to Resend with HTML template (falls back to console log if `RESEND_API_KEY` empty)
- **Web Push notifications** — Service Worker (`/sw.js`) + auto-generated VAPID keys (persisted in MongoDB); `ensurePushSubscription()` gracefully no-ops when permission denied
- **Backend refactor** — `server.py` split into `core.py`, `notifications_service.py`, `seed.py`, and `routers/` (auth, users, posts, courses, gigs, ads, dashboard, ai, notifications, files, ws, search, push)
- **Search bar** — `/api/search?q=` returns users + posts + courses + gigs; debounced dropdown in top header on every page; dedicated `/search` page
- **Brand color** — primary changed from blue to **Indian red** (`#B91C1C` light / `#DC2626` dark)

## Testing
- 80/80 backend pytest passing across all four iterations
- 100% frontend e2e passing
- Manual WebSocket test (`/tmp/ws_test.py`) confirms realtime notifications

## Backlog
- P1: Set `RESEND_API_KEY` (user to provide) so password-reset emails actually deliver
- P1: Add Mongo text indexes for /api/search to scale beyond seed-sized data
- P1: TTL index on `password_reset_tokens.expires_at`
- P2: Stripe / Razorpay course checkout (revenue!)
- P2: Stories / reels
- P2: DM messaging
- P2: Email verification on signup

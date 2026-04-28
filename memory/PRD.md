# Skiller — PRD

## Problem Statement (verbatim)
> https://gamma.app/docs/excue4og8dptp7u — create the fully functional front end and backend with upload section, day and night theme, Instagram-like UI. App name: Skiller. Modern minimalist blue/white/black palette.

## Vision
Skiller is India's Instagram-like learn-to-earn social network. Learners share skill content, discover courses, apply for freelance gigs, level up via XP/badges, and creators run their own ads — all in one place.

## Implemented (cumulative through Iteration 3 — Feb 2026)

### v1
- JWT auth, feed, upload, profiles, follow, like, comment
- Courses + Gigs (browse + apply)
- Day/night theme + sidebar/bottom-nav layout

### v2
- Public theme toggle on Login + Register
- Object storage via Emergent storage API (POST /api/upload, GET /api/files/{path})
- Post-detail page (/p/:id)
- In-app notifications (bell + page)
- AI recommendations (Claude Sonnet 4.5)
- Creator/Institution Dashboard with Posts/Courses/Ads CRUD
- Gamification: XP, 9 levels, 10 badges, daily streaks, leaderboard

### v3 (this round)
- **Real-time WebSocket notifications** — `/api/ws?token=<jwt>` with auto-reconnect + ping/pong; replaces 25 s polling; toast pop-up on each new notification
- **Media URL allowlist** — POST /api/posts now rejects `data:`, `javascript:`, empty, and other schemes; only `https://`, `http://`, or `/api/files/` accepted
- **Dashboard data-testids** — `dashboard-tab-overview/posts/courses/ads`, `dashboard-stats-grid`, `ad-slot`
- **Password reset flow** — `/api/auth/forgot-password` (no enumeration; logs reset link to backend in dev) and `/api/auth/reset-password` with 1-hr token expiry; `/forgot-password` and `/reset-password/:token` pages on frontend; "Forgot password?" link on Login

## Testing
- 52/52 backend pytest passing across iterations 1-3
- 100% frontend e2e passing
- Manual WS test (`/tmp/ws_test.py`) confirms realtime delivery
- Credentials: see `/app/memory/test_credentials.md`

## Backlog
- P1: Wire forgot-password to a real email provider (Resend / SendGrid) when user provides API key
- P1: Web Push notifications (service worker + VAPID) for browser-level push when tab is closed
- P2: Stripe / Razorpay course checkout
- P2: Stories / reels
- P2: DM messaging
- P2: Search (users, posts, hashtags)
- P2: Refactor server.py into routers (auth, posts, users, courses, gigs, ads, dashboard, ws)

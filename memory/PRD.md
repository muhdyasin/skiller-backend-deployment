# Skiller — PRD

## Problem Statement (verbatim)
> https://gamma.app/docs/excue4og8dptp7u — create the fully functional front end and backend with upload section, day and night theme, Instagram-like UI. App name: Skiller. Modern minimalist blue/white/black palette.

## Vision
Skiller is India's Instagram-like learn-to-earn social network. Learners share skill content, discover courses, apply for freelance gigs, level up via XP/badges, and creators run their own ads — all in one place.

## User Personas
- Learner: discovers skills, follows creators, takes courses, lands gigs, levels up.
- Creator / Mentor: posts content, runs courses, runs ads, builds audience.
- Institution: posts long-form courses + ads to reach learners.

## Implemented (v2 — Feb 2026)

### v1 (already shipped)
- JWT auth, feed, upload, profiles, follow, like, comment
- Courses + Gigs (browse + apply)
- Day/night theme + sidebar/bottom-nav layout

### v2 (this round)
- **Public theme toggle** on Login + Register
- **Object storage** (Emergent storage API) for images + videos via `/api/upload` and `/api/files/{path}` with content-type aware streaming
- **Post-detail page** (`/p/:postId`) — full media, comments, like
- **In-app notifications** — bell with badge, dropdown, dedicated page; auto-generated on like/comment/follow/badge
- **AI recommendations** (Claude Sonnet 4.5 via emergentintegrations) — `/api/ai/recommend` returns personalised courses/gigs/creators with reasoning; rendered as Smart Picks in feed sidebar
- **Creator/Institution Dashboard** (`/dashboard`) — stats overview, posts management, courses CRUD, ad campaigns CRUD with pause/resume + impressions/clicks/CTR/spend
- **Ads** — Sponsored card injected in feed; click tracking; impressions auto-increment on serve
- **Gamification (XP / Levels / Badges / Streaks)**
  - 9 levels: Newbie → Spark → Apprentice → Builder → Maker → Pro → Mentor → Master → Legend
  - 10 badges: First Post, Creator, Liked, Beloved, Conversationalist, Connector, Earner, Scholar, On Fire (3-day streak), Week Warrior (7-day streak)
  - XP awarded for posts (20), comments (5/3), likes (1/2), follow (1/5), course enroll (10), gig apply (15), daily login (5)
  - Leaderboard page with top creators sorted by XP

## Testing
- 36/36 backend pytest passing (iter 1: 17, iter 2: 19)
- 100% frontend e2e passing
- See `/app/memory/test_credentials.md`

## Backlog
- P1: Real-time notifications (WebSocket / SSE) instead of 25s polling
- P1: Rich post detail with permalink share, OG tags
- P1: Media validation on POST /api/posts (only allow /api/files/ or https URLs)
- P2: Stripe / Razorpay course checkout (revenue!)
- P2: Stories / short-form video reels
- P2: DM messaging
- P2: Email + push notifications
- P2: Email verification + password reset flow
- P2: Search (users, posts, hashtags)

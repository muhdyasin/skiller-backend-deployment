# Skiller — PRD

## Problem Statement (verbatim)
> https://gamma.app/docs/excue4og8dptp7u — create the fully functional front end and backend with upload section, day and night theme, Instagram-like UI. App name: Skiller. Modern minimalist blue/white/black palette.

## Vision
Skiller is India's Instagram-like learn-to-earn social network. Learners share skill content, discover courses, and apply for freelance gigs — all in one place.

## User Personas
- **Learner**: wants to discover skills, follow creators, take courses, and land gigs.
- **Creator / Mentor**: posts skill content, teaches via courses, grows a following.
- **Freelancer**: browses and applies for gigs matching their skills.

## Core Requirements (static)
- Instagram-like feed, upload, profiles, follow, like, comment
- Courses listing with filters + enroll CTA
- Gigs listing with filters + apply dialog
- Email/password JWT auth with seeded demo accounts
- Day/night theme toggle (blue/white/black palette)
- Mobile bottom nav + desktop left sidebar
- Cabinet Grotesk display font + Satoshi body font

## Implemented (v1 — Feb 2026)
- **Backend (FastAPI + MongoDB)**
  - `/api/auth/register`, `/api/auth/login`, `/api/auth/me` (JWT + bcrypt)
  - `/api/posts` CRUD + `/feed`, `/explore`, `/like`, `/comments`
  - `/api/users/{username}`, `/api/users/{id}/follow`, `PATCH /api/users/me`
  - `/api/courses`, `/api/gigs`, `/api/gigs/{id}/apply`
  - Auto-seed: admin + 3 demo users + 6 posts + 4 courses + 5 gigs
- **Frontend (React + Tailwind + shadcn)**
  - Landing page (hero, stats, feature grid)
  - Auth (Login + Register with split-image layout)
  - Main Layout (sidebar + mobile bottom nav + theme toggle)
  - Feed, Explore, Upload (base64), Profile (+ edit), Courses, Gigs (+ apply dialog)
  - Day/night theme toggle with persistence
- **Testing**: 17/17 backend pytest passing, full frontend e2e passing

## Test credentials
See `/app/memory/test_credentials.md`.

## Backlog (P0 → P2)
- **P1**: Public theme toggle on Landing/Login pages
- **P1**: Server-side media size/MIME validation on `/api/posts`
- **P1**: Object storage integration for media (replace base64)
- **P1**: Individual Post detail page (permalink, full comments)
- **P2**: Stories / short-form video player
- **P2**: In-app notifications (follow, like, comment)
- **P2**: AI-powered skill recommendations (Emergent LLM key)
- **P2**: Stripe / Razorpay integration for course enrollment
- **P2**: Messaging (DM) between learners & creators
- **P2**: Creator analytics dashboard
- **P2**: Email verification + password reset flow

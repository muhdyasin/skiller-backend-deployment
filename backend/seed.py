"""Database seed (admin + demo users + posts + courses + gigs)."""
import os
import uuid
from core import db, now_iso, hash_password, verify_password

from seed_subscription_plans import seed_subscription_plans

DEMO_AVATARS = [
    "https://images.unsplash.com/photo-1560250097-0b93528c311a?w=400&q=80",
    "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=400&q=80",
    "https://images.unsplash.com/photo-1573497019940-1c28c88b4f3e?w=400&q=80",
    "https://images.pexels.com/photos/10657877/pexels-photo-10657877.jpeg?w=400",
]
DEMO_POST_IMAGES = [
    "https://images.pexels.com/photos/6446678/pexels-photo-6446678.jpeg?w=1200",
    "https://images.unsplash.com/photo-1648111320024-3a08e28d20ff?w=1200&q=80",
    "https://images.unsplash.com/photo-1519408469771-2586093c3f14?w=1200&q=80",
    "https://images.pexels.com/photos/8546798/pexels-photo-8546798.jpeg?w=1200",
    "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=1200&q=80",
    "https://images.unsplash.com/photo-1461749280684-dccba630e2f6?w=1200&q=80",
]
DEMO_COURSE_IMAGES = [
    "https://images.unsplash.com/photo-1519408469771-2586093c3f14?w=1200&q=80",
    "https://images.pexels.com/photos/8546798/pexels-photo-8546798.jpeg?w=1200",
    "https://images.unsplash.com/photo-1498050108023-c5249f4df085?w=1200&q=80",
    "https://images.unsplash.com/photo-1517180102446-f3ece451e9d8?w=1200&q=80",
]


async def seed():
    await db.users.create_index("email", unique=True)
    await db.users.create_index("username", unique=True)
    await db.users.create_index("xp")
    await db.posts.create_index([("created_at", -1)])
    await db.posts.create_index([("user_id", 1), ("created_at", -1)])
    await db.notifications.create_index([("user_id", 1), ("created_at", -1)])
    await db.password_reset_tokens.create_index("token", unique=True)

    await seed_subscription_plans()

    # TTL index — Mongo auto-deletes expired tokens. expireAfterSeconds=0
    # uses the value of `expires_at` itself as the deletion timestamp.
    # Drop any pre-existing non-TTL index on expires_at first so we can recreate it.
    try:
        existing = await db.password_reset_tokens.index_information()
        if "expires_at_1" in existing and "expireAfterSeconds" not in existing["expires_at_1"]:
            await db.password_reset_tokens.drop_index("expires_at_1")
    except Exception:
        pass
    await db.password_reset_tokens.create_index("expires_at_dt", expireAfterSeconds=0)
    await db.files.create_index("storage_path")
    await db.ad_campaigns.create_index([("status", 1), ("created_at", -1)])
    await db.push_subscriptions.create_index("subscription.endpoint", unique=True)
    await db.push_subscriptions.create_index([("user_id", 1), ("active", 1)])
    await db.courses.create_index([("owner_id", 1), ("created_at", -1)])
    await db.gigs.create_index([("owner_id", 1), ("created_at", -1)])
    await db.enrollments.create_index([("course_id", 1)])
    await db.applications.create_index([("gig_id", 1)])

    # Text indexes — power /api/search beyond regex full-scans.
    # MongoDB allows only ONE text index per collection, so we set them up
    # idempotently and ignore "already exists" errors.
    text_specs = [
        ("users", [("username", "text"), ("name", "text"), ("bio", "text")]),
        ("posts", [("caption", "text"), ("tags", "text")]),
        ("courses", [("title", "text"), ("description", "text"), ("category", "text"), ("instructor", "text")]),
        ("gigs", [("title", "text"), ("description", "text"), ("category", "text"), ("skills", "text")]),
    ]
    for coll, spec in text_specs:
        try:
            await db[coll].create_index(spec, name=f"{coll}_text_idx", default_language="english")
        except Exception:
            # Conflicting/old text index — keep current one rather than crash startup.
            pass

    # ---- v6: token wallet, referrals, subscriptions ----
    await db.token_wallets.create_index("user_id", unique=True)
    await db.token_ledger.create_index([("user_id", 1), ("created_at", -1)])
    await db.referrals.create_index([("referrer_id", 1), ("created_at", -1)])
    await db.referrals.create_index("referred_user_id", unique=True)
    await db.subscription_events.create_index([("user_id", 1), ("created_at", -1)])
    await db.users.create_index("referral_code", unique=True, sparse=True)

    # ---- v6: stories (TTL 24h) ----
    await db.stories.create_index([("user_id", 1), ("created_at", -1)])
    try:
        existing = await db.stories.index_information()
        if "expires_at_dt_1" in existing and "expireAfterSeconds" not in existing["expires_at_dt_1"]:
            await db.stories.drop_index("expires_at_dt_1")
    except Exception:
        pass
    await db.stories.create_index("expires_at_dt", expireAfterSeconds=0)

    # ---- v6: community groups + messages ----
    await db.groups.create_index([("members", 1), ("last_message_at", -1)])
    await db.group_messages.create_index([("group_id", 1), ("created_at", -1)])

    # ---- v7: email verification tokens (TTL 7d) ----
    await db.email_verification_tokens.create_index("token", unique=True)
    try:
        existing = await db.email_verification_tokens.index_information()
        if "expires_at_dt_1" in existing and "expireAfterSeconds" not in existing["expires_at_dt_1"]:
            await db.email_verification_tokens.drop_index("expires_at_dt_1")
    except Exception:
        pass
    await db.email_verification_tokens.create_index("expires_at_dt", expireAfterSeconds=0)
    # Demo + admin accounts are pre-verified so they skip the nag
    await db.users.update_many(
        {"email": {"$in": ["admin@skiller.app", "maya@skiller.app", "arjun@skiller.app", "neha@skiller.app"]}},
        {"$set": {"email_verified": True}},
    )
    # default others to unverified
    await db.users.update_many(
        {"email_verified": {"$exists": False}}, {"$set": {"email_verified": False}},
    )

    # ---- v6: backfill — referral codes, trial, wallet for existing users ----
    from datetime import timedelta as _td
    import secrets as _sec
    async for u in db.users.find({"referral_code": {"$in": [None, ""]}}, {"id": 1}):
        for _ in range(5):
            code = _sec.token_urlsafe(6).replace("-", "").replace("_", "")[:8].upper()
            if not await db.users.find_one({"referral_code": code}):
                break
        await db.users.update_one({"id": u["id"]}, {"$set": {"referral_code": code}})
    async for u in db.users.find({"premium_until": {"$exists": False}}, {"id": 1, "created_at": 1}):
        from datetime import datetime as _dt, timezone as _tz
        try:
            ca = _dt.fromisoformat(u["created_at"]) if isinstance(u.get("created_at"), str) else u.get("created_at") or _dt.now(_tz.utc)
            if ca.tzinfo is None:
                ca = ca.replace(tzinfo=_tz.utc)
        except Exception:
            ca = _dt.now(_tz.utc)
        until = max(ca + _td(days=30), _dt.now(_tz.utc) + _td(days=30))
        await db.users.update_one({"id": u["id"]}, {"$set": {"premium_until": until.isoformat(), "plan": "trial"}})
    async for u in db.users.find({}, {"id": 1}):
        if not await db.token_wallets.find_one({"user_id": u["id"]}):
            await db.token_wallets.insert_one({
                "user_id": u["id"], "balance": 0,
                "lifetime_earned": 0, "lifetime_spent": 0,
                "created_at": now_iso(), "updated_at": now_iso(),
            })

    await db.users.update_many(
        {"xp": {"$exists": False}},
        {"$set": {"xp": 0, "badges": [], "streak": 0, "last_login_date": None}},
    )

    # Migrate role: legacy "user" -> "student"
    await db.users.update_many({"role": "user"}, {"$set": {"role": "student"}})
    # Promote demo accounts to "creator"
    await db.users.update_many(
        {"email": {"$in": ["maya@skiller.app", "arjun@skiller.app", "neha@skiller.app"]}},
        {"$set": {"role": "creator"}},
    )

    # Backfill ownership on legacy gigs/courses that pre-date the role split
    creator_emails = {
        "maya@skiller.app": "maya",
        "arjun@skiller.app": "arjun",
        "neha@skiller.app": "neha",
    }
    creator_lookup = {}
    async for u in db.users.find(
        {"email": {"$in": list(creator_emails)}}, {"id": 1, "email": 1, "username": 1, "name": 1}
    ):
        creator_lookup[u["username"]] = u
    admin_doc = await db.users.find_one({"role": "admin"}, {"_id": 0, "id": 1, "username": 1, "name": 1})

    # Map gig titles → owner usernames
    gig_owner_map = {
        "Landing page in React + Tailwind": "admin",
        "Logo + Brand identity for D2C brand": "maya",
        "Instagram content calendar (30 days)": "maya",
        "Python automation for lead scraping": "arjun",
        "Product strategy consulting (4 hrs)": "neha",
    }
    async for g in db.gigs.find({"owner_id": {"$exists": False}}):
        owner = gig_owner_map.get(g.get("title"), "admin")
        if owner == "admin" and admin_doc:
            update = {
                "owner_id": admin_doc["id"],
                "owner_username": admin_doc["username"],
                "owner_name": admin_doc["name"],
            }
        elif owner in creator_lookup:
            u = creator_lookup[owner]
            update = {"owner_id": u["id"], "owner_username": u["username"], "owner_name": u["name"]}
        else:
            continue
        await db.gigs.update_one({"id": g["id"]}, {"$set": update})

    # Backfill course owner_id by instructor name
    instructor_to_username = {
        "Maya Sharma": "maya",
        "Arjun Verma": "arjun",
        "Neha Iyer": "neha",
    }
    async for c in db.courses.find({"owner_id": {"$in": [None, ""]}}):
        owner_username = instructor_to_username.get(c.get("instructor"))
        if owner_username and owner_username in creator_lookup:
            await db.courses.update_one(
                {"id": c["id"]},
                {"$set": {"owner_id": creator_lookup[owner_username]["id"]}},
            )

    # Add reel-style video posts if none exist
    if await db.posts.count_documents({"media_type": "video"}) == 0:
        reel_posts = [
            ("maya", "Quick design tip: spacing system in 3 numbers.", "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4", ["design", "tip", "reel"]),
            ("arjun", "Speed-coding a button component. React + Tailwind, no library.", "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerJoyrides.mp4", ["code", "react", "reel"]),
            ("neha", "PM frameworks in 60 seconds — RICE prioritisation.", "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerFun.mp4", ["product", "pm", "reel"]),
        ]
        for username, caption, media, tags in reel_posts:
            user = creator_lookup.get(username)
            if not user:
                continue
            await db.posts.insert_one({
                "id": str(uuid.uuid4()),
                "user_id": user["id"],
                "caption": caption,
                "media": media,
                "media_type": "video",
                "tags": tags,
                "likes": [],
                "comments": [],
                "created_at": now_iso(),
            })

    admin_email = os.environ.get("ADMIN_EMAIL", "admin@skiller.app")
    admin_pw = os.environ.get("ADMIN_PASSWORD", "Admin@123")
    existing = await db.users.find_one({"email": admin_email})
    if not existing:
        await db.users.insert_one({
            "id": str(uuid.uuid4()), "email": admin_email, "username": "admin",
            "name": "Skiller Admin", "password_hash": hash_password(admin_pw),
            "bio": "Official Skiller team account.", "avatar_url": DEMO_AVATARS[0],
            "followers": [], "following": [], "role": "admin",
            "xp": 0, "badges": [], "streak": 0, "last_login_date": None,
            "created_at": now_iso(),
        })
    elif not verify_password(admin_pw, existing["password_hash"]):
        await db.users.update_one({"email": admin_email}, {"$set": {"password_hash": hash_password(admin_pw)}})

    demo_users = [
        ("maya@skiller.app", "maya", "Maya Sharma", "UI/UX designer · Bangalore. Turning ideas into pixels.", DEMO_AVATARS[1]),
        ("arjun@skiller.app", "arjun", "Arjun Verma", "Full-stack dev · Freelancer · Teaching React on Skiller.", DEMO_AVATARS[3]),
        ("neha@skiller.app", "neha", "Neha Iyer", "Product manager · Ex-Razorpay · Writing about 0→1.", DEMO_AVATARS[2]),
    ]
    user_ids = {}
    for email, username, name, bio, avatar in demo_users:
        u = await db.users.find_one({"email": email})
        if not u:
            uid = str(uuid.uuid4())
            await db.users.insert_one({
                "id": uid, "email": email, "username": username, "name": name,
                "password_hash": hash_password("Demo@123"),
                "bio": bio, "avatar_url": avatar,
                "followers": [], "following": [], "role": "user",
                "xp": 0, "badges": [], "streak": 0, "last_login_date": None,
                "created_at": now_iso(),
            })
            user_ids[username] = uid
        else:
            user_ids[username] = u["id"]

    if await db.posts.count_documents({}) == 0:
        demo_posts = [
            ("maya", "Shipped a new design system today. Reds and whites — clean, calm, scalable.", DEMO_POST_IMAGES[0], "image", ["design", "systems"]),
            ("arjun", "Built a mini Instagram clone in 4 hours using React + FastAPI. Tutorial dropping this weekend.", DEMO_POST_IMAGES[1], "image", ["react", "fastapi", "tutorial"]),
            ("neha", "Three frameworks I use to decide what NOT to build. Saved us 6 months last quarter.", DEMO_POST_IMAGES[2], "image", ["product", "strategy"]),
            ("maya", "Typography is 90% of good UI. Here's the exact scale I use on every project.", DEMO_POST_IMAGES[3], "image", ["typography", "ui"]),
            ("arjun", "Landed my first ₹50k freelance gig through Skiller gigs marketplace. It works.", DEMO_POST_IMAGES[4], "image", ["freelance", "win"]),
            ("neha", "Weekend read: how to price yourself without undercutting your worth.", DEMO_POST_IMAGES[5], "image", ["career"]),
            # Reels (vertical videos) — short stock samples
            ("maya", "Quick 30-sec design tip: spacing system in 3 numbers.", "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4", "video", ["design", "tip", "reel"]),
            ("arjun", "Speed-coding a button component. React + Tailwind, no library.", "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerJoyrides.mp4", "video", ["code", "react", "reel"]),
            ("neha", "PM frameworks in 60 seconds — RICE prioritisation explained.", "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerFun.mp4", "video", ["product", "pm", "reel"]),
        ]
        for username, caption, media, mtype, tags in demo_posts:
            await db.posts.insert_one({
                "id": str(uuid.uuid4()), "user_id": user_ids[username],
                "caption": caption, "media": media, "media_type": mtype,
                "tags": tags, "likes": [], "comments": [], "created_at": now_iso(),
            })

    if await db.courses.count_documents({}) == 0:
        courses = [
            ("React Mastery 2026", "Learn modern React 19 with hooks, server components, and real projects.", "Arjun Verma", "arjun", 12, 2999, DEMO_COURSE_IMAGES[0], "Development"),
            ("UI/UX Design Foundations", "Design stunning interfaces from scratch — color, type, layout, motion.", "Maya Sharma", "maya", 18, 3499, DEMO_COURSE_IMAGES[1], "Design"),
            ("Product Management 0→1", "Go from idea to MVP to PMF. Frameworks from top Indian PMs.", "Neha Iyer", "neha", 10, 2499, DEMO_COURSE_IMAGES[2], "Product"),
            ("Freelancing Without Begging", "Get your first 5 clients in 30 days. Pricing, pitching, delivery.", "Arjun Verma", "arjun", 8, 1999, DEMO_COURSE_IMAGES[3], "Business"),
        ]
        for title, desc, instructor, owner_username, lessons, price, thumb, cat in courses:
            await db.courses.insert_one({
                "id": str(uuid.uuid4()), "title": title, "description": desc,
                "instructor": instructor, "owner_id": user_ids.get(owner_username, ""),
                "lessons": lessons, "price": price, "thumbnail": thumb, "category": cat,
                "rating": 4.7, "students": 1200, "created_at": now_iso(),
            })

    if await db.gigs.count_documents({}) == 0:
        gigs = [
            ("admin", "Landing page in React + Tailwind", "Need a clean conversion-focused landing page for a SaaS.", 25000, "Remote", "Web Development", ["React", "Tailwind"]),
            ("maya", "Logo + Brand identity for D2C brand", "Full brand identity kit — logo, type, palette, usage.", 40000, "Remote", "Design", ["Logo", "Branding"]),
            ("maya", "Instagram content calendar (30 days)", "Plan and design 30 reels + carousel posts for a coaching brand.", 15000, "Remote", "Content", ["Social", "Design"]),
            ("arjun", "Python automation for lead scraping", "Scrape LinkedIn + clean into Google Sheets daily.", 20000, "Remote", "Development", ["Python", "Automation"]),
            ("neha", "Product strategy consulting (4 hrs)", "Help us pick the right v1 scope for our healthtech app.", 18000, "Remote", "Product", ["Strategy"]),
        ]
        # Resolve admin id
        admin_doc = await db.users.find_one({"role": "admin"}, {"_id": 0, "id": 1, "username": 1, "name": 1})
        admin_id = admin_doc["id"] if admin_doc else ""
        for owner_username, title, desc, budget, location, cat, skills in gigs:
            if owner_username == "admin":
                oid, ouname, oname = admin_id, admin_doc["username"] if admin_doc else "admin", admin_doc["name"] if admin_doc else "Skiller Admin"
            else:
                oid = user_ids.get(owner_username, "")
                u_doc = await db.users.find_one({"id": oid}, {"_id": 0, "username": 1, "name": 1})
                ouname = u_doc["username"] if u_doc else owner_username
                oname = u_doc["name"] if u_doc else owner_username
            await db.gigs.insert_one({
                "id": str(uuid.uuid4()),
                "owner_id": oid,
                "owner_username": ouname,
                "owner_name": oname,
                "title": title,
                "description": desc,
                "budget": budget,
                "currency": "INR",
                "location": location,
                "category": cat,
                "skills": skills,
                "created_at": now_iso(),
            })


async def init_vapid_keys():
    """Generate VAPID keys on first start, store them in MongoDB, return both as strings."""
    import base64
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec

    rec = await db.config.find_one({"key": "vapid"})
    if rec:
        return rec["private_key"], rec["public_key"]

    private_key = ec.generate_private_key(ec.SECP256R1())
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    pub = private_key.public_key().public_numbers()
    raw_pub = b"\x04" + pub.x.to_bytes(32, "big") + pub.y.to_bytes(32, "big")
    public_b64 = base64.urlsafe_b64encode(raw_pub).rstrip(b"=").decode()

    await db.config.insert_one({
        "key": "vapid",
        "private_key": private_pem,
        "public_key": public_b64,
    })
    return private_pem, public_b64

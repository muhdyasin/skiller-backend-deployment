"""Database seed (admin + demo users + posts + courses + gigs)."""
import os
import uuid
from core import db, now_iso, hash_password, verify_password

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
    await db.notifications.create_index([("user_id", 1), ("created_at", -1)])
    await db.password_reset_tokens.create_index("token", unique=True)
    await db.password_reset_tokens.create_index("expires_at")
    await db.files.create_index("storage_path")
    await db.ad_campaigns.create_index([("status", 1), ("created_at", -1)])
    await db.push_subscriptions.create_index("subscription.endpoint", unique=True)
    await db.push_subscriptions.create_index([("user_id", 1), ("active", 1)])

    await db.users.update_many(
        {"xp": {"$exists": False}},
        {"$set": {"xp": 0, "badges": [], "streak": 0, "last_login_date": None}},
    )

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
            ("maya", "Shipped a new design system today. Reds and whites — clean, calm, scalable.", DEMO_POST_IMAGES[0], ["design", "systems"]),
            ("arjun", "Built a mini Instagram clone in 4 hours using React + FastAPI. Tutorial dropping this weekend.", DEMO_POST_IMAGES[1], ["react", "fastapi", "tutorial"]),
            ("neha", "Three frameworks I use to decide what NOT to build. Saved us 6 months last quarter.", DEMO_POST_IMAGES[2], ["product", "strategy"]),
            ("maya", "Typography is 90% of good UI. Here's the exact scale I use on every project.", DEMO_POST_IMAGES[3], ["typography", "ui"]),
            ("arjun", "Landed my first ₹50k freelance gig through Skiller gigs marketplace. It works.", DEMO_POST_IMAGES[4], ["freelance", "win"]),
            ("neha", "Weekend read: how to price yourself without undercutting your worth.", DEMO_POST_IMAGES[5], ["career"]),
        ]
        for username, caption, media, tags in demo_posts:
            await db.posts.insert_one({
                "id": str(uuid.uuid4()), "user_id": user_ids[username],
                "caption": caption, "media": media, "media_type": "image",
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
            ("Landing page in React + Tailwind", "Need a clean conversion-focused landing page for a SaaS.", 25000, "Remote", "Web Development", ["React", "Tailwind"]),
            ("Logo + Brand identity for D2C brand", "Full brand identity kit — logo, type, palette, usage.", 40000, "Remote", "Design", ["Logo", "Branding"]),
            ("Instagram content calendar (30 days)", "Plan and design 30 reels + carousel posts for a coaching brand.", 15000, "Remote", "Content", ["Social", "Design"]),
            ("Python automation for lead scraping", "Scrape LinkedIn + clean into Google Sheets daily.", 20000, "Remote", "Development", ["Python", "Automation"]),
            ("Product strategy consulting (4 hrs)", "Help us pick the right v1 scope for our healthtech app.", 18000, "Remote", "Product", ["Strategy"]),
        ]
        for title, desc, budget, location, cat, skills in gigs:
            await db.gigs.insert_one({
                "id": str(uuid.uuid4()), "title": title, "description": desc,
                "budget": budget, "currency": "INR", "location": location,
                "category": cat, "skills": skills, "created_at": now_iso(),
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

import sys
from pathlib import Path

sys.path.append(
    str(Path(__file__).resolve().parent.parent)
)

import asyncio
from datetime import datetime

from core import db

from db.session import AsyncSessionLocal

from models.user import User
from models.user_follow import UserFollow

from datetime import datetime

def parse_datetime(value):
    if not value:
        return None

    try:
        dt = datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )

        # convert timezone-aware -> naive
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)

        return dt

    except Exception:
        return None


async def migrate_users():

    async with AsyncSessionLocal() as session:

        users = await db.users.find(
            {},
            {"_id": 0}
        ).to_list(5000)

        print(f"Found {len(users)} users")

        follow_pairs = set()

        for u in users:

            existing = await session.get(
                User,
                u["id"]
            )
            
            if existing:
                continue

            user = User(
                id=u["id"],
                email=u["email"],
                username=u["username"],
                name=u["name"],
                password_hash=u["password_hash"],
                bio=u.get("bio", ""),
                avatar_url=u.get("avatar_url", ""),
                role=u.get("role", "student"),
                xp=u.get("xp", 0),
                streak=u.get("streak", 0),
                badges=u.get("badges", []),
                email_verified=u.get("email_verified", False),
                referral_code=u.get("referral_code"),
                referred_by=u.get("referred_by"),
                plan=u.get("plan", "trial"),
                premium_until=parse_datetime(
                u.get("premium_until")
                ),
                last_login_date=u.get(
                    "last_login_date"
                ),
                created_at=parse_datetime(
                    u.get("created_at")
                )
            )

            session.add(user)

            for follower_id in u.get(
                "followers",
                []
            ):
                follow_pairs.add(
                    (
                        follower_id,
                        u["id"]
                    )
                )

        await session.commit()

        print(
            f"Found {len(follow_pairs)} follows"
        )

        for follower_id, following_id in follow_pairs:

            session.add(
                UserFollow(
                    follower_id=follower_id,
                    following_id=following_id
                )
            )

        await session.commit()

        print(
            "Users migration completed"
        )


asyncio.run(
    migrate_users()
)
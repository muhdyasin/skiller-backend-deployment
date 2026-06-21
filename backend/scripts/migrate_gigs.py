import sys
from pathlib import Path

sys.path.append(
    str(Path(__file__).resolve().parent.parent)
)

import asyncio

from core import db
from db.session import AsyncSessionLocal

from models.gig import Gig
from models.application import Application


async def migrate_gigs():

    async with AsyncSessionLocal() as session:

        gigs = await db.gigs.find(
            {},
            {"_id": 0}
        ).to_list(1000)

        print(f"Found {len(gigs)} gigs")

        for g in gigs:

            existing = await session.get(
                Gig,
                g["id"]
            )

            if existing:
                continue

            session.add(
                Gig(
                    id=g["id"],
                    owner_id=g["owner_id"],
                    owner_username=g["owner_username"],
                    owner_name=g["owner_name"],
                    title=g["title"],
                    description=g["description"],
                    budget=g["budget"],
                    currency=g.get("currency", "INR"),
                    location=g.get("location"),
                    category=g.get("category"),
                    skills=g.get("skills", [])
                )
            )

        apps = await db.applications.find(
            {},
            {"_id": 0}
        ).to_list(5000)

        print(f"Found {len(apps)} applications")

        for a in apps:

            existing = await session.get(
                Application,
                a["id"]
            )

            if existing:
                continue

            session.add(
                Application(
                    id=a["id"],
                    gig_id=a["gig_id"],
                    user_id=a["user_id"],
                    username=a["username"],
                    name=a["name"],
                    email=a["email"],
                    avatar_url=a.get("avatar_url"),
                    message=a["message"],
                    status=a.get("status", "pending")
                )
            )

        await session.commit()

        print("Migration completed")


asyncio.run(
    migrate_gigs()
)
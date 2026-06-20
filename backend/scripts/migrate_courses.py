import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

import asyncio

from core import db
from db.session import AsyncSessionLocal

from models.course import Course


async def migrate_courses():

    async with AsyncSessionLocal() as session:

        courses = await db.courses.find(
            {},
            {"_id": 0}
        ).to_list(1000)

        print(f"Found {len(courses)} courses")

        for c in courses:

            existing = await session.get(
                Course,
                c["id"]
            )

            if existing:
                continue

            course = Course(
                id=c["id"],
                owner_id=c["owner_id"],
                instructor=c["instructor"],
                title=c["title"],
                description=c["description"],
                price=int(c.get("price", 0)),
                lessons=int(c.get("lessons", 0)),
                thumbnail=c.get("thumbnail"),
                category=c.get("category"),
                rating=float(c.get("rating", 5.0)),
                students=int(c.get("students", 0))
            )

            session.add(course)

        await session.commit()

        print("Migration completed")


asyncio.run(
    migrate_courses()
)
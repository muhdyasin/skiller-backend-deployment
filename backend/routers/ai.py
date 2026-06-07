"""AI recommendations."""
import json
import logging
from fastapi import APIRouter, HTTPException, Depends
from core import db, get_current_user, EMERGENT_LLM_KEY

# New: OpenAI async client
from openai import AsyncOpenAI


router = APIRouter(prefix="/api/ai", tags=["ai"])
logger = logging.getLogger("skiller")


@router.get("/recommend")
async def ai_recommend(current=Depends(get_current_user)):
    if not EMERGENT_LLM_KEY:
        # If the key is missing, we can either error or fallback directly.
        # Here we choose to fallback to non-AI recommendations.
        logger.warning("EMERGENT_LLM_KEY not set, using fallback recommendations")

    user = await db.users.find_one({"id": current["id"]})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user_posts = (
        await db.posts.find(
            {"user_id": current["id"]},
            {"_id": 0, "caption": 1, "tags": 1},
        )
        .limit(10)
        .to_list(10)
    )
    courses = (
        await db.courses.find(
            {},
            {"_id": 0, "id": 1, "title": 1, "category": 1, "description": 1},
        )
        .to_list(50)
    )
    gigs = (
        await db.gigs.find(
            {},
            {"_id": 0, "id": 1, "title": 1, "skills": 1, "category": 1},
        )
        .to_list(50)
    )
    creators = (
        await db.users.find(
            {"id": {"$ne": current["id"]}},
            {"_id": 0, "username": 1, "name": 1, "bio": 1},
        )
        .limit(20)
        .to_list(20)
    )

    user_summary = (
        f"Name: {user['name']}\n"
        f"Bio: {user.get('bio', '')}\n"
        f"Recent posts: {json.dumps(user_posts)}"
    )
    catalog = {"courses": courses[:20], "gigs": gigs[:20], "creators": creators[:15]}

    system = (
        "You are a friendly career coach inside Skiller, an Indian learn-to-earn platform. "
        "Pick the most relevant courses, gigs and creators for the given user based on their bio, posts and tags. "
        "Return ONLY valid JSON, no markdown, no commentary."
    )
    prompt = (
        f"USER PROFILE:\n{user_summary}\n\n"
        f"AVAILABLE CATALOG (JSON):\n{json.dumps(catalog)[:6000]}\n\n"
        "Return JSON of shape: {\"courses\": [{\"id\": str, \"why\": str}], "
        "\"gigs\": [{\"id\": str, \"why\": str}], \"creators\": [{\"username\": str, \"why\": str}]}. "
        "Pick at most 3 courses, 3 gigs, 3 creators. 'why' is a single short sentence."
    )

    data = None

    # Try calling OpenAI; if anything fails, we fallback.
    if EMERGENT_LLM_KEY:
        try:
            client = AsyncOpenAI(api_key=EMERGENT_LLM_KEY)

            response = await client.chat.completions.create(
                model="gpt-4.1-mini",  # or any other model you have access to
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.5,
            )

            text = response.choices[0].message.content.strip()

            # Handle possible code fences (```json ... ```), similar to your old logic
            if text.startswith("```"):
                text = text.split("```", 2)[1]
                if text.lower().startswith("json"):
                    text = text[4:]
                text = text.strip("` \n")

            data = json.loads(text)
        except Exception as e:
            logger.error(f"AI recommend failed: {e}")

    # Fallback if data is still None or invalid
    if not isinstance(data, dict):
        data = {
            "courses": [
                {"id": c["id"], "why": "Trending right now"}
                for c in courses[:3]
            ],
            "gigs": [
                {"id": g["id"], "why": "Matches general skills"}
                for g in gigs[:3]
            ],
            "creators": [
                {"username": c["username"], "why": "Popular in your network"}
                for c in creators[:3]
            ],
        }

    course_map = {c["id"]: c for c in courses}
    gig_map = {g["id"]: g for g in gigs}
    creator_map = {c["username"]: c for c in creators}

    return {
        "courses": [
            {
                **course_map[r["id"]],
                "why": r.get("why", ""),
            }
            for r in data.get("courses", [])
            if r.get("id") in course_map
        ][:3],
        "gigs": [
            {
                **gig_map[r["id"]],
                "why": r.get("why", ""),
            }
            for r in data.get("gigs", [])
            if r.get("id") in gig_map
        ][:3],
        "creators": [
            {
                **creator_map[r["username"]],
                "why": r.get("why", ""),
            }
            for r in data.get("creators", [])
            if r.get("username") in creator_map
        ][:3],
    }
"""Skiller server entry point — wires routers, CORS, startup."""
import os
import sys
import logging
from pathlib import Path
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

# Make local modules importable
sys.path.insert(0, str(Path(__file__).parent))

from core import client, init_storage  # loads .env via core
from notifications_service import set_vapid_keys
from seed import seed

from routers.auth import router as auth_router
from routers.users import router as users_router
from routers.posts import router as posts_router
from routers.courses import router as courses_router
from routers.gigs import router as gigs_router
from routers.ads import router as ads_router
from routers.dashboard import router as dashboard_router
from routers.ai import router as ai_router
from routers.notifications import router as notifications_router
from routers.files import router as files_router
from routers.ws import router as ws_router
from routers.search import router as search_router
from routers.push import router as push_router
from routers.billing import router as billing_router
from routers.wallet import router as wallet_router
from routers.stories import router as stories_router
from routers.groups import router as groups_router
from routers.seo import router as seo_router


from routers.subscriptions import router as subscriptions_router
from routers import wallets
from routers import withdrawals
from routers.admin_withdrawals import router as admin_withdrawals_router
from routers.enrollments import router as enrollments_router
from routers.lessons import router as lessons_router
from routers import payout_accounts

logger = logging.getLogger("skiller")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Skiller API")

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(posts_router)
app.include_router(courses_router)
app.include_router(gigs_router)
app.include_router(ads_router)
app.include_router(dashboard_router)
app.include_router(ai_router)
app.include_router(notifications_router)
app.include_router(files_router)
app.include_router(ws_router)
app.include_router(search_router)
app.include_router(push_router)
app.include_router(billing_router)
app.include_router(wallet_router)
app.include_router(stories_router)
app.include_router(groups_router)
app.include_router(seo_router)
app.include_router(subscriptions_router)
app.include_router(wallets.router)
app.include_router(withdrawals.router)
app.include_router(admin_withdrawals_router)
app.include_router(enrollments_router)
app.include_router(lessons_router)
app.include_router(payout_accounts.router)


@app.on_event("startup")
async def startup():
    logger.info("Application started")
    init_storage()
    # try:
    #     priv, pub = await init_vapid_keys()
    #     set_vapid_keys(priv, pub)
    #     logger.info("VAPID keys ready")
    # except Exception as e:
    #     logger.warning(f"VAPID init failed: {e}")


@app.on_event("shutdown")
async def shutdown():
    client.close()


app.add_middleware(
    CORSMiddleware,
    allow_credentials=False,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

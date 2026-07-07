import asyncio
from datetime import datetime

from sqlalchemy import select

from db.session import AsyncSessionLocal

from core import (
    hash_password,
    trial_premium_until,
    generate_referral_code,
)

from models.user import User
from models.course import Course
from models.gig import Gig
from models.application import Application
from models.enrollment import Enrollment
from models.subscription import Subscription
from models.subscription_plan import SubscriptionPlan
from models.user_follow import UserFollow
from models.wallet import Wallet
from models.wallet_ledger import WalletLedger
from models.payment_transaction import PaymentTransaction
from models.xp_event import XPEvent

from seed_subscription_plans import seed_subscription_plans

ADMIN_EMAIL = "admin@skiller.app"
ADMIN_PASSWORD = "Admin@123"

CREATOR_EMAIL = "creator@skiller.app"
CREATOR_PASSWORD = "Creator@123"

STUDENT_EMAIL = "student@skiller.app"
STUDENT_PASSWORD = "Student@123"

INSTITUTION_EMAIL = "institution@skiller.app"
INSTITUTION_PASSWORD = "Institution@123"

async def get_user_by_email(db, email: str):
    result = await db.execute(
        select(User).where(User.email == email)
    )

    return result.scalar_one_or_none()

async def create_user(
    db,
    *,
    email,
    username,
    name,
    password,
    role,
):
    existing = await get_user_by_email(
        db,
        email
    )

    if existing:
        print(f"✓ {email} already exists")
        return existing

    user = User(
        email=email,
        username=username,
        name=name,
        password_hash=hash_password(password),
        role=role,
        bio=f"Demo {role.title()} Account",
        avatar_url="",
        xp=50 if role != "admin" else 500,
        streak=1,
        badges=[],
        email_verified=True,
        referral_code=generate_referral_code(),
        referred_by=None,
        plan="trial",
        premium_until=trial_premium_until(),
        last_login_date=str(datetime.utcnow().date()),
    )

    db.add(user)

    await db.commit()
    await db.refresh(user)

    print(f"✓ Created {email}")

    return user

async def create_wallet(
    db,
    owner,
):
    result = await db.execute(
        select(Wallet).where(
            Wallet.owner_id == owner.id
        )
    )

    wallet = result.scalar_one_or_none()

    if wallet:
        return wallet

    wallet = Wallet(
        owner_id=owner.id,
        owner_type=owner.role,
        balance=0,
        lifetime_earned=0,
        lifetime_withdrawn=0,
    )

    db.add(wallet)

    await db.commit()
    await db.refresh(wallet)

    print(f"✓ Wallet created for {owner.username}")

    return wallet

async def create_trial_subscription(
    db,
    user,
):
    result = await db.execute(
        select(Subscription).where(
            Subscription.user_id == user.id
        )
    )

    subscription = result.scalar_one_or_none()

    if subscription:
        return subscription

    subscription = Subscription(
        user_id=user.id,
        user_type=user.role,
        plan_id="trial",
        status="trial",
        starts_at=datetime.utcnow(),
        expires_at=trial_premium_until(),
        payment_provider=None,
    )

    db.add(subscription)

    await db.commit()
    await db.refresh(subscription)

    print(f"✓ Trial subscription created for {user.username}")

    return subscription

async def seed_users(db):

    print("\n========== USERS ==========\n")

    admin = await create_user(
        db,
        email=ADMIN_EMAIL,
        username="admin",
        name="Administrator",
        password=ADMIN_PASSWORD,
        role="admin",
    )

    creator = await create_user(
        db,
        email=CREATOR_EMAIL,
        username="creator1",
        name="Creator User",
        password=CREATOR_PASSWORD,
        role="creator",
    )

    student = await create_user(
        db,
        email=STUDENT_EMAIL,
        username="student1",
        name="Student User",
        password=STUDENT_PASSWORD,
        role="student",
    )

    institution = await create_user(
        db,
        email=INSTITUTION_EMAIL,
        username="institution1",
        name="Institution User",
        password=INSTITUTION_PASSWORD,
        role="institution",
    )

    users = [
        admin,
        creator,
        student,
        institution,
    ]

    print("\n========== WALLETS ==========\n")

    for user in users:
        await create_wallet(
            db,
            user,
        )

    print("\n========== TRIAL SUBSCRIPTIONS ==========\n")

    for user in [creator, institution]:
        await create_trial_subscription(
            db,
            user,
        )

    return {
        "admin": admin,
        "creator": creator,
        "student": student,
        "institution": institution,
    }
    
async def create_demo_follow(
    db,
    student,
    creator,
):
    result = await db.execute(
        select(UserFollow).where(
            UserFollow.follower_id == student.id,
            UserFollow.following_id == creator.id,
        )
    )

    follow = result.scalar_one_or_none()

    if follow:
        return

    follow = UserFollow(
        follower_id=student.id,
        following_id=creator.id,
    )

    db.add(follow)

    await db.commit()

    print("✓ Demo follow relationship created")
    
async def award_demo_xp(
    db,
    user,
):

    result = await db.execute(
        select(XPEvent).where(
            XPEvent.user_id == user.id
        )
    )

    existing = result.scalars().first()

    if existing:
        return

    user.xp += 100

    event = XPEvent(
        user_id=user.id,
        reason="seed",
        amount=100,
        meta={
            "source": "seed.py"
        }
    )

    db.add(event)

    await db.commit()

    print(f"✓ XP awarded to {user.username}")
    
async def seed_course(
    db,
    creator,
):

    result = await db.execute(
        select(Course).where(
            Course.title == "Python Masterclass"
        )
    )

    course = result.scalar_one_or_none()

    if course:
        return course

    course = Course(
        owner_id=creator.id,
        instructor=creator.name,
        title="Python Masterclass",
        description="Complete Python Course",
        price=1000,
        lessons=10,
        thumbnail="https://images.unsplash.com/photo-1519408469771-2586093c3f14?w=1200&q=80",
        category="Programming",
        rating=5.0,
        students=0,
    )

    db.add(course)

    await db.commit()
    await db.refresh(course)

    print("✓ Demo course created")

    return course

async def seed_enrollment(
    db,
    student,
    course,
):

    result = await db.execute(
        select(Enrollment).where(
            Enrollment.user_id == student.id,
            Enrollment.course_id == course.id,
        )
    )

    enrollment = result.scalar_one_or_none()

    if enrollment:
        return enrollment

    enrollment = Enrollment(
        user_id=student.id,
        course_id=course.id,
        amount_paid=course.price,
    )

    db.add(enrollment)

    course.students += 1

    await db.commit()

    print("✓ Demo enrollment created")

    return enrollment

async def seed_gig(
    db,
    creator,
):

    result = await db.execute(
        select(Gig).where(
            Gig.title == "Build a React Website"
        )
    )

    gig = result.scalar_one_or_none()

    if gig:
        return gig

    gig = Gig(
        owner_id=creator.id,
        owner_username=creator.username,
        owner_name=creator.name,
        title="Build a React Website",
        description="Looking for a frontend developer.",
        budget=5000,
        currency="INR",
        location="Remote",
        category="Web Development",
        skills=[
            "React",
            "JavaScript",
            "CSS"
        ]
    )

    db.add(gig)

    await db.commit()
    await db.refresh(gig)

    print("✓ Demo gig created")

    return gig

async def seed_application(
    db,
    student,
    gig,
):

    result = await db.execute(
        select(Application).where(
            Application.user_id == student.id,
            Application.gig_id == gig.id,
        )
    )

    application = result.scalar_one_or_none()

    if application:
        return application

    application = Application(
        gig_id=gig.id,
        user_id=student.id,
        applicant_name=student.name,
        applicant_username=student.username,
        cover_letter="Interested in this project.",
        status="pending",
    )

    db.add(application)

    await db.commit()

    print("✓ Demo application created")
    
async def seed_payment(
    db,
    student,
    creator,
    course,
):

    result = await db.execute(
        select(PaymentTransaction).where(
            PaymentTransaction.transaction_type == "course_purchase",
            PaymentTransaction.payer_id == student.id,
        )
    )

    transaction = result.scalar_one_or_none()

    if transaction:
        return

    transaction = PaymentTransaction(
        payer_id=student.id,
        payee_id=creator.id,
        amount=course.price,
        commission_amount=100,
        transaction_type="course_purchase",
        payment_provider="manual",
        status="paid",
    )

    db.add(transaction)

    await db.commit()

    print("✓ Demo payment created")
    
async def seed_wallet_credit(
    db,
    creator,
):

    result = await db.execute(
        select(Wallet).where(
            Wallet.owner_id == creator.id
        )
    )

    wallet = result.scalar_one()

    if wallet.balance > 0:
        return

    wallet.balance = 900
    wallet.lifetime_earned = 900

    ledger = WalletLedger(
        wallet_id=wallet.id,
        transaction_type="credit",
        amount=900,
        description="Demo course purchase",
    )

    db.add(ledger)

    await db.commit()

    print("✓ Wallet credited")
    
async def seed():

    print("\n==============================")
    print("SKILLER POSTGRES SEED")
    print("==============================\n")

    await seed_subscription_plans()

    async with AsyncSessionLocal() as db:

        users = await seed_users(db)

        await create_demo_follow(
            db,
            users["student"],
            users["creator"],
        )

        await award_demo_xp(
            db,
            users["creator"],
        )

        course = await seed_course(
            db,
            users["creator"],
        )

        await seed_enrollment(
            db,
            users["student"],
            course,
        )

        gig = await seed_gig(
            db,
            users["creator"],
        )

        await seed_application(
            db,
            users["student"],
            gig,
        )

        await seed_payment(
            db,
            users["student"],
            users["creator"],
            course,
        )

        await seed_wallet_credit(
            db,
            users["creator"],
        )

    print("\n==============================")
    print("DATABASE SEEDED SUCCESSFULLY")
    print("==============================")
    
if __name__ == "__main__":
    asyncio.run(seed())
    

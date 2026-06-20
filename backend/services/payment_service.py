from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.payment_transaction import PaymentTransaction


class PaymentService:

    @staticmethod
    async def create_transaction(
        db: AsyncSession,
        payer_id: str,
        amount: int,
        transaction_type: str,
        payment_provider: str,
        payee_id: str = None,
        plan_id: str = None,
        commission_amount: int = 0
    ):
        transaction = PaymentTransaction(
            payer_id=payer_id,
            payee_id=payee_id,
            amount=amount,
            commission_amount=commission_amount,
            transaction_type=transaction_type,
            payment_provider=payment_provider,
            plan_id=plan_id,
            status="pending"
        )

        db.add(transaction)

        await db.commit()
        await db.refresh(transaction)

        return transaction

    @staticmethod
    async def get_transaction(
        db: AsyncSession,
        transaction_id: str
    ):
        result = await db.execute(
            select(PaymentTransaction)
            .where(
                PaymentTransaction.id == transaction_id
            )
        )

        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_transaction_by_order_id(
    db: AsyncSession,
    order_id: str
    ):
        result = await db.execute(
            select(PaymentTransaction)
            .where(
                PaymentTransaction.provider_order_id
                == order_id
            )
        )

        return result.scalar_one_or_none()

    @staticmethod
    async def mark_paid(
        db: AsyncSession,
        transaction: PaymentTransaction,
        provider_order_id: str = None,
        provider_payment_id: str = None
    ):
        transaction.status = "paid"
        transaction.provider_order_id = provider_order_id
        transaction.provider_payment_id = provider_payment_id

        await db.commit()

        return transaction

    @staticmethod
    async def mark_failed(
        db: AsyncSession,
        transaction: PaymentTransaction
    ):
        transaction.status = "failed"

        await db.commit()

        return transaction

    @staticmethod
    async def create_subscription_transaction(
        db: AsyncSession,
        payer_id: str,
        plan_id:str,
        amount: int,
        payment_provider: str
    ):
        
        return await PaymentService.create_transaction(
        db=db,
        payer_id=payer_id,
        plan_id=plan_id,
        amount=amount,
        transaction_type="subscription",
        payment_provider=payment_provider
        )
        
    @staticmethod
    async def create_razorpay_order_transaction(
        db: AsyncSession,
        payer_id: str,
        amount: int,
        plan_id: str,
        order_id: str
    ):
        transaction = PaymentTransaction(
        payer_id=payer_id,
        amount=amount,
        transaction_type="subscription",
        payment_provider="razorpay",
        provider_order_id=order_id,
        plan_id=plan_id,
        status="created"
        )

        db.add(transaction)

        await db.commit()
        await db.refresh(transaction)

        return transaction
    
    @staticmethod
    async def create_course_purchase_transaction(
        db: AsyncSession,
        payer_id: str,
        payee_id: str,
        amount: int,
        commission_amount: int
    ):
        
        return await PaymentService.create_transaction(
            db=db,
            payer_id=payer_id,
            payee_id=payee_id,
            amount=amount,
            commission_amount=commission_amount,
            transaction_type="course_purchase",
            payment_provider="manual"
        )
    
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.observability import InferenceLog, Alert
from typing import List, Optional

class CRUDObservability:
    async def create_log(
        self, 
        db: AsyncSession, 
        model_id: UUID, 
        features: dict, 
        prediction: int, 
        confidence: float, 
        latent_embedding: Optional[list] = None
    ) -> InferenceLog:
        db_obj = InferenceLog(
            model_id=model_id,
            features=features,
            prediction=prediction,
            confidence=confidence,
            latent_embedding={"vector": latent_embedding} if latent_embedding is not None else None
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def create_alert(
        self, 
        db: AsyncSession, 
        model_id: UUID, 
        alert_type: str, 
        severity: str, 
        message: str, 
        metric_value: float
    ) -> Alert:
        db_obj = Alert(
            model_id=model_id,
            alert_type=alert_type,
            severity=severity,
            message=message,
            metric_value=metric_value
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def get_alert(self, db: AsyncSession, alert_id: UUID) -> Optional[Alert]:
        result = await db.execute(select(Alert).where(Alert.id == alert_id))
        return result.scalars().first()

    async def get_alerts_by_model(self, db: AsyncSession, model_id: UUID) -> List[Alert]:
        result = await db.execute(
            select(Alert)
            .where(Alert.model_id == model_id)
            .order_by(Alert.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_recent_logs(self, db: AsyncSession, model_id: UUID, limit: int = 100) -> List[InferenceLog]:
        result = await db.execute(
            select(InferenceLog)
            .where(InferenceLog.model_id == model_id)
            .order_by(InferenceLog.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

observability_crud = CRUDObservability()

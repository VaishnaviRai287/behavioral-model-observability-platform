from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.fingerprint import BehavioralFingerprint
from typing import List, Optional

class CRUDFingerprint:
    async def get(self, db: AsyncSession, fingerprint_id: UUID) -> Optional[BehavioralFingerprint]:
        result = await db.execute(select(BehavioralFingerprint).where(BehavioralFingerprint.id == fingerprint_id))
        return result.scalars().first()

    async def get_latest_by_model(self, db: AsyncSession, model_id: UUID) -> Optional[BehavioralFingerprint]:
        result = await db.execute(
            select(BehavioralFingerprint)
            .where(BehavioralFingerprint.model_id == model_id)
            .order_by(BehavioralFingerprint.created_at.desc())
            .limit(1)
        )
        return result.scalars().first()

    async def create(
        self, 
        db: AsyncSession, 
        model_id: UUID, 
        num_samples: int,
        class_distribution: dict,
        confidence_distribution: dict,
        high_uncertainty_regions: dict,
        boundary_samples: dict
    ) -> BehavioralFingerprint:
        db_obj = BehavioralFingerprint(
            model_id=model_id,
            num_samples=num_samples,
            class_distribution=class_distribution,
            confidence_distribution=confidence_distribution,
            high_uncertainty_regions=high_uncertainty_regions,
            boundary_samples=boundary_samples
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

fingerprint_crud = CRUDFingerprint()

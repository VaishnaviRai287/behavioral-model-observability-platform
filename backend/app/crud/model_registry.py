from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.model_registry import RegisteredModel
from app.schemas.model_registry import ModelRegisterCreate
from typing import List, Optional

class CRUDModelRegistry:
    async def get(self, db: AsyncSession, model_id: UUID) -> Optional[RegisteredModel]:
        result = await db.execute(select(RegisteredModel).where(RegisteredModel.id == model_id))
        return result.scalars().first()

    async def get_by_name_and_version(
        self, db: AsyncSession, name: str, version: str
    ) -> Optional[RegisteredModel]:
        result = await db.execute(
            select(RegisteredModel).where(
                RegisteredModel.name == name, RegisteredModel.version == version
            )
        )
        return result.scalars().first()

    async def get_multi(
        self, db: AsyncSession, skip: int = 0, limit: int = 100
    ) -> List[RegisteredModel]:
        result = await db.execute(select(RegisteredModel).offset(skip).limit(limit))
        return list(result.scalars().all())

    async def create(self, db: AsyncSession, obj_in: ModelRegisterCreate) -> RegisteredModel:
        db_obj = RegisteredModel(
            name=obj_in.name,
            version=obj_in.version,
            framework=obj_in.framework,
            task_type=obj_in.task_type,
            artifact_uri=obj_in.artifact_uri,
            input_schema=obj_in.input_schema.model_dump(),
            output_schema=obj_in.output_schema.model_dump(),
            status=obj_in.status or "registered",
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def remove(self, db: AsyncSession, model_id: UUID) -> Optional[RegisteredModel]:
        db_obj = await self.get(db, model_id=model_id)
        if db_obj:
            await db.delete(db_obj)
            await db.commit()
        return db_obj

model_registry_crud = CRUDModelRegistry()

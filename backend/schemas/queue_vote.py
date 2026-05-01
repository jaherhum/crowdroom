from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CreateQueueVote(BaseModel):
    queue_item_id: UUID = Field(..., alias="id", description="Queue item id")
    user_id: UUID = Field(..., description="User id")

    model_config = ConfigDict(populate_by_name=True)


class ReadQueueVote(BaseModel):
    id: UUID = Field(..., description="Vote id")
    queue_item_id: UUID = Field(..., description="Queue item id")
    user_id: UUID = Field(..., description="User id")

    model_config = ConfigDict(from_attributes=True)
from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, computed_field
from fastapi import File, UploadFile, Form

from models import ArtifactStatus, Region, SystemRole, ReviewDecision


class LoginForm(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    refresh_token: str
    access_token: str
    token_type: str


class UserForm(BaseModel):
    email: str
    password: str
    name: str
    role: SystemRole
    region: Region
    is_trusted_contributor: Optional[bool] = False


class UserResponse(BaseModel):
    id: UUID
    email: str
    name: str
    role: SystemRole
    region: Region
    is_trusted_contributor: Optional[bool] = False
    created_on: datetime

    class Config:
        from_attributes = True


class KnowledgeArtifactForm(BaseModel):
    title: str
    summary: str
    content: str
    status: ArtifactStatus | None = ArtifactStatus.DRAFT
    file: UploadFile | None = None

    @classmethod
    def as_form(
        cls,
        title: str = Form(...),
        summary: str = Form(...),
        content: str = Form(...),
        status: ArtifactStatus = Form(ArtifactStatus.DRAFT),
        file: UploadFile = File(None),
    ):
        return cls(
            title=title,
            summary=summary,
            content=content,
            status=status,
            file=file,
        )


class KnowledgeArtifactResponse(BaseModel):
    id: UUID
    title: str
    summary: str
    content: str
    status: ArtifactStatus
    file: Optional[str]
    created_by: UUID
    created_on: datetime
    review: Optional[ArtifactReviewStatusResponse] = None

    @computed_field
    @property
    def review_requested(self) -> bool:
        return self.review is not None

    @computed_field
    @property
    def file_url(self) -> Optional[str]:
        if self.file:
            return f"http://localhost:8000/api/files/{self.created_by}/artifacts/{self.file}"
        return None

    class Config:
        from_attributes = True


class ArtifactTagForm(BaseModel):
    tag: str


class ArtifactTagResponse(ArtifactTagForm):
    id: UUID
    artifact_id: UUID

    class Config:
        from_attributes = True


class RatingForm(BaseModel):
    artifact_id: UUID
    score: int


class RatingResponse(BaseModel):
    id: UUID
    artifact_id: UUID
    user_id: UUID
    score: int
    rated_on: datetime

    class Config:
        from_attributes = True


class ArtifactReviewStatusForm(BaseModel):
    decision: ReviewDecision
    comments: Optional[str] = None


class ArtifactReviewStatusResponse(BaseModel):
    id: UUID
    artifact_id: UUID
    decision: ReviewDecision
    comments: Optional[str] = None
    reviewed_by: Optional[UUID] = None
    submitted_on: datetime

    class Config:
        from_attributes = True


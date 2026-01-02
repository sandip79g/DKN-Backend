from datetime import datetime, timezone
from enum import Enum
import uuid

from sqlalchemy import (
    Column,
    String,
    Enum as EnumField,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    Integer,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database import Base


class SystemRole(str, Enum):
    CONSULTANT = "CONSULTANT"
    KNOWLEDGE_CHAMPION = "KNOWLEDGE_CHAMPION"
    GOVERNANCE_COUNCIL = "GOVERNANCE_COUNCIL"
    ADMIN = "ADMIN"


class ArtifactStatus(str, Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    PUBLISHED = "PUBLISHED"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"


class ReviewDecision(str, Enum):
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"


class Region(str, Enum):
    AFRICA = "AFRICA"
    ASIA = "ASIA"
    AUSTRALIA = "AUSTRALIA"
    EUROPE = "EUROPE"
    NORTH_AMERICA = "NORTH_AMERICA"
    SOUTH_AMERICA = "SOUTH_AMERICA"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(256), nullable=False)
    email = Column(String(256), unique=True, nullable=False)
    password = Column(String(256), nullable=False)
    role = Column(EnumField(SystemRole), default=SystemRole.CONSULTANT, nullable=False)
    region = Column(EnumField(Region), default=Region.EUROPE, nullable=False)
    is_trusted_contributor = Column(Boolean, default=False)
    created_on = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    artifacts = relationship("KnowledgeArtifact", back_populates="created_by_user")
    ratings = relationship("Rating", back_populates="rated_by_user")
    reviews = relationship("ArtifactReviewStatus", back_populates="reviewed_by_user")
  


class KnowledgeArtifact(Base):
    __tablename__ = "artifacts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(256), nullable=False)
    content = Column(Text, nullable=False)
    summary = Column(Text)
    status = Column(EnumField(ArtifactStatus), default=ArtifactStatus.DRAFT, nullable=False)
    file = Column(String(256))
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_on = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_updated = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    created_by_user = relationship("User", back_populates="artifacts")
    tags = relationship("ArtifactTag", back_populates="artifact", cascade="all, delete-orphan")
    ratings = relationship("Rating", back_populates="artifact", cascade="all, delete-orphan")
    review = relationship("ArtifactReviewStatus", back_populates="artifact", uselist=False, cascade="all, delete-orphan")


class ArtifactTag(Base):
    __tablename__ = "artifact_tags"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    artifact_id = Column(UUID(as_uuid=True), ForeignKey("artifacts.id"), nullable=False)
    tag = Column(String(256), nullable=False)

    artifact = relationship("KnowledgeArtifact", back_populates="tags")


class ArtifactReviewStatus(Base):
    __tablename__ = "reviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    artifact_id = Column(UUID(as_uuid=True), ForeignKey("artifacts.id"), unique=True, nullable=False)
    decision = Column(EnumField(ReviewDecision), default=ReviewDecision.PENDING, nullable=False)
    comments = Column(Text, nullable=True)
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    submitted_on = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    artifact = relationship("KnowledgeArtifact", back_populates="review")
    reviewed_by_user = relationship("User", back_populates="reviews")


class Rating(Base):
    __tablename__ = "ratings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    artifact_id = Column(UUID(as_uuid=True), ForeignKey("artifacts.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    score = Column(Integer, nullable=False)
    rated_on = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    artifact = relationship("KnowledgeArtifact", back_populates="ratings")
    rated_by_user = relationship("User", back_populates="ratings")


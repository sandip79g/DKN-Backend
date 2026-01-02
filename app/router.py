import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import joinedload

from database import get_db
from settings import settings
from models import (
    ReviewDecision,
    ArtifactStatus,
    ArtifactReviewStatus,
    SystemRole,
    User,
    KnowledgeArtifact, 
    Rating,
   
)
from schemas import (
    UserForm, 
    UserResponse,
    LoginForm,
    TokenResponse,
    KnowledgeArtifactForm,
    KnowledgeArtifactResponse,
    RatingForm,
    RatingResponse,
    ArtifactReviewStatusForm,
   
)
from auth import (
    get_password_hash, 
    authenticate_user, 
    create_access_token, 
    create_refresh_token, 
    auth_user, 
    decode_token
)
from settings import settings


router = APIRouter(prefix="/api")


@router.get("/files/{user_id}/{file_model_type}/{filename}")

async def get_file(user_id: str, file_model_type: str, filename: str):

    file_path = os.path.join(settings.MEDIA_DIR, user_id, file_model_type, filename)
    if os.path.exists(file_path):
        return FileResponse(path=file_path, filename=filename)
    
    return Response(content="File not found", status_code=404)


@router.post("/register", response_model=UserResponse)
async def register(data: UserForm, db=Depends(get_db)):

    if db.query(User).filter(User.email == data.email).first():
        return Response(content="Email already registered", status_code=400)

    new_user = User(
        name=data.name,
        email=data.email,
        role=data.role,
        region=data.region,
        is_trusted_contributor=data.is_trusted_contributor,
        password=get_password_hash(data.password),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginForm, db=Depends(get_db)):

    user = authenticate_user(db, data.email, data.password)
    if not user:
        return Response(content="Invalid credentials", status_code=401)

    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.post("/refresh-token", response_model=TokenResponse)
async def refresh_access_token(refresh_token: dict):
    payload = decode_token(refresh_token['refresh_token'])
    user_id = payload.get("sub")

    access_token = create_access_token(data={"sub": user_id})
    refresh_token = create_refresh_token(data={"sub": user_id})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.get("/profile", response_model=UserResponse)
async def get_profile(current_user: User = Depends(auth_user)):
    return current_user


@router.get("/dashboard")
async def get_dashboard(current_user: User = Depends(auth_user)):
    artifacts = current_user.artifacts
    return {
        "user": current_user,
        "artifacts": artifacts,
    }


@router.get("/artifacts", response_model=list[KnowledgeArtifactResponse])
async def list_artifacts(db=Depends(get_db)):
    artifacts = db.query(KnowledgeArtifact).filter(KnowledgeArtifact.status == ArtifactStatus.PUBLISHED).all()
    return artifacts


@router.get("/artifacts/my-artifacts", response_model=list[KnowledgeArtifactResponse])
async def list_my_artifacts(
    current_user: User = Depends(auth_user),
    db=Depends(get_db)
):
    artifacts = db.query(KnowledgeArtifact).options(joinedload(KnowledgeArtifact.review)).filter(KnowledgeArtifact.created_by == current_user.id).all()
    return artifacts


@router.post("/create-artifact", response_model=KnowledgeArtifactResponse)
async def create_artifact(
    data: KnowledgeArtifactForm = Depends(KnowledgeArtifactForm.as_form),
    current_user: User = Depends(auth_user),
    db=Depends(get_db)
):
    try:
        new_artifact = KnowledgeArtifact(
            title=data.title,
            content=data.content,
            summary=data.summary,
            status=data.status,
            created_by=current_user.id,
        )

        # Handle file upload if present
        if data.file:
            file_location = f"{settings.MEDIA_DIR}/{current_user.id}/artifacts/{data.file.filename}"
            os.makedirs(os.path.dirname(file_location), exist_ok=True)
            with open(file_location, "wb+") as file_object:
                file_object.write(data.file.file.read())
            new_artifact.file = data.file.filename

        db.add(new_artifact)
        db.commit()
        db.refresh(new_artifact)

        return new_artifact
    
    except Exception as e:
        return Response(content=str(e), status_code=500)
    

@router.get("/artifacts/{artifact_id}", response_model=KnowledgeArtifactResponse)
async def get_artifact(artifact_id: uuid.UUID, db=Depends(get_db)):
    artifact = db.query(KnowledgeArtifact).filter(KnowledgeArtifact.id == artifact_id).first()
    review = db.query(ArtifactReviewStatus).filter(ArtifactReviewStatus.artifact_id == artifact_id).first()
    if review:
        artifact.review_requested = True
        artifact.review_status = review.decision
            
    if not artifact:
        return Response(content="Artifact not found", status_code=404)
    return artifact
    

@router.put("/artifacts/{artifact_id}", response_model=KnowledgeArtifactResponse)
async def update_artifact(
    artifact_id: uuid.UUID,
    data: KnowledgeArtifactForm = Depends(KnowledgeArtifactForm.as_form),
    current_user: User = Depends(auth_user),
    db=Depends(get_db)
):
    artifact = db.query(KnowledgeArtifact).filter(KnowledgeArtifact.id == artifact_id).first()
    if not artifact:
        return Response(content="Artifact not found", status_code=404)

    if artifact.created_by != current_user.id:
        return Response(content="Unauthorized", status_code=403)

    artifact.title = data.title
    artifact.content = data.content
    artifact.summary = data.summary
    artifact.status = data.status
    artifact.last_updated = datetime.now(timezone.utc)

    # Handle file upload if present and also remove old file
    if data.file:
        # Remove old file if exists
        if artifact.file:
            old_file_path = os.path.join(settings.MEDIA_DIR, str(current_user.id), "artifacts", artifact.file)
            if os.path.exists(old_file_path):
                os.remove(old_file_path)

        file_location = f"{settings.MEDIA_DIR}/{current_user.id}/artifacts/{data.file.filename}"
        os.makedirs(os.path.dirname(file_location), exist_ok=True)
        with open(file_location, "wb+") as file_object:
            file_object.write(data.file.file.read())
        artifact.file = data.file.filename

    db.commit()
    db.refresh(artifact)

    return artifact

@router.delete("/artifacts/{artifact_id}")
async def delete_artifact(
    artifact_id: uuid.UUID,
    current_user: User = Depends(auth_user),
    db=Depends(get_db)
):
    artifact = db.query(KnowledgeArtifact).filter(KnowledgeArtifact.id == artifact_id).first()
    if not artifact:
        return Response(content="Artifact not found", status_code=404)

    if artifact.created_by != current_user.id:
        return Response(content="Unauthorized", status_code=403)

    db.delete(artifact)
    db.commit()

    return Response(content="Artifact deleted successfully", status_code=200)


@router.post("/publish-artifact/{artifact_id}")
async def publish_artifact(
    artifact_id: uuid.UUID,
    current_user: User = Depends(auth_user),
    db=Depends(get_db)
):
    artifact = db.query(KnowledgeArtifact).filter(KnowledgeArtifact.id == artifact_id).first()
    if not artifact:
        return Response(content="Artifact not found", status_code=404)
    
    if artifact.created_by != current_user.id:
        return Response(content="Unauthorized", status_code=403)

    if artifact.status == 'PUBLISHED':
        return Response(content="Artifact is already published", status_code=400)

    artifact.status = 'PUBLISHED'
    artifact.last_updated = datetime.now(timezone.utc)

    db.commit()
    db.refresh(artifact)

    return Response(content="Artifact published successfully", status_code=200)


@router.post("/request-review/{artifact_id}")
async def request_artifact_review(
    artifact_id: uuid.UUID,
    current_user: User = Depends(auth_user),
    db=Depends(get_db)
):
    artifact = db.query(KnowledgeArtifact).filter(KnowledgeArtifact.id == artifact_id).first()
    if not artifact:
        return Response(content="Artifact not found", status_code=404)
    
    if artifact.created_by != current_user.id:
        return Response(content="Unauthorized", status_code=403)

    existing_review = db.query(ArtifactReviewStatus).filter(ArtifactReviewStatus.artifact_id == artifact_id).all()
    if existing_review:
        return Response(content="Review already requested for this artifact", status_code=400)

    new_review_request = ArtifactReviewStatus(
        artifact_id=artifact_id,
    )

    db.add(new_review_request)
    db.commit()
    db.refresh(new_review_request)

    return Response(content="Review requested successfully", status_code=200)


@router.get("/review-requests", response_model=list[KnowledgeArtifactResponse])
async def list_review_requests(
    current_user: User = Depends(auth_user),
    db=Depends(get_db)
):
    if current_user.role not in [SystemRole.KNOWLEDGE_CHAMPION, SystemRole.ADMIN]:
        return Response(content="Permission denied. Only Knowledge Champions and Admins can view review requests.", status_code=403)

    review_requests = db.query(KnowledgeArtifact).join(ArtifactReviewStatus).options(joinedload(KnowledgeArtifact.review)).filter(ArtifactReviewStatus.decision != ReviewDecision.APPROVED).all()
    return review_requests


@router.post("/review-artifact/{artifact_id}")
async def review_artifact(
    artifact_id: uuid.UUID,
    data: ArtifactReviewStatusForm,
    current_user: User = Depends(auth_user),
    db=Depends(get_db)
):
    artifact = db.query(KnowledgeArtifact).filter(KnowledgeArtifact.id == artifact_id).first()
    if not artifact:
        return Response(content="Artifact not found", status_code=404)
    
    review = db.query(ArtifactReviewStatus).filter(ArtifactReviewStatus.artifact_id == artifact_id).first()
    if not review:
        return Response(content="No review request found for this artifact", status_code=404)
    
    if not current_user.role in [SystemRole.KNOWLEDGE_CHAMPION, SystemRole.ADMIN]:
        return Response(content="Permission denied. Only Knowledge Champions and Admins can review artifacts.", status_code=403)

    review.decision = data.decision
    print(f"Review decision: {data.decision}, comments: {data.comments}")
    review.comments = data.comments
    review.reviewed_by = current_user.id

    db.commit()
    db.refresh(review)

    return Response(content="Artifact reviewed successfully", status_code=200)


@router.post("/rate-artifact/{artifact_id}", response_model=RatingResponse)
async def rate_artifact(
    artifact_id: uuid.UUID,
    data: RatingForm,
    current_user: User = Depends(auth_user),
    db=Depends(get_db)
):
    artifact = db.query(KnowledgeArtifact).filter(KnowledgeArtifact.id == artifact_id).first()
    if not artifact:
        return Response(content="Artifact not found", status_code=404)

    new_rating = Rating(
        artifact_id=artifact_id,
        user_id=current_user.id,
        score=data.rating_value,
        comment=data.comment,
    )

    db.add(new_rating)
    db.commit()
    db.refresh(new_rating)

    return new_rating



from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from backend.database.schema import User
from backend.services.auth_service import get_db, hash_password, verify_password, create_access_token, get_current_user
from backend.schemas import UserRegister, UserLogin, SocialLoginRequest, TokenResponse, UserResponse
from backend.services.oauth_service import (
    get_google_auth_url, exchange_google_code, get_google_user_info,
    get_github_auth_url, exchange_github_code, get_github_user_info,
    get_microsoft_auth_url, exchange_microsoft_code, get_microsoft_user_info
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/register", response_model=TokenResponse)
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="User with this email already exists")

    new_user = User(
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        full_name=user_data.full_name,
        role=user_data.role or "PARTICIPANT",
        auth_provider="EMAIL",
        last_login=datetime.utcnow()
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = create_access_token({"sub": new_user.id, "role": new_user.role})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": UserResponse.model_validate(new_user)
    }

@router.post("/login", response_model=TokenResponse)
def login(login_data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == login_data.email).first()
    
    if not user:
        user = User(
            email=login_data.email,
            password_hash=hash_password(login_data.password),
            full_name=login_data.email.split("@")[0].capitalize(),
            role="PARTICIPANT",
            auth_provider="EMAIL",
            last_login=datetime.utcnow()
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        if not verify_password(login_data.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        user.last_login = datetime.utcnow()
        db.commit()

    if not user.is_active:
        raise HTTPException(status_code=403, detail="User account is deactivated")

    token = create_access_token({"sub": user.id, "role": user.role})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": UserResponse.model_validate(user)
    }

# --- Google OAuth Endpoints ---
@router.get("/google/login")
def google_login():
    try:
        url = get_google_auth_url()
        return RedirectResponse(url=url)
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(ve)
        )

@router.get("/google/callback")
async def google_callback(code: str = Query(...), state: Optional[str] = None, db: Session = Depends(get_db)):
    try:
        token_data = await exchange_google_code(code)
        access_token = token_data.get("access_token")
        user_info = await get_google_user_info(access_token)

        user = _create_or_update_oauth_user(db, provider="GOOGLE", info=user_info)
        token = create_access_token({"sub": user.id, "role": user.role})

        return RedirectResponse(url=f"/#token={token}&provider=GOOGLE")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Google OAuth authentication failed: {str(e)}")

# --- GitHub OAuth Endpoints ---
@router.get("/github/login")
def github_login():
    try:
        url = get_github_auth_url()
        return RedirectResponse(url=url)
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(ve)
        )

@router.get("/github/callback")
async def github_callback(code: str = Query(...), state: Optional[str] = None, db: Session = Depends(get_db)):
    try:
        token_data = await exchange_github_code(code)
        access_token = token_data.get("access_token")
        user_info = await get_github_user_info(access_token)

        user = _create_or_update_oauth_user(db, provider="GITHUB", info=user_info)
        token = create_access_token({"sub": user.id, "role": user.role})

        return RedirectResponse(url=f"/#token={token}&provider=GITHUB")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"GitHub OAuth authentication failed: {str(e)}")

# --- Microsoft OAuth Endpoints ---
@router.get("/microsoft/login")
def microsoft_login():
    try:
        url = get_microsoft_auth_url()
        return RedirectResponse(url=url)
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(ve)
        )

@router.get("/microsoft/callback")
async def microsoft_callback(code: str = Query(...), state: Optional[str] = None, db: Session = Depends(get_db)):
    try:
        token_data = await exchange_microsoft_code(code)
        access_token = token_data.get("access_token")
        user_info = await get_microsoft_user_info(access_token)

        user = _create_or_update_oauth_user(db, provider="MICROSOFT", info=user_info)
        token = create_access_token({"sub": user.id, "role": user.role})

        return RedirectResponse(url=f"/#token={token}&provider=MICROSOFT")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Microsoft OAuth authentication failed: {str(e)}")

# --- Shared Social & Local Fallback ---
@router.post("/social-login", response_model=TokenResponse)
def social_login(req: SocialLoginRequest, db: Session = Depends(get_db)):
    provider_name = req.provider.upper()
    info = {
        "provider_user_id": req.provider_user_id or req.email,
        "email": req.email,
        "name": req.full_name,
        "picture": req.profile_image
    }
    user = _create_or_update_oauth_user(db, provider=provider_name, info=info)
    token = create_access_token({"sub": user.id, "role": user.role})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": UserResponse.model_validate(user)
    }

@router.post("/logout")
def logout(current_user: User = Depends(get_current_user)):
    return {"success": True, "message": "Successfully logged out"}

@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)

# Helper function to create or update OAuth user record safely
def _create_or_update_oauth_user(db: Session, provider: str, info: dict) -> User:
    email = info.get("email")
    provider_user_id = info.get("provider_user_id")
    full_name = info.get("name") or email.split("@")[0].capitalize()
    picture = info.get("picture")

    # 1. Search by provider and provider_user_id
    user = db.query(User).filter(
        User.auth_provider == provider,
        User.provider_user_id == provider_user_id
    ).first()

    # 2. If not found by provider_user_id, search by email
    if not user:
        user = db.query(User).filter(User.email == email).first()

    if user:
        user.auth_provider = provider
        user.provider_user_id = provider_user_id
        if picture:
            user.profile_image = picture
        if full_name:
            user.full_name = full_name
        user.last_login = datetime.utcnow()
        db.commit()
        db.refresh(user)
    else:
        user = User(
            email=email,
            password_hash=hash_password(f"oauth-secret-{provider}-{email}"),
            full_name=full_name,
            role="PARTICIPANT",
            auth_provider=provider,
            provider_user_id=provider_user_id,
            profile_image=picture,
            last_login=datetime.utcnow()
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    return user

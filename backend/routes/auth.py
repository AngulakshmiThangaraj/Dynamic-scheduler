from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.database.schema import User
from backend.services.auth_service import get_db, hash_password, verify_password, create_access_token, get_current_user
from backend.schemas import UserRegister, UserLogin, SocialLoginRequest, TokenResponse, UserResponse

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
        role=user_data.role or "PARTICIPANT"
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
    
    # Auto-register user if not present (convenience mode for new emails)
    if not user:
        user = User(
            email=login_data.email,
            password_hash=hash_password(login_data.password),
            full_name=login_data.email.split("@")[0].capitalize(),
            role="PARTICIPANT"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        if not verify_password(login_data.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="User account is deactivated")

    token = create_access_token({"sub": user.id, "role": user.role})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": UserResponse.model_validate(user)
    }

@router.post("/social-login", response_model=TokenResponse)
def social_login(req: SocialLoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user:
        user = User(
            email=req.email,
            password_hash=hash_password(f"social-oauth-{req.email}"),
            full_name=req.full_name or req.email.split("@")[0].capitalize(),
            role="PARTICIPANT"
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    token = create_access_token({"sub": user.id, "role": user.role})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": UserResponse.model_validate(user)
    }

@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)

# Phase 1: Config Service Implementation

## Objective

Build the Config Service - a FastAPI application that handles user authentication, user management, configuration CRUD, folder scanning, and YAML export/import.

## Prerequisites

- Phase 0 completed (shared models exist in `shared/python/rag_config_common/`)
- MongoDB running on `localhost:27017`
- Redis running on `localhost:6379`

## Task Overview

| Task ID | Task | Description |
|---------|------|-------------|
| P1-1 | FastAPI Scaffold | Create config-service structure with main.py |
| P1-2 | MongoDB Connection | Implement async MongoDB client |
| P1-3 | User Repository | Implement user CRUD operations |
| P1-4 | Auth Endpoints | Implement register, login, refresh, logout |
| P1-5 | JWT Middleware | Implement JWT validation dependency |
| P1-6 | Config Repository | Implement config CRUD operations |
| P1-7 | Config Endpoints | Implement config CRUD API |
| P1-8 | Folder Scanner | Implement local folder scanning |
| P1-9 | Folder Endpoints | Implement folder scan API |
| P1-10 | YAML Export | Implement config export/import |
| P1-11 | Tests | Unit and integration tests |

---

## Task P1-1: FastAPI Scaffold

Create the basic FastAPI application structure.

### File: `services/config-service/app/main.py`

```python
"""Config Service - Main FastAPI Application."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.settings import settings
from app.db.mongodb import mongodb


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    await mongodb.connect()
    yield
    # Shutdown
    await mongodb.disconnect()


app = FastAPI(
    title="RAG Configurator - Config Service",
    description="Configuration management service for RAG pipelines",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "config-service"}
```

### File: `services/config-service/app/core/settings.py`

```python
"""Application settings using Pydantic Settings."""

from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
    
    # Application
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    
    # MongoDB
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DATABASE: str = "rag_configurator"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # JWT
    JWT_SECRET_KEY: str = "change-this-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:3001"]
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Return CORS origins as list."""
        if isinstance(self.CORS_ORIGINS, str):
            return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
        return self.CORS_ORIGINS


settings = Settings()
```

### File: `services/config-service/app/core/exceptions.py`

```python
"""Custom exceptions for the Config Service."""

from fastapi import HTTPException, status


class NotFoundException(HTTPException):
    """Resource not found exception."""
    
    def __init__(self, resource: str, id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource} with id '{id}' not found",
        )


class AlreadyExistsException(HTTPException):
    """Resource already exists exception."""
    
    def __init__(self, resource: str, field: str, value: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{resource} with {field} '{value}' already exists",
        )


class UnauthorizedException(HTTPException):
    """Unauthorized access exception."""
    
    def __init__(self, detail: str = "Could not validate credentials"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class ForbiddenException(HTTPException):
    """Forbidden access exception."""
    
    def __init__(self, detail: str = "Not enough permissions"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


class ValidationException(HTTPException):
    """Validation error exception."""
    
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
        )
```

### File: `services/config-service/app/api/v1/router.py`

```python
"""API v1 router aggregating all endpoints."""

from fastapi import APIRouter

from app.api.v1 import auth, users, configs, folders, export

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(configs.router)
api_router.include_router(folders.router)
api_router.include_router(export.router)
```

### File: `services/config-service/requirements.txt`

```
# FastAPI and server
fastapi==0.111.0
uvicorn[standard]==0.30.1
python-multipart==0.0.9

# Database
motor==3.4.0
pymongo==4.7.2

# Authentication
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4

# Settings
pydantic-settings==2.3.0

# Validation
email-validator==2.1.1

# YAML
pyyaml==6.0.1

# Shared models (install from local)
# pip install -e ../../shared/python

# Testing
pytest==8.2.2
pytest-asyncio==0.23.7
pytest-cov==5.0.0
httpx==0.27.0

# Development
ruff==0.4.8
black==24.4.2
```

### File: `services/config-service/pyproject.toml`

```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "config-service"
version = "1.0.0"
description = "RAG Configurator - Config Service"
requires-python = ">=3.11"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
line-length = 88
select = ["E", "F", "I", "N", "W"]
ignore = ["E501"]

[tool.black]
line-length = 88
target-version = ["py311"]
```

---

## Task P1-2: MongoDB Connection

### File: `services/config-service/app/db/mongodb.py`

```python
"""MongoDB connection handler."""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.settings import settings


class MongoDB:
    """MongoDB connection manager."""
    
    client: AsyncIOMotorClient | None = None
    
    async def connect(self) -> None:
        """Connect to MongoDB."""
        self.client = AsyncIOMotorClient(settings.MONGODB_URI)
        # Verify connection
        await self.client.admin.command("ping")
        print(f"Connected to MongoDB: {settings.MONGODB_DATABASE}")
    
    async def disconnect(self) -> None:
        """Disconnect from MongoDB."""
        if self.client:
            self.client.close()
            print("Disconnected from MongoDB")
    
    def get_database(self) -> AsyncIOMotorDatabase:
        """Get the database instance."""
        if not self.client:
            raise RuntimeError("MongoDB client not initialized")
        return self.client[settings.MONGODB_DATABASE]


mongodb = MongoDB()


def get_db() -> AsyncIOMotorDatabase:
    """Dependency to get database instance."""
    return mongodb.get_database()
```

---

## Task P1-3: User Repository

### File: `services/config-service/app/db/repositories/base.py`

```python
"""Base repository with common CRUD operations."""

from typing import Optional, List, TypeVar, Generic
from datetime import datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """Base repository class with common CRUD operations."""
    
    def __init__(self, db: AsyncIOMotorDatabase, collection_name: str):
        self.collection = db[collection_name]
    
    async def find_by_id(self, id: str) -> Optional[dict]:
        """Find document by ID."""
        if not ObjectId.is_valid(id):
            return None
        return await self.collection.find_one({"_id": ObjectId(id)})
    
    async def find_one(self, filter: dict) -> Optional[dict]:
        """Find single document by filter."""
        return await self.collection.find_one(filter)
    
    async def find_many(
        self,
        filter: dict,
        skip: int = 0,
        limit: int = 100,
        sort: Optional[List[tuple]] = None,
    ) -> List[dict]:
        """Find multiple documents with pagination."""
        cursor = self.collection.find(filter).skip(skip).limit(limit)
        if sort:
            cursor = cursor.sort(sort)
        return await cursor.to_list(length=limit)
    
    async def count(self, filter: dict) -> int:
        """Count documents matching filter."""
        return await self.collection.count_documents(filter)
    
    async def insert_one(self, document: dict) -> str:
        """Insert single document."""
        document["created_at"] = datetime.utcnow()
        document["updated_at"] = datetime.utcnow()
        result = await self.collection.insert_one(document)
        return str(result.inserted_id)
    
    async def update_one(self, id: str, update: dict) -> bool:
        """Update single document."""
        if not ObjectId.is_valid(id):
            return False
        update["updated_at"] = datetime.utcnow()
        result = await self.collection.update_one(
            {"_id": ObjectId(id)},
            {"$set": update}
        )
        return result.modified_count > 0
    
    async def delete_one(self, id: str) -> bool:
        """Delete single document."""
        if not ObjectId.is_valid(id):
            return False
        result = await self.collection.delete_one({"_id": ObjectId(id)})
        return result.deleted_count > 0
    
    @staticmethod
    def serialize_doc(doc: dict) -> dict:
        """Convert MongoDB document to serializable dict."""
        if doc and "_id" in doc:
            doc["id"] = str(doc.pop("_id"))
        return doc
```

### File: `services/config-service/app/db/repositories/user_repo.py`

```python
"""User repository for database operations."""

from typing import Optional
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.repositories.base import BaseRepository


class UserRepository(BaseRepository):
    """Repository for user operations."""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db, "users")
    
    async def find_by_email(self, email: str) -> Optional[dict]:
        """Find user by email address."""
        return await self.find_one({"email": email.lower()})
    
    async def create_user(self, user_data: dict) -> str:
        """Create a new user."""
        user_data["email"] = user_data["email"].lower()
        user_data["is_active"] = True
        return await self.insert_one(user_data)
    
    async def update_user(self, user_id: str, update_data: dict) -> bool:
        """Update user data."""
        if "email" in update_data:
            update_data["email"] = update_data["email"].lower()
        return await self.update_one(user_id, update_data)
    
    async def deactivate_user(self, user_id: str) -> bool:
        """Soft delete user by deactivating."""
        return await self.update_one(user_id, {"is_active": False})
```

---

## Task P1-4: Auth Endpoints

### File: `services/config-service/app/core/security.py`

```python
"""Security utilities for authentication."""

from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.settings import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate password hash."""
    return pwd_context.hash(password)


def create_access_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create JWT access token."""
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode = {
        "exp": expire,
        "sub": subject,
        "type": "access",
        "iat": datetime.utcnow(),
    }
    return jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def create_refresh_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create JWT refresh token."""
    expire = datetime.utcnow() + (
        expires_delta or timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    )
    to_encode = {
        "exp": expire,
        "sub": subject,
        "type": "refresh",
        "iat": datetime.utcnow(),
    }
    return jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_token(token: str) -> Optional[dict]:
    """Decode and validate JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except JWTError:
        return None
```

### File: `services/config-service/app/schemas/auth.py`

```python
"""Authentication request/response schemas."""

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """User registration request."""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    name: str = Field(..., min_length=1, max_length=100)


class LoginRequest(BaseModel):
    """User login request."""
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    """Token refresh request."""
    refresh_token: str


class TokenResponse(BaseModel):
    """Authentication token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class MessageResponse(BaseModel):
    """Simple message response."""
    message: str
```

### File: `services/config-service/app/schemas/user.py`

```python
"""User schemas for request/response."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserResponse(BaseModel):
    """User response schema."""
    id: str
    email: EmailStr
    name: str
    created_at: datetime
    updated_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """User update request schema."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
```

### File: `services/config-service/app/services/auth_service.py`

```python
"""Authentication service with business logic."""

from typing import Optional
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.core.settings import settings
from app.core.exceptions import (
    UnauthorizedException,
    AlreadyExistsException,
)
from app.db.repositories.user_repo import UserRepository
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse


class AuthService:
    """Service for authentication operations."""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.user_repo = UserRepository(db)
    
    async def register(self, data: RegisterRequest) -> TokenResponse:
        """Register a new user."""
        # Check if user exists
        existing = await self.user_repo.find_by_email(data.email)
        if existing:
            raise AlreadyExistsException("User", "email", data.email)
        
        # Create user
        user_data = {
            "email": data.email,
            "name": data.name,
            "password_hash": get_password_hash(data.password),
        }
        user_id = await self.user_repo.create_user(user_data)
        
        # Generate tokens
        return self._create_tokens(user_id)
    
    async def login(self, data: LoginRequest) -> TokenResponse:
        """Authenticate user and return tokens."""
        user = await self.user_repo.find_by_email(data.email)
        
        if not user:
            raise UnauthorizedException("Invalid email or password")
        
        if not user.get("is_active", False):
            raise UnauthorizedException("Account is deactivated")
        
        if not verify_password(data.password, user["password_hash"]):
            raise UnauthorizedException("Invalid email or password")
        
        return self._create_tokens(str(user["_id"]))
    
    async def refresh(self, refresh_token: str) -> TokenResponse:
        """Refresh access token using refresh token."""
        payload = decode_token(refresh_token)
        
        if not payload:
            raise UnauthorizedException("Invalid refresh token")
        
        if payload.get("type") != "refresh":
            raise UnauthorizedException("Invalid token type")
        
        user_id = payload.get("sub")
        if not user_id:
            raise UnauthorizedException("Invalid token payload")
        
        # Verify user still exists and is active
        user = await self.user_repo.find_by_id(user_id)
        if not user or not user.get("is_active", False):
            raise UnauthorizedException("User not found or deactivated")
        
        return self._create_tokens(user_id)
    
    def _create_tokens(self, user_id: str) -> TokenResponse:
        """Create access and refresh tokens."""
        access_token = create_access_token(user_id)
        refresh_token = create_refresh_token(user_id)
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
```

### File: `services/config-service/app/api/v1/auth.py`

```python
"""Authentication endpoints."""

from fastapi import APIRouter, Depends, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.mongodb import get_db
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    RefreshRequest,
    TokenResponse,
    MessageResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user",
)
async def register(
    data: RegisterRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> TokenResponse:
    """
    Register a new user account.
    
    Returns access and refresh tokens upon successful registration.
    """
    service = AuthService(db)
    return await service.register(data)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="User login",
)
async def login(
    data: LoginRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> TokenResponse:
    """
    Authenticate user with email and password.
    
    Returns access and refresh tokens upon successful authentication.
    """
    service = AuthService(db)
    return await service.login(data)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
)
async def refresh(
    data: RefreshRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> TokenResponse:
    """
    Refresh access token using a valid refresh token.
    """
    service = AuthService(db)
    return await service.refresh(data.refresh_token)


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="User logout",
)
async def logout() -> MessageResponse:
    """
    Logout user.
    
    Note: With JWT, actual token invalidation requires a token blacklist
    which is not implemented in this basic version. The client should
    discard the tokens.
    """
    return MessageResponse(message="Successfully logged out")
```

---

## Task P1-5: JWT Middleware (Dependencies)

### File: `services/config-service/app/api/deps.py`

```python
"""API dependencies for dependency injection."""

from typing import Annotated
from fastapi import Depends, Header
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.mongodb import get_db
from app.db.repositories.user_repo import UserRepository
from app.core.security import decode_token
from app.core.exceptions import UnauthorizedException
from app.schemas.user import UserResponse


async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> UserResponse:
    """
    Dependency to get current authenticated user from JWT token.
    
    Extracts the Bearer token from Authorization header,
    validates it, and returns the user.
    """
    if not authorization:
        raise UnauthorizedException("Authorization header missing")
    
    # Extract token from "Bearer <token>"
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise UnauthorizedException("Invalid authorization header format")
    
    token = parts[1]
    
    # Decode and validate token
    payload = decode_token(token)
    if not payload:
        raise UnauthorizedException("Invalid or expired token")
    
    if payload.get("type") != "access":
        raise UnauthorizedException("Invalid token type")
    
    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedException("Invalid token payload")
    
    # Get user from database
    user_repo = UserRepository(db)
    user = await user_repo.find_by_id(user_id)
    
    if not user:
        raise UnauthorizedException("User not found")
    
    if not user.get("is_active", False):
        raise UnauthorizedException("User account is deactivated")
    
    # Serialize and return
    user = UserRepository.serialize_doc(user)
    return UserResponse(**user)


# Type alias for cleaner dependency injection
CurrentUser = Annotated[UserResponse, Depends(get_current_user)]
```

---

## Task P1-6: Config Repository

### File: `services/config-service/app/db/repositories/config_repo.py`

```python
"""Configuration repository for database operations."""

from typing import Optional, List
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.repositories.base import BaseRepository


class ConfigRepository(BaseRepository):
    """Repository for RAG pipeline configuration operations."""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db, "configs")
    
    async def find_by_user(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[dict]:
        """Find all configurations for a user."""
        return await self.find_many(
            filter={"created_by": user_id},
            skip=skip,
            limit=limit,
            sort=[("created_at", -1)],
        )
    
    async def count_by_user(self, user_id: str) -> int:
        """Count configurations for a user."""
        return await self.count({"created_by": user_id})
    
    async def find_by_name(self, user_id: str, name: str) -> Optional[dict]:
        """Find configuration by name for a user."""
        return await self.find_one({
            "created_by": user_id,
            "name": name,
        })
    
    async def create_config(self, config_data: dict) -> str:
        """Create a new configuration."""
        return await self.insert_one(config_data)
    
    async def update_config(self, config_id: str, update_data: dict) -> bool:
        """Update configuration."""
        return await self.update_one(config_id, update_data)
    
    async def is_owner(self, config_id: str, user_id: str) -> bool:
        """Check if user owns the configuration."""
        config = await self.find_by_id(config_id)
        return config is not None and config.get("created_by") == user_id
```

---

## Task P1-7: Config Endpoints

### File: `services/config-service/app/schemas/config.py`

```python
"""Configuration schemas for request/response."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

from rag_config_common.models.enums import IngestionStatus
from rag_config_common.models.config import (
    DataSourceConfig,
    RBACConfig,
    ModelConfig,
    RetrievalConfig,
    ChunkingConfig,
    AgentConfig,
    PromptConfig,
)


class ConfigCreate(BaseModel):
    """Configuration creation request."""
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="")
    data_source: DataSourceConfig
    rbac: Optional[RBACConfig] = None
    models: ModelConfig
    retrieval: RetrievalConfig
    chunking: Optional[ChunkingConfig] = None
    agent: AgentConfig
    prompts: PromptConfig


class ConfigUpdate(BaseModel):
    """Configuration update request."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    data_source: Optional[DataSourceConfig] = None
    rbac: Optional[RBACConfig] = None
    models: Optional[ModelConfig] = None
    retrieval: Optional[RetrievalConfig] = None
    chunking: Optional[ChunkingConfig] = None
    agent: Optional[AgentConfig] = None
    prompts: Optional[PromptConfig] = None


class ConfigSummary(BaseModel):
    """Configuration summary for list views."""
    id: str
    name: str
    description: str
    status: IngestionStatus
    created_at: datetime
    updated_at: datetime


class ConfigResponse(BaseModel):
    """Full configuration response."""
    id: str
    name: str
    description: str
    version: str
    created_by: str
    created_at: datetime
    updated_at: datetime
    status: IngestionStatus
    api_endpoint: Optional[str] = None
    data_source: DataSourceConfig
    rbac: RBACConfig
    models: ModelConfig
    retrieval: RetrievalConfig
    chunking: ChunkingConfig
    agent: AgentConfig
    prompts: PromptConfig
    stats: Optional[dict] = None


class ConfigListResponse(BaseModel):
    """Paginated configuration list response."""
    items: List[ConfigSummary]
    total: int
    page: int
    page_size: int
```

### File: `services/config-service/app/services/config_service.py`

```python
"""Configuration service with business logic."""

from typing import Optional
from motor.motor_asyncio import AsyncIOMotorDatabase

from rag_config_common.models.enums import IngestionStatus
from rag_config_common.models.config import RBACConfig, ChunkingConfig

from app.core.exceptions import NotFoundException, AlreadyExistsException, ForbiddenException
from app.db.repositories.config_repo import ConfigRepository
from app.schemas.config import (
    ConfigCreate,
    ConfigUpdate,
    ConfigResponse,
    ConfigSummary,
    ConfigListResponse,
)


class ConfigService:
    """Service for configuration operations."""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.config_repo = ConfigRepository(db)
    
    async def create(self, data: ConfigCreate, user_id: str) -> ConfigResponse:
        """Create a new configuration."""
        # Check for duplicate name
        existing = await self.config_repo.find_by_name(user_id, data.name)
        if existing:
            raise AlreadyExistsException("Configuration", "name", data.name)
        
        # Prepare config document
        config_data = data.model_dump()
        config_data["created_by"] = user_id
        config_data["version"] = "1.0.0"
        config_data["status"] = IngestionStatus.PENDING.value
        config_data["api_endpoint"] = None
        config_data["stats"] = None
        
        # Set defaults for optional fields
        if config_data.get("rbac") is None:
            config_data["rbac"] = RBACConfig().model_dump()
        if config_data.get("chunking") is None:
            config_data["chunking"] = ChunkingConfig().model_dump()
        
        # Create config
        config_id = await self.config_repo.create_config(config_data)
        
        # Fetch and return created config
        return await self.get_by_id(config_id, user_id)
    
    async def get_by_id(self, config_id: str, user_id: str) -> ConfigResponse:
        """Get configuration by ID."""
        config = await self.config_repo.find_by_id(config_id)
        
        if not config:
            raise NotFoundException("Configuration", config_id)
        
        if config.get("created_by") != user_id:
            raise ForbiddenException("You don't have access to this configuration")
        
        config = ConfigRepository.serialize_doc(config)
        return ConfigResponse(**config)
    
    async def list(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> ConfigListResponse:
        """List configurations for a user."""
        skip = (page - 1) * page_size
        
        configs = await self.config_repo.find_by_user(user_id, skip, page_size)
        total = await self.config_repo.count_by_user(user_id)
        
        items = [
            ConfigSummary(**ConfigRepository.serialize_doc(c))
            for c in configs
        ]
        
        return ConfigListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )
    
    async def update(
        self,
        config_id: str,
        data: ConfigUpdate,
        user_id: str,
    ) -> ConfigResponse:
        """Update configuration."""
        # Verify ownership
        if not await self.config_repo.is_owner(config_id, user_id):
            config = await self.config_repo.find_by_id(config_id)
            if not config:
                raise NotFoundException("Configuration", config_id)
            raise ForbiddenException("You don't have access to this configuration")
        
        # Check for duplicate name if name is being changed
        if data.name:
            existing = await self.config_repo.find_by_name(user_id, data.name)
            if existing and str(existing["_id"]) != config_id:
                raise AlreadyExistsException("Configuration", "name", data.name)
        
        # Update only provided fields
        update_data = data.model_dump(exclude_unset=True)
        
        if update_data:
            await self.config_repo.update_config(config_id, update_data)
        
        return await self.get_by_id(config_id, user_id)
    
    async def delete(self, config_id: str, user_id: str) -> bool:
        """Delete configuration."""
        if not await self.config_repo.is_owner(config_id, user_id):
            config = await self.config_repo.find_by_id(config_id)
            if not config:
                raise NotFoundException("Configuration", config_id)
            raise ForbiddenException("You don't have access to this configuration")
        
        return await self.config_repo.delete_one(config_id)
    
    async def duplicate(self, config_id: str, user_id: str, new_name: str) -> ConfigResponse:
        """Duplicate a configuration."""
        original = await self.config_repo.find_by_id(config_id)
        
        if not original:
            raise NotFoundException("Configuration", config_id)
        
        if original.get("created_by") != user_id:
            raise ForbiddenException("You don't have access to this configuration")
        
        # Check for duplicate name
        existing = await self.config_repo.find_by_name(user_id, new_name)
        if existing:
            raise AlreadyExistsException("Configuration", "name", new_name)
        
        # Create copy
        new_config = original.copy()
        del new_config["_id"]
        new_config["name"] = new_name
        new_config["status"] = IngestionStatus.PENDING.value
        new_config["api_endpoint"] = None
        new_config["stats"] = None
        
        config_id = await self.config_repo.create_config(new_config)
        return await self.get_by_id(config_id, user_id)
```

### File: `services/config-service/app/api/v1/configs.py`

```python
"""Configuration CRUD endpoints."""

from fastapi import APIRouter, Depends, status, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.mongodb import get_db
from app.api.deps import CurrentUser
from app.schemas.config import (
    ConfigCreate,
    ConfigUpdate,
    ConfigResponse,
    ConfigListResponse,
)
from app.schemas.auth import MessageResponse
from app.services.config_service import ConfigService

router = APIRouter(prefix="/configs", tags=["configurations"])


@router.get(
    "/",
    response_model=ConfigListResponse,
    summary="List configurations",
)
async def list_configs(
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> ConfigListResponse:
    """
    List all configurations for the current user.
    
    Supports pagination with page and page_size parameters.
    """
    service = ConfigService(db)
    return await service.list(current_user.id, page, page_size)


@router.post(
    "/",
    response_model=ConfigResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create configuration",
)
async def create_config(
    data: ConfigCreate,
    current_user: CurrentUser,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> ConfigResponse:
    """
    Create a new RAG pipeline configuration.
    """
    service = ConfigService(db)
    return await service.create(data, current_user.id)


@router.get(
    "/{config_id}",
    response_model=ConfigResponse,
    summary="Get configuration",
)
async def get_config(
    config_id: str,
    current_user: CurrentUser,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> ConfigResponse:
    """
    Get a specific configuration by ID.
    """
    service = ConfigService(db)
    return await service.get_by_id(config_id, current_user.id)


@router.put(
    "/{config_id}",
    response_model=ConfigResponse,
    summary="Update configuration",
)
async def update_config(
    config_id: str,
    data: ConfigUpdate,
    current_user: CurrentUser,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> ConfigResponse:
    """
    Update an existing configuration.
    
    Only provided fields will be updated.
    """
    service = ConfigService(db)
    return await service.update(config_id, data, current_user.id)


@router.delete(
    "/{config_id}",
    response_model=MessageResponse,
    summary="Delete configuration",
)
async def delete_config(
    config_id: str,
    current_user: CurrentUser,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> MessageResponse:
    """
    Delete a configuration.
    """
    service = ConfigService(db)
    await service.delete(config_id, current_user.id)
    return MessageResponse(message="Configuration deleted successfully")


@router.post(
    "/{config_id}/duplicate",
    response_model=ConfigResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Duplicate configuration",
)
async def duplicate_config(
    config_id: str,
    new_name: str = Query(..., min_length=1, max_length=100),
    current_user: CurrentUser,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> ConfigResponse:
    """
    Create a copy of an existing configuration with a new name.
    """
    service = ConfigService(db)
    return await service.duplicate(config_id, current_user.id, new_name)
```

---

## Task P1-8: Folder Scanner

### File: `services/config-service/app/services/folder_service.py`

```python
"""Folder scanning service."""

import os
from pathlib import Path
from typing import List, Set

from rag_config_common.models.enums import DataType

from app.schemas.folder import FolderInfo, FolderScanResponse, FolderScanRequest


# File extension to DataType mapping
EXTENSION_MAP = {
    ".txt": DataType.TEXT,
    ".md": DataType.MARKDOWN,
    ".markdown": DataType.MARKDOWN,
    ".pdf": DataType.PDF,
    ".png": DataType.IMAGE,
    ".jpg": DataType.IMAGE,
    ".jpeg": DataType.IMAGE,
    ".gif": DataType.IMAGE,
    ".webp": DataType.IMAGE,
    ".docx": DataType.DOCX,
    ".doc": DataType.DOCX,
    ".xlsx": DataType.XLSX,
    ".xls": DataType.XLSX,
    ".csv": DataType.CSV,
}

# Image/complex file types that indicate multimodal
MULTIMODAL_TYPES = {DataType.IMAGE, DataType.PDF}


class FolderService:
    """Service for scanning and analyzing folders."""
    
    def scan(self, request: FolderScanRequest) -> FolderScanResponse:
        """
        Scan a directory and return folder structure with detected file types.
        
        Currently supports local file system only.
        """
        if request.type != "local":
            raise NotImplementedError(f"Data source type '{request.type}' not yet supported")
        
        base_path = Path(request.base_path)
        
        if not base_path.exists():
            raise ValueError(f"Path does not exist: {request.base_path}")
        
        if not base_path.is_dir():
            raise ValueError(f"Path is not a directory: {request.base_path}")
        
        # Scan folder recursively
        folders, all_types = self._scan_directory(base_path, base_path)
        
        # Determine if multimodal content exists
        has_multimodal = bool(all_types & MULTIMODAL_TYPES)
        
        return FolderScanResponse(
            base_path=str(base_path.absolute()),
            folders=folders,
            has_multimodal=has_multimodal,
        )
    
    def _scan_directory(
        self,
        path: Path,
        base_path: Path,
        max_depth: int = 5,
        current_depth: int = 0,
    ) -> tuple[List[FolderInfo], Set[DataType]]:
        """
        Recursively scan a directory.
        
        Returns tuple of (folder_infos, all_detected_types).
        """
        if current_depth >= max_depth:
            return [], set()
        
        folders = []
        all_types: Set[DataType] = set()
        
        try:
            for item in sorted(path.iterdir()):
                # Skip hidden files/folders
                if item.name.startswith("."):
                    continue
                
                if item.is_dir():
                    # Recursively scan subdirectory
                    children, child_types = self._scan_directory(
                        item, base_path, max_depth, current_depth + 1
                    )
                    
                    # Get direct files in this folder
                    detected_types, file_count = self._analyze_folder(item)
                    
                    # Combine types from this folder and children
                    combined_types = detected_types | child_types
                    all_types |= combined_types
                    
                    # Calculate relative path
                    rel_path = str(item.relative_to(base_path))
                    
                    folders.append(FolderInfo(
                        path=rel_path,
                        name=item.name,
                        detected_types=list(combined_types),
                        file_count=file_count,
                        children=children,
                    ))
        except PermissionError:
            pass  # Skip folders we can't access
        
        return folders, all_types
    
    def _analyze_folder(self, path: Path) -> tuple[Set[DataType], int]:
        """
        Analyze files directly in a folder (not recursive).
        
        Returns tuple of (detected_types, file_count).
        """
        detected_types: Set[DataType] = set()
        file_count = 0
        
        try:
            for item in path.iterdir():
                if item.is_file() and not item.name.startswith("."):
                    file_count += 1
                    ext = item.suffix.lower()
                    if ext in EXTENSION_MAP:
                        detected_types.add(EXTENSION_MAP[ext])
        except PermissionError:
            pass
        
        return detected_types, file_count
```

### File: `services/config-service/app/schemas/folder.py`

```python
"""Folder scanning schemas."""

from typing import List, Optional
from pydantic import BaseModel, Field

from rag_config_common.models.enums import DataType, DataSourceType


class FolderScanRequest(BaseModel):
    """Request to scan a folder."""
    type: DataSourceType = DataSourceType.LOCAL
    base_path: str = Field(..., description="Path to scan")
    credentials: Optional[dict] = Field(None, description="Cloud credentials if needed")


class FolderInfo(BaseModel):
    """Information about a scanned folder."""
    path: str
    name: str
    detected_types: List[DataType] = []
    file_count: int = 0
    children: List["FolderInfo"] = []


class FolderScanResponse(BaseModel):
    """Response from folder scan."""
    base_path: str
    folders: List[FolderInfo]
    has_multimodal: bool


# Update forward refs for recursive model
FolderInfo.model_rebuild()
```

---

## Task P1-9: Folder Endpoints

### File: `services/config-service/app/api/v1/folders.py`

```python
"""Folder scanning endpoints."""

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser
from app.schemas.folder import FolderScanRequest, FolderScanResponse
from app.services.folder_service import FolderService

router = APIRouter(prefix="/folders", tags=["folders"])


@router.post(
    "/scan",
    response_model=FolderScanResponse,
    summary="Scan folder structure",
)
async def scan_folders(
    request: FolderScanRequest,
    current_user: CurrentUser,
) -> FolderScanResponse:
    """
    Scan a directory and return its structure with detected file types.
    
    Currently supports local file system. Cloud storage support coming soon.
    """
    try:
        service = FolderService()
        return service.scan(request)
    except NotImplementedError as e:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=str(e),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to scan folder: {str(e)}",
        )
```

---

## Task P1-10: YAML Export/Import

### File: `services/config-service/app/services/export_service.py`

```python
"""Configuration export/import service."""

import yaml
from typing import Any
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.exceptions import NotFoundException, ForbiddenException, ValidationException
from app.db.repositories.config_repo import ConfigRepository
from app.services.config_service import ConfigService
from app.schemas.config import ConfigCreate


class ExportService:
    """Service for exporting and importing configurations."""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.config_repo = ConfigRepository(db)
        self.config_service = ConfigService(db)
    
    async def export_yaml(self, config_id: str, user_id: str) -> str:
        """Export configuration as YAML."""
        config = await self.config_repo.find_by_id(config_id)
        
        if not config:
            raise NotFoundException("Configuration", config_id)
        
        if config.get("created_by") != user_id:
            raise ForbiddenException("You don't have access to this configuration")
        
        # Prepare export data (exclude internal fields)
        export_data = {
            "name": config["name"],
            "description": config.get("description", ""),
            "version": config.get("version", "1.0.0"),
            "data_source": config["data_source"],
            "rbac": config.get("rbac"),
            "models": config["models"],
            "retrieval": config["retrieval"],
            "chunking": config.get("chunking"),
            "agent": config["agent"],
            "prompts": config["prompts"],
        }
        
        # Add metadata as comments
        metadata = {
            "_metadata": {
                "exported_at": datetime.utcnow().isoformat(),
                "original_id": str(config["_id"]),
                "rag_configurator_version": "1.0.0",
            }
        }
        
        # Convert to YAML
        yaml_content = yaml.dump(
            {**metadata, **export_data},
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )
        
        return yaml_content
    
    async def import_yaml(self, yaml_content: str, user_id: str) -> dict:
        """Import configuration from YAML."""
        try:
            data = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            raise ValidationException(f"Invalid YAML format: {str(e)}")
        
        if not isinstance(data, dict):
            raise ValidationException("YAML must contain a configuration object")
        
        # Remove metadata if present
        data.pop("_metadata", None)
        
        # Validate required fields
        required_fields = ["name", "data_source", "models", "retrieval", "agent", "prompts"]
        missing = [f for f in required_fields if f not in data]
        if missing:
            raise ValidationException(f"Missing required fields: {', '.join(missing)}")
        
        try:
            # Validate against schema
            config_create = ConfigCreate(**data)
        except Exception as e:
            raise ValidationException(f"Invalid configuration format: {str(e)}")
        
        # Create the configuration
        result = await self.config_service.create(config_create, user_id)
        return result
```

### File: `services/config-service/app/api/v1/export.py`

```python
"""Configuration export/import endpoints."""

from fastapi import APIRouter, Depends, UploadFile, File, Response, status
from fastapi.responses import PlainTextResponse
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.mongodb import get_db
from app.api.deps import CurrentUser
from app.schemas.config import ConfigResponse
from app.services.export_service import ExportService

router = APIRouter(prefix="/configs", tags=["export"])


@router.get(
    "/{config_id}/export",
    response_class=PlainTextResponse,
    summary="Export configuration as YAML",
)
async def export_config(
    config_id: str,
    current_user: CurrentUser,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Response:
    """
    Export a configuration as a YAML file.
    """
    service = ExportService(db)
    yaml_content = await service.export_yaml(config_id, current_user.id)
    
    return Response(
        content=yaml_content,
        media_type="application/x-yaml",
        headers={
            "Content-Disposition": f"attachment; filename=config-{config_id}.yaml"
        },
    )


@router.post(
    "/import",
    response_model=ConfigResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Import configuration from YAML",
)
async def import_config(
    file: UploadFile = File(...),
    current_user: CurrentUser = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> ConfigResponse:
    """
    Import a configuration from a YAML file.
    """
    # Read file content
    content = await file.read()
    yaml_content = content.decode("utf-8")
    
    service = ExportService(db)
    return await service.import_yaml(yaml_content, current_user.id)
```

---

## Task P1-11: User Endpoints

### File: `services/config-service/app/services/user_service.py`

```python
"""User service with business logic."""

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.exceptions import NotFoundException, AlreadyExistsException
from app.db.repositories.user_repo import UserRepository
from app.schemas.user import UserResponse, UserUpdate


class UserService:
    """Service for user operations."""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.user_repo = UserRepository(db)
    
    async def get_by_id(self, user_id: str) -> UserResponse:
        """Get user by ID."""
        user = await self.user_repo.find_by_id(user_id)
        
        if not user:
            raise NotFoundException("User", user_id)
        
        user = UserRepository.serialize_doc(user)
        return UserResponse(**user)
    
    async def update(self, user_id: str, data: UserUpdate) -> UserResponse:
        """Update user."""
        # Check if email is being changed to an existing email
        if data.email:
            existing = await self.user_repo.find_by_email(data.email)
            if existing and str(existing["_id"]) != user_id:
                raise AlreadyExistsException("User", "email", data.email)
        
        # Update only provided fields
        update_data = data.model_dump(exclude_unset=True)
        
        if update_data:
            success = await self.user_repo.update_user(user_id, update_data)
            if not success:
                raise NotFoundException("User", user_id)
        
        return await self.get_by_id(user_id)
    
    async def delete(self, user_id: str) -> bool:
        """Soft delete user (deactivate)."""
        success = await self.user_repo.deactivate_user(user_id)
        if not success:
            raise NotFoundException("User", user_id)
        return True
```

### File: `services/config-service/app/api/v1/users.py`

```python
"""User management endpoints."""

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.mongodb import get_db
from app.api.deps import CurrentUser
from app.schemas.user import UserResponse, UserUpdate
from app.schemas.auth import MessageResponse
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
)
async def get_current_user_info(
    current_user: CurrentUser,
) -> UserResponse:
    """
    Get the currently authenticated user's information.
    """
    return current_user


@router.put(
    "/me",
    response_model=UserResponse,
    summary="Update current user",
)
async def update_current_user(
    data: UserUpdate,
    current_user: CurrentUser,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> UserResponse:
    """
    Update the current user's information.
    """
    service = UserService(db)
    return await service.update(current_user.id, data)


@router.delete(
    "/me",
    response_model=MessageResponse,
    summary="Delete current user",
)
async def delete_current_user(
    current_user: CurrentUser,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> MessageResponse:
    """
    Delete (deactivate) the current user's account.
    """
    service = UserService(db)
    await service.delete(current_user.id)
    return MessageResponse(message="Account deleted successfully")
```

---

## Task P1-12: Tests

### File: `services/config-service/tests/conftest.py`

```python
"""Pytest fixtures for Config Service tests."""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from motor.motor_asyncio import AsyncIOMotorClient

from app.main import app
from app.db.mongodb import mongodb
from app.core.settings import settings


@pytest_asyncio.fixture
async def test_db():
    """Create a test database connection."""
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[f"{settings.MONGODB_DATABASE}_test"]
    
    # Clear test collections
    for collection in await db.list_collection_names():
        await db[collection].delete_many({})
    
    yield db
    
    # Cleanup
    for collection in await db.list_collection_names():
        await db[collection].delete_many({})
    
    client.close()


@pytest_asyncio.fixture
async def client(test_db):
    """Create test client with test database."""
    # Override the database
    mongodb.client = test_db.client
    original_db_name = settings.MONGODB_DATABASE
    settings.MONGODB_DATABASE = f"{original_db_name}_test"
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    
    # Restore original settings
    settings.MONGODB_DATABASE = original_db_name


@pytest.fixture
def test_user_data():
    """Test user data."""
    return {
        "email": "test@example.com",
        "password": "testpassword123",
        "name": "Test User",
    }


@pytest_asyncio.fixture
async def auth_headers(client, test_user_data):
    """Get authentication headers for test user."""
    # Register user
    response = await client.post("/api/v1/auth/register", json=test_user_data)
    assert response.status_code == 201
    
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
```

### File: `services/config-service/tests/test_auth.py`

```python
"""Tests for authentication endpoints."""

import pytest


@pytest.mark.asyncio
async def test_register_success(client, test_user_data):
    """Test successful user registration."""
    response = await client.post("/api/v1/auth/register", json=test_user_data)
    
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_register_duplicate_email(client, test_user_data):
    """Test registration with duplicate email."""
    # First registration
    await client.post("/api/v1/auth/register", json=test_user_data)
    
    # Second registration with same email
    response = await client.post("/api/v1/auth/register", json=test_user_data)
    
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_login_success(client, test_user_data):
    """Test successful login."""
    # Register first
    await client.post("/api/v1/auth/register", json=test_user_data)
    
    # Login
    login_data = {
        "email": test_user_data["email"],
        "password": test_user_data["password"],
    }
    response = await client.post("/api/v1/auth/login", json=login_data)
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data


@pytest.mark.asyncio
async def test_login_invalid_password(client, test_user_data):
    """Test login with invalid password."""
    # Register first
    await client.post("/api/v1/auth/register", json=test_user_data)
    
    # Login with wrong password
    login_data = {
        "email": test_user_data["email"],
        "password": "wrongpassword",
    }
    response = await client.post("/api/v1/auth/login", json=login_data)
    
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token(client, test_user_data):
    """Test token refresh."""
    # Register and get tokens
    response = await client.post("/api/v1/auth/register", json=test_user_data)
    refresh_token = response.json()["refresh_token"]
    
    # Refresh
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
```

### File: `services/config-service/tests/test_configs.py`

```python
"""Tests for configuration endpoints."""

import pytest

from rag_config_common.models.enums import (
    DataSourceType,
    LLMProvider,
    EmbeddingProvider,
    RetrievalMethod,
    AgentTemplate,
)


@pytest.fixture
def sample_config():
    """Sample configuration data."""
    return {
        "name": "Test Config",
        "description": "A test configuration",
        "data_source": {
            "type": DataSourceType.LOCAL.value,
            "base_path": "/data/test",
            "folders": [],
            "has_multimodal": False,
        },
        "models": {
            "llm": {
                "provider": LLMProvider.OPENAI.value,
                "model_name": "gpt-4",
                "temperature": 0.7,
                "max_tokens": 2048,
                "is_multimodal": False,
            },
            "embedding": {
                "provider": EmbeddingProvider.OPENAI.value,
                "model_name": "text-embedding-3-small",
                "dimensions": 1536,
            },
            "document_processing": {
                "use_docling": False,
                "use_vision_llm": False,
                "ocr_enabled": True,
            },
        },
        "retrieval": {
            "method": RetrievalMethod.NAIVE.value,
            "vector": {
                "enabled": True,
                "top_k": 5,
                "score_threshold": 0.7,
            },
            "keyword": {"enabled": False},
            "graph": {"enabled": False},
        },
        "agent": {
            "template": AgentTemplate.NAIVE_RAG.value,
            "max_iterations": 5,
            "enable_judge": False,
        },
        "prompts": {
            "system_prompt": "You are a helpful assistant.",
            "rag_prompt_template": "Context: {context}\n\nQuestion: {query}\n\nAnswer:",
        },
    }


@pytest.mark.asyncio
async def test_create_config(client, auth_headers, sample_config):
    """Test creating a configuration."""
    response = await client.post(
        "/api/v1/configs/",
        json=sample_config,
        headers=auth_headers,
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == sample_config["name"]
    assert "id" in data


@pytest.mark.asyncio
async def test_list_configs(client, auth_headers, sample_config):
    """Test listing configurations."""
    # Create a config first
    await client.post("/api/v1/configs/", json=sample_config, headers=auth_headers)
    
    # List configs
    response = await client.get("/api/v1/configs/", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1


@pytest.mark.asyncio
async def test_get_config(client, auth_headers, sample_config):
    """Test getting a specific configuration."""
    # Create config
    create_response = await client.post(
        "/api/v1/configs/",
        json=sample_config,
        headers=auth_headers,
    )
    config_id = create_response.json()["id"]
    
    # Get config
    response = await client.get(f"/api/v1/configs/{config_id}", headers=auth_headers)
    
    assert response.status_code == 200
    assert response.json()["id"] == config_id


@pytest.mark.asyncio
async def test_update_config(client, auth_headers, sample_config):
    """Test updating a configuration."""
    # Create config
    create_response = await client.post(
        "/api/v1/configs/",
        json=sample_config,
        headers=auth_headers,
    )
    config_id = create_response.json()["id"]
    
    # Update config
    update_data = {"name": "Updated Config Name"}
    response = await client.put(
        f"/api/v1/configs/{config_id}",
        json=update_data,
        headers=auth_headers,
    )
    
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Config Name"


@pytest.mark.asyncio
async def test_delete_config(client, auth_headers, sample_config):
    """Test deleting a configuration."""
    # Create config
    create_response = await client.post(
        "/api/v1/configs/",
        json=sample_config,
        headers=auth_headers,
    )
    config_id = create_response.json()["id"]
    
    # Delete config
    response = await client.delete(f"/api/v1/configs/{config_id}", headers=auth_headers)
    
    assert response.status_code == 200
    
    # Verify deleted
    get_response = await client.get(f"/api/v1/configs/{config_id}", headers=auth_headers)
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_unauthorized_access(client, sample_config):
    """Test that endpoints require authentication."""
    response = await client.get("/api/v1/configs/")
    assert response.status_code == 401
```

---

## Verification Checklist

After completing all tasks, verify:

- [ ] `cd services/config-service && pip install -r requirements.txt` succeeds
- [ ] `pip install -e ../../shared/python` succeeds
- [ ] `uvicorn app.main:app --reload --port 8001` starts without errors
- [ ] Health check works: `curl http://localhost:8001/health`
- [ ] API docs accessible: `http://localhost:8001/docs`
- [ ] Register user works
- [ ] Login works
- [ ] Token refresh works
- [ ] Create config works (with auth)
- [ ] List configs works
- [ ] Update config works
- [ ] Delete config works
- [ ] Folder scan works
- [ ] YAML export works
- [ ] YAML import works
- [ ] `pytest tests/ -v` passes all tests

---

## Running the Service

```bash
# From services/config-service directory

# Install dependencies
pip install -r requirements.txt
pip install -e ../../shared/python

# Run development server
uvicorn app.main:app --reload --port 8001

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=app --cov-report=html
```

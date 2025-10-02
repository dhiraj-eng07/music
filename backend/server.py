from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
import uuid
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import JWTError, jwt
import hashlib
import base64
from bson import ObjectId
import uvicorn
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Security setup
SECRET_KEY = "serenity_music_app_secret_key_2025"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

security = HTTPBearer()

# Create the main app without a prefix
app = FastAPI(title="Serenity Music Streaming API")
uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Utility functions
def verify_password(plain_password, hashed_password):
    # Simple hash comparison for development
    password_hash = hashlib.sha256(plain_password.encode()).hexdigest()
    return password_hash == hashed_password

def get_password_hash(password):
    # Simple SHA256 hash for development
    return hashlib.sha256(password.encode()).hexdigest()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = await db.users.find_one({"email": username})
    if user is None:
        raise credentials_exception
    return user

# Models
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(BaseModel):
    id: str
    name: str
    email: str
    created_at: datetime

class Token(BaseModel):
    access_token: str
    token_type: str
    user: User

class Song(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    artist: str
    duration: int  # in seconds
    file_data: str  # base64 encoded audio data
    cover_art: Optional[str] = None  # base64 encoded image
    genre: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    uploaded_by: str  # user id

class Playlist(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: Optional[str] = None
    songs: List[str] = []  # list of song IDs
    cover_art: Optional[str] = None
    created_by: str  # user id
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_public: bool = True

class PlaylistCreate(BaseModel):
    title: str
    description: Optional[str] = None
    cover_art: Optional[str] = None
    is_public: bool = True

class SongCreate(BaseModel):
    title: str
    artist: str
    duration: int
    file_data: str
    cover_art: Optional[str] = None
    genre: Optional[str] = None

# Sample data initialization
async def initialize_sample_data():
    """Initialize sample playlists and songs for demo"""
    # Check if sample data already exists
    existing_playlists = await db.playlists.find({"created_by": "system"}).to_list(1)
    if existing_playlists:
        return
    
    # Sample album covers (base64 will be added from the image URLs)
    album_covers = [
        "https://images.unsplash.com/photo-1644855640845-ab57a047320e?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDk1Nzd8MHwxfHNlYXJjaHwxfHxtdXNpYyUyMGFsYnVtJTIwY292ZXJ8ZW58MHx8fHwxNzU5Mzg5OTEyfDA&ixlib=rb-4.1.0&q=85",
        "https://images.unsplash.com/photo-1496208612508-eb52fba7d94e?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2NzV8MHwxfHNlYXJjaHwxfHxlbGVjdHJvbmljJTIwZGFuY2UlMjBtdXNpY3xlbnwwfHx8fDE3NTkzODk5MTd8MA&ixlib=rb-4.1.0&q=85",
        "https://images.unsplash.com/photo-1609316116970-dbfd288439d3?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2NzV8MHwxfHNlYXJjaHwyfHxlbGVjdHJvbmljJTIwZGFuY2UlMjBtdXNpY3xlbnwwfHx8fDE3NTkzODk5MTd8MA&ixlib=rb-4.1.0&q=85",
        "https://images.unsplash.com/photo-1629923759854-156b88c433aa?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDk1Nzd8MHwxfHNlYXJjaHwyfHxtdXNpYyUyMGFsYnVtJTIwY292ZXJ8ZW58MHx8fHwxNzU5Mzg5OTEyfDA&ixlib=rb-4.1.0&q=85"
    ]
    
    # Create sample playlists
    sample_playlists = [
        {
            "id": str(uuid.uuid4()),
            "title": "Dance",
            "description": "High-energy dance tracks to get you moving",
            "songs": [],
            "cover_art": album_covers[0],
            "created_by": "system",
            "created_at": datetime.utcnow(),
            "is_public": True
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Mood",
            "description": "Chill vibes for relaxing moments",
            "songs": [],
            "cover_art": album_covers[1],
            "created_by": "system",
            "created_at": datetime.utcnow(),
            "is_public": True
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Party",
            "description": "Party anthems and crowd favorites",
            "songs": [],
            "cover_art": album_covers[2],
            "created_by": "system",
            "created_at": datetime.utcnow(),
            "is_public": True
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Chill",
            "description": "Laid-back tracks for peaceful moments",
            "songs": [],
            "cover_art": album_covers[3],
            "created_by": "system",
            "created_at": datetime.utcnow(),
            "is_public": True
        }
    ]
    
    # Insert sample playlists
    await db.playlists.insert_many(sample_playlists)

# Authentication routes
@api_router.post("/auth/register", response_model=Token)
async def register(user: UserCreate):
    # Check if user exists
    existing_user = await db.users.find_one({"email": user.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Hash password
    hashed_password = get_password_hash(user.password)
    
    # Create user
    user_data = {
        "id": str(uuid.uuid4()),
        "name": user.name,
        "email": user.email,
        "password": hashed_password,
        "created_at": datetime.utcnow()
    }
    
    await db.users.insert_one(user_data)
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    user_response = User(
        id=user_data["id"],
        name=user_data["name"],
        email=user_data["email"],
        created_at=user_data["created_at"]
    )
    
    return Token(access_token=access_token, token_type="bearer", user=user_response)

@api_router.post("/auth/login", response_model=Token)
async def login(user: UserLogin):
    # Find user
    db_user = await db.users.find_one({"email": user.email})
    if not db_user or not verify_password(user.password, db_user["password"]):
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    user_response = User(
        id=db_user["id"],
        name=db_user["name"],
        email=db_user["email"],
        created_at=db_user["created_at"]
    )
    
    return Token(access_token=access_token, token_type="bearer", user=user_response)

# Music routes
@api_router.get("/playlists", response_model=List[Playlist])
async def get_playlists(current_user: dict = Depends(get_current_user)):
    playlists = await db.playlists.find({"$or": [{"is_public": True}, {"created_by": current_user["id"]}]}).to_list(100)
    return [Playlist(**playlist) for playlist in playlists]

@api_router.post("/playlists", response_model=Playlist)
async def create_playlist(playlist: PlaylistCreate, current_user: dict = Depends(get_current_user)):
    playlist_data = playlist.dict()
    playlist_data["id"] = str(uuid.uuid4())
    playlist_data["created_by"] = current_user["id"]
    playlist_data["created_at"] = datetime.utcnow()
    playlist_data["songs"] = []
    
    await db.playlists.insert_one(playlist_data)
    return Playlist(**playlist_data)

@api_router.get("/playlists/{playlist_id}/songs", response_model=List[Song])
async def get_playlist_songs(playlist_id: str, current_user: dict = Depends(get_current_user)):
    playlist = await db.playlists.find_one({"id": playlist_id})
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    
    if not playlist["is_public"] and playlist["created_by"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    songs = await db.songs.find({"id": {"$in": playlist["songs"]}}).to_list(100)
    return [Song(**song) for song in songs]

@api_router.post("/songs", response_model=Song)
async def upload_song(song: SongCreate, current_user: dict = Depends(get_current_user)):
    song_data = song.dict()
    song_data["id"] = str(uuid.uuid4())
    song_data["uploaded_by"] = current_user["id"]
    song_data["created_at"] = datetime.utcnow()
    
    await db.songs.insert_one(song_data)
    return Song(**song_data)

@api_router.get("/songs", response_model=List[Song])
async def get_songs(current_user: dict = Depends(get_current_user)):
    songs = await db.songs.find().to_list(100)
    return [Song(**song) for song in songs]

@api_router.post("/playlists/{playlist_id}/songs/{song_id}")
async def add_song_to_playlist(playlist_id: str, song_id: str, current_user: dict = Depends(get_current_user)):
    playlist = await db.playlists.find_one({"id": playlist_id})
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    
    if playlist["created_by"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    song = await db.songs.find_one({"id": song_id})
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    
    if song_id not in playlist["songs"]:
        await db.playlists.update_one(
            {"id": playlist_id},
            {"$push": {"songs": song_id}}
        )
    
    return {"message": "Song added to playlist"}

@api_router.delete("/playlists/{playlist_id}/songs/{song_id}")
async def remove_song_from_playlist(playlist_id: str, song_id: str, current_user: dict = Depends(get_current_user)):
    playlist = await db.playlists.find_one({"id": playlist_id})
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    
    if playlist["created_by"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    await db.playlists.update_one(
        {"id": playlist_id},
        {"$pull": {"songs": song_id}}
    )
    
    return {"message": "Song removed from playlist"}

# Search routes
@api_router.get("/search")
async def search(q: str, current_user: dict = Depends(get_current_user)):
    # Search songs
    songs = await db.songs.find({
        "$or": [
            {"title": {"$regex": q, "$options": "i"}},
            {"artist": {"$regex": q, "$options": "i"}},
            {"genre": {"$regex": q, "$options": "i"}}
        ]
    }).to_list(50)
    
    # Search playlists
    playlists = await db.playlists.find({
        "$and": [
            {"$or": [{"is_public": True}, {"created_by": current_user["id"]}]},
            {"$or": [
                {"title": {"$regex": q, "$options": "i"}},
                {"description": {"$regex": q, "$options": "i"}}
            ]}
        ]
    }).to_list(20)
    
    return {
        "songs": [Song(**song) for song in songs],
        "playlists": [Playlist(**playlist) for playlist in playlists]
    }

# User preferences
@api_router.get("/user/profile")
async def get_user_profile(current_user: dict = Depends(get_current_user)):
    return User(
        id=current_user["id"],
        name=current_user["name"],
        email=current_user["email"],
        created_at=current_user["created_at"]
    )

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup_event():
    await initialize_sample_data()
    logger.info("Sample data initialized")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

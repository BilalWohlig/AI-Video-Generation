import os
from pathlib import Path
from dotenv import load_dotenv
from dataclasses import dataclass
from typing import Dict, Any

# Load environment variables
load_dotenv()

@dataclass
class APIConfig:
    groq_api_key: str
    elevenlabs_api_key: str
    openai_api_key: str
    fal_key: str
    creatomate_api_key: str
    beatoven_api_key: str
    
@dataclass
class StorageConfig:
    gcp_project: str
    gcp_bucket: str
    gcp_credentials: str

@dataclass
class VideoConfig:
    resolution: str = "1920x1080"
    fps: int = 30
    max_duration: int = 600  # 10 minutes max
    quality: str = "high"

@dataclass
class Settings:
    api: APIConfig
    storage: StorageConfig
    video: VideoConfig
    debug: bool = False
    max_retries: int = 3
    temp_dir: Path = Path("temp")
    output_dir: Path = Path("output")

def load_settings() -> Settings:
    """Load configuration from environment variables"""
    
    api_config = APIConfig(
        groq_api_key=os.getenv("GROQ_API_KEY", ""),
        elevenlabs_api_key=os.getenv("ELEVENLABS_API_KEY", ""),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        fal_key=os.getenv("FAL_KEY", ""),
        creatomate_api_key=os.getenv("CREATOMATE_API_KEY", ""),
        beatoven_api_key=os.getenv("BEATOVEN_API_KEY", "")
    )
    
    storage_config = StorageConfig(
        gcp_project=os.getenv("GOOGLE_CLOUD_PROJECT", ""),
        gcp_bucket=os.getenv("GOOGLE_CLOUD_BUCKET", ""),
        gcp_credentials=os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
    )
    
    video_config = VideoConfig(
        resolution=os.getenv("DEFAULT_VIDEO_RESOLUTION", "1920x1080"),
        fps=int(os.getenv("DEFAULT_VIDEO_FPS", "30"))
    )
    
    return Settings(
        api=api_config,
        storage=storage_config,
        video=video_config,
        debug=os.getenv("DEBUG", "False").lower() == "true",
        max_retries=int(os.getenv("MAX_RETRIES", "3"))
    )
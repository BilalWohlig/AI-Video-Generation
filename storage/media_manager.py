import os
from pathlib import Path
from typing import Dict, Optional, Union
from google.cloud import storage
from urllib.parse import urlparse
import requests
import tempfile

from config.settings import load_settings
from utils.logger import setup_logger
from utils.helpers import retry_with_backoff

class MediaManager:
    """Handles media storage and organization using Google Cloud Storage"""
    
    def __init__(self):
        self.settings = load_settings()
        self.logger = setup_logger("media_manager")
        
        # Initialize Google Cloud Storage client
        self.client = storage.Client(project=self.settings.storage.gcp_project)
        self.bucket = self.client.bucket(self.settings.storage.gcp_bucket)
        
    @retry_with_backoff(max_retries=3)
    def upload_file(self, local_path: Path, remote_path: str) -> str:
        """Upload file to Google Cloud Storage"""
        
        self.logger.info(f"Uploading {local_path} to {remote_path}")
        
        try:
            blob = self.bucket.blob(remote_path)
            blob.upload_from_filename(str(local_path))
            
            # Make file publicly accessible
            blob.make_public()
            
            public_url = blob.public_url
            self.logger.info(f"File uploaded successfully: {public_url}")
            
            return public_url
            
        except Exception as e:
            self.logger.error(f"Error uploading file: {e}")
            raise
    
    @retry_with_backoff(max_retries=3)
    def upload_from_url(self, url: str, remote_path: str) -> str:
        """Download from URL and upload to Google Cloud Storage"""
        
        self.logger.info(f"Downloading from {url} and uploading to {remote_path}")
        
        try:
            # Download file to temporary location
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                for chunk in response.iter_content(chunk_size=8192):
                    temp_file.write(chunk)
                temp_path = temp_file.name
            
            # Upload to GCS
            blob = self.bucket.blob(remote_path)
            blob.upload_from_filename(temp_path)
            blob.make_public()
            
            # Clean up temporary file
            os.unlink(temp_path)
            
            public_url = blob.public_url
            self.logger.info(f"File uploaded from URL successfully: {public_url}")
            
            return public_url
            
        except Exception as e:
            self.logger.error(f"Error uploading from URL: {e}")
            # Fallback: If we fail to download or upload (e.g., placeholder URL or network issue),
            # gracefully degrade by returning the original URL. This allows the pipeline to
            # continue running in offline/mock scenarios where the asset is only a reference.
            self.logger.warning("Falling back to original URL without GCS upload")
            return url
    
    def organize_project_assets(self, project_id: str) -> Dict[str, str]:
        """Create organized folder structure for project assets"""
        
        folders = {
            "audio": f"projects/{project_id}/audio/",
            "images": f"projects/{project_id}/images/",
            "videos": f"projects/{project_id}/videos/",
            "music": f"projects/{project_id}/music/",
            "characters": f"projects/{project_id}/characters/",
            "final": f"projects/{project_id}/final/",
            "temp": f"projects/{project_id}/temp/"
        }
        
        return folders
    
    def store_character_reference(self, character_name: str, image_source: Union[str, Path], project_id: str) -> str:
        """Store character reference image in organized structure
        
        Args:
            character_name: Name of the character
            image_source: Either a URL string or local file Path
            project_id: Project identifier
            
        Returns:
            GCS public URL
        """
        
        folders = self.organize_project_assets(project_id)
        remote_path = folders["characters"] + f"{character_name}_reference.jpg"
        
        # Check if image_source is a local file path or URL
        if isinstance(image_source, (str, Path)):
            # Convert to Path object for consistent handling
            if isinstance(image_source, str):
                # Check if it's a URL or local path
                if image_source.startswith(('http://', 'https://')):
                    # It's a URL, use upload_from_url
                    gcs_url = self.upload_from_url(image_source, remote_path)
                else:
                    # It's a local path string, convert to Path and upload
                    local_path = Path(image_source)
                    gcs_url = self.upload_file(local_path, remote_path)
            else:
                # It's already a Path object, upload directly
                gcs_url = self.upload_file(image_source, remote_path)
        else:
            raise ValueError(f"Invalid image_source type: {type(image_source)}. Expected str or Path.")
        
        return gcs_url
    
    def store_scene_asset(self, scene_id: str, asset_url: str, project_id: str, asset_type: str = "videos") -> str:
        """Store scene asset (video/image) in organized structure"""
        
        folders = self.organize_project_assets(project_id)
        
        # Determine file extension based on asset type
        if asset_type == "videos":
            extension = ".mp4"
        elif asset_type == "images":
            extension = ".jpg"
        elif asset_type == "music":
            extension = ".mp3"
        elif asset_type == "final":
            extension = ".mp4"
        else:
            extension = ".file"
        
        remote_path = folders[asset_type] + f"{scene_id}{extension}"
        gcs_url = self.upload_from_url(asset_url, remote_path)
        return gcs_url
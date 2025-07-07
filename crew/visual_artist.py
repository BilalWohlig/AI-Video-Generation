import fal_client
import os
from typing import Dict, Optional, List
from pathlib import Path

from config.settings import load_settings
from utils.logger import setup_logger
from utils.helpers import retry_with_backoff, create_character_reference_prompt
from director.production_plan import Character

class VisualArtist:
    """Handles video generation using Veo 3 with character consistency"""
    
    def __init__(self):
        self.settings = load_settings()
        self.logger = setup_logger("visual_artist")
        os.environ["FAL_KEY"] = self.settings.api.fal_key
        
    @retry_with_backoff(max_retries=3)
    def generate_broll_video(self, scene_description: str, duration: float, mood: str = "neutral") -> str:
        """Generate B-roll video using Veo 3"""
        
        self.logger.info(f"Generating B-roll video: {scene_description[:50]}... (duration: {duration}s)")
        
        # Enhanced prompt for Veo 3
        enhanced_prompt = f"""
        {scene_description}
        
        Cinematic quality, professional video production.
        Mood: {mood}
        Duration: {duration} seconds
        
        Camera movement: Smooth, professional cinematography
        Lighting: Professional, cinematic lighting
        Quality: High definition, sharp focus
        Style: Documentary/cinematic style
        """
        
        try:
            handler = fal_client.submit(
                "fal-ai/google-veo/v3",  # Using Veo 3
                arguments={
                    "prompt": enhanced_prompt,
                    "duration": min(duration, 10.0),  # Veo 3 max duration
                    "aspect_ratio": "16:9",
                    "resolution": "720p",
                    "quality": "high",
                    "camera_motion": "smooth",
                    "style": "cinematic"
                }
            )
            
            result = handler.get()
            video_url = result["video"]["url"]
            
            self.logger.info(f"B-roll video generated: {video_url}")
            return video_url
            
        except Exception as e:
            self.logger.error(f"Error generating B-roll video: {e}")
            raise
    
    @retry_with_backoff(max_retries=3)
    def generate_character_video_with_references(self, characters: List[Character], scene_description: str, duration: float) -> str:
        """Generate video scene with characters using their reference images"""
        
        char_names = [c.name for c in characters]
        self.logger.info(f"Generating character video with: {char_names}")
        
        # Create enhanced prompt with character references
        character_refs = []
        for i, character in enumerate(characters, 1):
            character_refs.append({
                "name": character.name,
                "description": character.description,
                "image_number": i
            })
        
        # Build prompt with character references
        char_ref_text = []
        for ref in character_refs:
            char_ref_text.append(f"{ref['name']} (image {ref['image_number']})")
        
        enhanced_prompt = f"""
        Create a cinematic video scene featuring: {', '.join(char_ref_text)}
        
        Scene: {scene_description}
        
        Character consistency requirements:
        """
        
        for ref in character_refs:
            enhanced_prompt += f"""
        - {ref['name']} must match their reference image exactly: {ref['description']}
        """
        
        enhanced_prompt += f"""
        
        Professional cinematography requirements:
        - Duration: {duration} seconds
        - Smooth camera movement
        - Professional lighting
        - High quality video production
        - Characters clearly visible and recognizable
        - Cinematic style and composition
        """
        
        try:
            # Prepare reference images for the API call
            reference_images = []
            for character in characters:
                if character.gcs_image_url:
                    reference_images.append(character.gcs_image_url)
            
            handler = fal_client.submit(
                "fal-ai/google-veo/v3",
                arguments={
                    "prompt": enhanced_prompt,
                    "duration": min(duration, 10.0),
                    "aspect_ratio": "16:9",
                    "resolution": "720p",
                    "quality": "high",
                    "style": "cinematic",
                    "reference_images": reference_images[:3]  # Veo 3 supports up to 3 reference images
                }
            )
            
            result = handler.get()
            video_url = result["video"]["url"]
            
            self.logger.info(f"Character video scene generated: {video_url}")
            return video_url
            
        except Exception as e:
            self.logger.error(f"Error generating character video scene: {e}")
            raise
    
    @retry_with_backoff(max_retries=3)
    def generate_talking_avatar(self, character: Character, audio_path: Path, duration: float) -> str:
        """Generate talking avatar using character image and audio"""
        
        self.logger.info(f"Generating talking avatar for {character.name} (duration: {duration}s)")
        
        try:
            # Upload audio file for avatar generation
            with open(audio_path, 'rb') as audio_file:
                handler = fal_client.submit(
                    "fal-ai/hunyuan-avatar",
                    arguments={
                        "image_url": character.gcs_image_url,
                        "audio_file": audio_file,
                        "quality": "high",
                        "resolution": "720p",
                        "aspect_ratio": "16:9"
                    }
                )
            
            result = handler.get()
            video_url = result["video"]["url"]
            
            self.logger.info(f"Talking avatar generated: {video_url}")
            return video_url
            
        except Exception as e:
            self.logger.error(f"Error generating talking avatar: {e}")
            raise
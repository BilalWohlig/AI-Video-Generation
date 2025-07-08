import fal_client
import os
from typing import Dict, Optional, List
from pathlib import Path

from config.settings import load_settings
from utils.logger import setup_logger
from utils.helpers import retry_with_backoff, create_character_reference_prompt
from director.production_plan import Character
from crew.character_designer import CharacterDesigner

class VisualArtist:
    """Handles video generation using scene images converted to video"""
    
    def __init__(self):
        self.settings = load_settings()
        self.logger = setup_logger("visual_artist")
        os.environ["FAL_KEY"] = self.settings.api.fal_key
        self.character_designer = CharacterDesigner()
        
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
                "fal-ai/veo3",  # Correct Veo 3 endpoint
                arguments={
                    "prompt": enhanced_prompt,
                    "duration": "8s",  # Veo 3 max duration
                    "aspect_ratio": "16:9",
                    # "resolution": "720p",
                    # "quality": "high",
                    "generate_audio": False  # Disable audio to save costs
                }
            )
            
            result = handler.get()
            
            # Handle different possible response structures
            if "video" in result and "url" in result["video"]:
                video_url = result["video"]["url"]
            elif "url" in result:
                video_url = result["url"]
            else:
                self.logger.error(f"Unexpected response structure: {result}")
                raise Exception(f"Could not find video URL in response: {result}")
            
            self.logger.info(f"B-roll video generated: {video_url}")
            return video_url
            
        except Exception as e:
            self.logger.error(f"Error generating B-roll video: {e}")
            raise
    
    @retry_with_backoff(max_retries=3)
    def generate_character_video_with_references(self, characters: List[Character], scene_description: str, duration: float) -> str:
        """Generate video by first creating scene image, then converting to video"""
        
        char_names = [c.name for c in characters]
        self.logger.info(f"Generating character video with: {char_names}")
        
        try:
            # Step 1: Generate scene image with characters using DALL-E 3
            self.logger.info("Step 1: Generating scene image with characters...")
            scene_image_path = self.character_designer.generate_character_scene_image(
                characters, 
                scene_description
            )
            
            # Step 2: Convert scene image to video using image-to-video model
            self.logger.info("Step 2: Converting scene image to video...")
            video_url = self._convert_image_to_video(scene_image_path, scene_description, duration)
            
            self.logger.info(f"Character video scene generated: {video_url}")
            return video_url
            
        except Exception as e:
            self.logger.error(f"Error generating character video scene: {e}")
            raise
    
    @retry_with_backoff(max_retries=3)
    def _convert_image_to_video(self, image_path: Path, scene_description: str, duration: float) -> str:
        """Convert static image to video using image-to-video model"""
        
        self.logger.info(f"Converting image to video: {image_path}")
        
        # Enhanced prompt for motion
        motion_prompt = f"""
        {scene_description}
        
        Professional cinematic movement:
        - Subtle, natural camera movements
        - Smooth transitions and motion
        - Professional cinematography
        - High quality video production
        """
        
        try:
            # Encode the image file as a data URL
            self.logger.info("Encoding image file...")
            image_data_url = fal_client.encode_file(str(image_path))
            
            # First preference: Kling 2.1 Standard
            self.logger.info("Using Kling 2.1 Standard Image-to-Video...")
            handler = fal_client.submit(
                "fal-ai/kling-video/v2.1/standard/image-to-video",
                arguments={
                    "image_url": image_data_url,
                    "prompt": motion_prompt,
                    "duration": "5",  # Kling supports up to 10s
                    # "aspect_ratio": "16:9",
                    "cfg_scale": 0.5,  # Classifier Free Guidance scale
                    # "seed": 42
                }
            )
            
            result = handler.get()
            
            # Handle different possible response structures
            if "video" in result and "url" in result["video"]:
                video_url = result["video"]["url"]
            elif "url" in result:
                video_url = result["url"]
            else:
                self.logger.error(f"Unexpected response structure: {result}")
                raise Exception(f"Could not find video URL in response: {result}")
            
            self.logger.info(f"Image converted to video with Kling 2.1: {video_url}")
            return video_url
            
        except Exception as e:
            self.logger.error(f"Error converting image to video with Kling 2.1: {e}")
            # Fallback to Veo 2 Image-to-Video
            try:
                self.logger.info("Trying fallback: Veo 2 Image-to-Video...")
                return self._convert_with_veo2(image_data_url, motion_prompt, duration)
            except Exception as e2:
                self.logger.error(f"Error with Veo 2 fallback: {e2}")
                # Final fallback: Stable Video Diffusion
                try:
                    self.logger.info("Trying final fallback: Stable Video Diffusion...")
                    return self._convert_with_stable_video(image_path, motion_prompt, duration)
                except Exception as e3:
                    self.logger.error(f"Error with Stable Video fallback: {e3}")
                    # Ultimate fallback: Generate text-to-video with scene description
                    return self._fallback_text_to_video(scene_description, duration)
    
    @retry_with_backoff(max_retries=2)
    def _convert_with_veo2(self, image_data_url: str, motion_prompt: str, duration: float) -> str:
        """Fallback: Convert using Veo 2 Image-to-Video"""
        
        try:
            handler = fal_client.submit(
                "fal-ai/veo-2-image-to-video",
                arguments={
                    "image_url": image_data_url,
                    "prompt": motion_prompt,
                    "duration": min(duration, 8.0),
                    "aspect_ratio": "16:9",
                    "quality": "standard"
                }
            )
            
            result = handler.get()
            
            if "video" in result and "url" in result["video"]:
                return result["video"]["url"]
            elif "url" in result:
                return result["url"]
            else:
                raise Exception(f"Could not find video URL in Veo 2 response: {result}")
                
        except Exception as e:
            self.logger.error(f"Veo 2 conversion failed: {e}")
            raise

    @retry_with_backoff(max_retries=2)
    def _convert_with_stable_video(self, image_path: Path, motion_prompt: str, duration: float) -> str:
        """Fallback: Convert using Stable Video Diffusion"""
        
        try:
            # Encode the image file as a data URL
            image_data_url = fal_client.encode_file(str(image_path))
            
            handler = fal_client.submit(
                "fal-ai/stable-video",  # Stable Video Diffusion
                arguments={
                    "image_url": image_data_url,
                    "motion_bucket_id": 127,  # Controls motion amount
                    "cond_aug": 0.02,  # Conditioning augmentation
                    "seed": 42,
                    "fps": 6,
                    "num_frames": min(int(duration * 6), 25)  # Max 25 frames for SVD
                }
            )
            
            result = handler.get()
            
            if "video" in result and "url" in result["video"]:
                return result["video"]["url"]
            elif "url" in result:
                return result["url"]
            else:
                raise Exception(f"Could not find video URL in Stable Video response: {result}")
                
        except Exception as e:
            self.logger.error(f"Stable Video conversion failed: {e}")
            raise
    
    @retry_with_backoff(max_retries=2)
    def _fallback_text_to_video(self, scene_description: str, duration: float) -> str:
        """Final fallback: Generate video from text description only"""
        
        self.logger.info("Using final fallback: text-to-video generation")
        
        try:
            handler = fal_client.submit(
                "fal-ai/veo3",  # Veo 3 text-to-video as final fallback
                arguments={
                    "prompt": scene_description,
                    "duration": min(duration, 8.0),
                    "aspect_ratio": "16:9",
                    "resolution": "720p",
                    "audio": False
                }
            )
            
            result = handler.get()
            
            if "video" in result and "url" in result["video"]:
                return result["video"]["url"]
            elif "url" in result:
                return result["url"]
            else:
                raise Exception(f"Could not find video URL in Veo3 response: {result}")
                
        except Exception as e:
            self.logger.error(f"Final fallback failed: {e}")
            raise
    
    @retry_with_backoff(max_retries=3)
    def generate_talking_avatar(self, character: Character, audio_path: Path, duration: float) -> str:
        """Generate talking avatar using character image and audio"""
        
        self.logger.info(f"Generating talking avatar for {character.name} (duration: {duration}s)")
        
        try:
            # For talking avatars, use the character's image with subtle motion
            character_image_data_url = fal_client.encode_file(character.reference_image_url)
            
            # Enhanced prompt for talking motion
            talking_prompt = f"""
            Professional presenter speaking to camera:
            - Subtle facial movements and expressions
            - Natural head movements
            - Professional presentation style
            - Engaging eye contact with camera
            - Minimal but realistic motion
            """
            
            # Try Kling 2.1 Standard first for talking avatars too
            self.logger.info("Using Kling 2.1 Standard for talking avatar...")
            handler = fal_client.submit(
                "fal-ai/kling-video/v1/standard/image-to-video",
                arguments={
                    "image_url": character_image_data_url,
                    "prompt": talking_prompt,
                    "duration": min(duration, 10.0),
                    "aspect_ratio": "16:9",
                    "cfg_scale": 0.3,  # Lower CFG for more subtle motion
                    "seed": 42
                }
            )
            
            result = handler.get()
            
            # Handle different possible response structures  
            if "video" in result and "url" in result["video"]:
                video_url = result["video"]["url"]
            elif "url" in result:
                video_url = result["url"]
            else:
                self.logger.error(f"Unexpected response structure: {result}")
                raise Exception(f"Could not find video URL in response: {result}")
            
            self.logger.info(f"Talking avatar generated with Kling 2.1: {video_url}")
            return video_url
            
        except Exception as e:
            self.logger.error(f"Error generating talking avatar with Kling 2.1: {e}")
            # Fallback: Use Stable Video Diffusion with lower motion
            try:
                self.logger.info("Fallback: Using Stable Video Diffusion for talking avatar...")
                
                handler = fal_client.submit(
                    "fal-ai/stable-video",
                    arguments={
                        "image_url": character_image_data_url,
                        "motion_bucket_id": 40,  # Lower motion for subtle talking movement
                        "cond_aug": 0.02,
                        "seed": 42,
                        "fps": 6,
                        "num_frames": min(int(duration * 6), 25)
                    }
                )
                
                result = handler.get()
                
                if "video" in result and "url" in result["video"]:
                    return result["video"]["url"]
                elif "url" in result:
                    return result["url"]
                else:
                    raise Exception(f"Could not find video URL in Stable Video response: {result}")
                    
            except Exception as e2:
                self.logger.error(f"Error with Stable Video fallback: {e2}")
                # Final fallback: Generate basic character scene
                return self._convert_image_to_video(
                    Path(character.reference_image_url), 
                    f"Professional presenter speaking to camera", 
                    duration
                )
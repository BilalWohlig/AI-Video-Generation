import requests
import json
import time
from typing import Dict, List, Any
from pathlib import Path

from config.settings import load_settings
from utils.logger import setup_logger
from utils.helpers import retry_with_backoff
from director.production_plan import ProductionPlan

class VideoAssembler:
    """Handles final video assembly using Creatomate API"""
    
    def __init__(self):
        self.settings = load_settings()
        self.logger = setup_logger("video_assembler")
        self.api_key = self.settings.api.creatomate_api_key
        self.base_url = "https://api.creatomate.com/v1"
        
    @retry_with_backoff(max_retries=3)
    def assemble_final_video(self, production_plan: ProductionPlan, media_assets: Dict[str, Dict[str, str]]) -> str:
        """Assemble final video using all generated assets"""
        
        self.logger.info(f"Assembling final video for project: {production_plan.project_id}")
        
        # Create comprehensive edit decision list
        edl = self._create_comprehensive_edl(production_plan, media_assets)
        
        # Submit render job to Creatomate
        render_id = self._submit_render_job(edl)
        
        # Poll for completion
        final_video_url = self._wait_for_render_completion(render_id)
        
        self.logger.info(f"Final video assembled: {final_video_url}")
        return final_video_url
    
    def _create_comprehensive_edl(self, production_plan: ProductionPlan, media_assets: Dict[str, Dict[str, str]]) -> Dict[str, Any]:
        """Create comprehensive Edit Decision List for Creatomate"""
        
        # Base composition settings
        composition = {
            "width": 1920,
            "height": 1080,
            "duration": production_plan.total_duration,
            "frame_rate": self.settings.video.fps,
            "elements": []
        }
        
        # Add main voiceover track
        if "audio" in media_assets and "main_voiceover" in media_assets["audio"]:
            composition["elements"].append({
                "type": "audio",
                "source": media_assets["audio"]["main_voiceover"],
                "start_time": 0,
                "duration": production_plan.total_duration,
                "volume": 0.8
            })
        
        # Add background music
        if "music" in media_assets and "background" in media_assets["music"]:
            composition["elements"].append({
                "type": "audio",
                "source": media_assets["music"]["background"],
                "start_time": 0,
                "duration": production_plan.total_duration,
                "volume": 0.3,  # Lower volume for background
                "fade_in": 1.0,
                "fade_out": 2.0
            })
        
        # Add video scenes
        for scene in production_plan.scenes:
            if scene.id in media_assets.get("videos", {}):
                video_element = {
                    "type": "video",
                    "source": media_assets["videos"][scene.id],
                    "start_time": scene.start_time,
                    "duration": scene.end_time - scene.start_time,
                    "width": 1920,
                    "height": 1080,
                    "fit": "cover"
                }
                
                # Add transitions based on scene mood
                if hasattr(scene, 'mood'):
                    video_element.update(self._get_transition_for_mood(scene.mood))
                
                composition["elements"].append(video_element)
        
        # Add title overlay if specified
        if production_plan.title:
            composition["elements"].append({
                "type": "text",
                "text": production_plan.title,
                "start_time": 0,
                "duration": 3.0,
                "font_size": 48,
                "font_weight": "bold",
                "color": "#FFFFFF",
                "stroke_color": "#000000",
                "stroke_width": 2,
                "x": "50%",
                "y": "20%",
                "text_align": "center",
                "fade_in": 0.5,
                "fade_out": 0.5
            })
        
        return {"composition": composition}
    
    def _get_transition_for_mood(self, mood: str) -> Dict[str, Any]:
        """Get appropriate transition effects based on scene mood"""
        
        transition_map = {
            "energetic": {"fade_in": 0.2, "fade_out": 0.2},
            "dramatic": {"fade_in": 0.8, "fade_out": 0.8},
            "calm": {"fade_in": 1.0, "fade_out": 1.0},
            "mysterious": {"fade_in": 1.5, "fade_out": 1.5},
            "upbeat": {"fade_in": 0.1, "fade_out": 0.1}
        }
        
        return transition_map.get(mood, {"fade_in": 0.5, "fade_out": 0.5})
    
    @retry_with_backoff(max_retries=3)
    def _submit_render_job(self, edl: Dict[str, Any]) -> str:
        """Submit render job to Creatomate"""
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "composition": edl["composition"],
            "output_format": "mp4",
            "quality": "high",
            "frame_rate": self.settings.video.fps
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/renders",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            response.raise_for_status()
            render_data = response.json()
            
            return render_data["id"]
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error submitting render job: {e}")
            raise
    
    def _wait_for_render_completion(self, render_id: str, max_wait_time: int = 600) -> str:
        """Wait for render completion and return final video URL"""
        
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
        
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            try:
                response = requests.get(
                    f"{self.base_url}/renders/{render_id}",
                    headers=headers,
                    timeout=10
                )
                
                response.raise_for_status()
                render_status = response.json()
                
                status = render_status.get("status", "unknown")
                
                if status == "succeeded":
                    return render_status["url"]
                elif status == "failed":
                    error_msg = render_status.get("error", "Unknown error")
                    raise Exception(f"Render failed: {error_msg}")
                
                # Still processing, wait and retry
                self.logger.info(f"Render status: {status}, waiting...")
                time.sleep(10)
                
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Error checking render status: {e}")
                time.sleep(5)
        
        raise TimeoutError(f"Render did not complete within {max_wait_time} seconds")
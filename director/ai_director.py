import json
import uuid
from datetime import datetime
from typing import Dict, List, Any
from groq import Groq

from config.settings import load_settings
from utils.logger import setup_logger
from utils.helpers import retry_with_backoff
from director.production_plan import ProductionPlan, Theme, Character, Scene

class AIDirector:
    """The AI Director - orchestrates the entire video production pipeline"""
    
    def __init__(self):
        self.settings = load_settings()
        self.logger = setup_logger("ai_director")
        self.groq_client = Groq(api_key=self.settings.api.groq_api_key)
        print(self.groq_client)
        
    @retry_with_backoff(max_retries=3)
    def create_production_plan(self, user_brief: str) -> ProductionPlan:
        """Phase 1: Create comprehensive production plan from user brief"""
        
        self.logger.info("Creating production plan from user brief")
        
        system_prompt = """
        You are an AI Video Director creating professional video content. Analyze the user's brief and create a comprehensive production plan.

        Return a JSON object with this EXACT structure:
        {
          "title": "Video title",
          "theme": {
            "visual_style": "cinematic/documentary/corporate/artistic",
            "color_palette": ["#color1", "#color2", "#color3"],
            "mood": "energetic/calm/dramatic/educational",
            "lighting": "natural/dramatic/soft/bright",
            "art_style": "realistic/stylized/animated"
          },
          "script": "Full voiceover script with <break time='1.5s'/> SSML tags for natural pauses",
          "characters": [
            {
              "name": "character_name",
              "description": "detailed visual description for consistency (age, appearance, clothing, style)",
              "visual_style": "professional/casual/animated",
              "personality": "confident/friendly/authoritative"
            }
          ],
          "scenes": [
            {
              "id": "scene_1",
              "description": "detailed visual description of what happens in this scene",
              "script_segment": "part of script for this scene",
              "duration_estimate": 5.0,
              "visual_type": "character/broll/talking_avatar/static",
              "characters": ["character_name1", "character_name2"],
              "mood": "scene mood",
              "camera_angle": "close/medium/wide/overhead"
            }
          ]
        }

        Guidelines:
        - Use SSML <break time="1.5s"/> tags for natural pauses in script
        - Each scene should be 3-8 seconds for good pacing
        - Mix visual types for engagement
        - Ensure character descriptions are detailed for visual consistency
        - Script should be conversational and engaging
        - List all characters that appear in each scene in the "characters" array
        """
        
        try:
            response = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Create a video production plan for: {user_brief}"}
                ],
                temperature=0.7,
                max_tokens=4000
            )
            
            content = response.choices[0].message.content
            self.logger.debug(f"Groq response: {content}")

            if content.startswith("```json"):
                content = content[7:]  # Remove ```json
                if content.endswith("```"):
                    content = content[:-3] # Remove trailing ```
            
            # Parse JSON response
            plan_data = json.loads(content)
            
            # Create ProductionPlan object
            project_id = str(uuid.uuid4())
            
            production_plan = ProductionPlan(
                project_id=project_id,
                title=plan_data["title"],
                theme=Theme(**plan_data["theme"]),
                script=plan_data["script"],
                characters=[Character(**char) for char in plan_data["characters"]],
                scenes=[Scene(**scene) for scene in plan_data["scenes"]],
                created_at=datetime.now().isoformat()
            )
            
            self.logger.info(f"Created production plan with {len(production_plan.scenes)} scenes")
            return production_plan
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse Groq JSON response: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error creating production plan: {e}")
            raise
    
    @retry_with_backoff(max_retries=3)
    def refine_plan_with_audio_rhythm(self, production_plan: ProductionPlan, rhythm_map: Dict[str, Any]) -> ProductionPlan:
        """Phase 2: Refine plan based on actual audio rhythm analysis"""
        
        self.logger.info("Refining production plan with audio rhythm analysis")
        
        refinement_prompt = f"""
        You are refining a video production plan based on actual audio analysis. 
        
        Original Plan: {json.dumps(production_plan.to_dict(), indent=2)}
        
        Audio Rhythm Analysis: {json.dumps(rhythm_map, indent=2)}
        
        Update the scene timings to perfectly sync with the actual audio rhythm. 
        Adjust start_time, end_time, and duration for each scene based on:
        - Speech segments and natural breaks
        - Emphasis points for visual highlights
        - Overall tempo and rhythm
        
        Return the updated scenes array in JSON format:
        [
          {{
            "id": "scene_id",
            "start_time": float,
            "end_time": float,
            "duration": float,
            "description": "updated if needed",
            "script_segment": "same as before",
            "visual_type": "same as before",
            "characters": ["same as before"],
            "mood": "same as before",
            "camera_angle": "same as before"
          }}
        ]
        """
        
        try:
            response = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You are an expert video editor syncing visuals to audio rhythm."},
                    {"role": "user", "content": refinement_prompt}
                ],
                temperature=0.3,
                max_completion_tokens=3000
            )
            
            content = response.choices[0].message.content
            updated_scenes_data = json.loads(content)
            
            # Update scenes in production plan
            updated_scenes = []
            for scene_data in updated_scenes_data:
                scene = Scene(**scene_data)
                updated_scenes.append(scene)
            
            production_plan.scenes = updated_scenes
            production_plan.total_duration = rhythm_map.get("duration", 0.0)
            
            self.logger.info("Production plan refined with audio rhythm")
            return production_plan
            
        except Exception as e:
            self.logger.error(f"Error refining plan with audio rhythm: {e}")
            raise
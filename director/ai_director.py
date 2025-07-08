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
        
        # Extract only essential timing data to reduce token usage
        scenes_summary = []
        for scene in production_plan.scenes:
            scenes_summary.append({
                "id": scene.id,
                "duration_estimate": scene.duration_estimate,
                "description": scene.description[:100] + "..." if len(scene.description) > 100 else scene.description,
                "script_segment": scene.script_segment[:200] + "..." if len(scene.script_segment) > 200 else scene.script_segment,
                "visual_type": scene.visual_type,
                "characters": scene.characters,
                "mood": scene.mood,
                "camera_angle": scene.camera_angle
            })
        
        # Extract only key timing information from rhythm map
        rhythm_summary = {
            "duration": rhythm_map.get("duration", 0),
            "tempo": rhythm_map.get("tempo", 120),
            "natural_breaks": [
                {"start": br["start"], "end": br["end"], "duration": br["duration"], "type": br["type"]}
                for br in rhythm_map.get("natural_breaks", [])[:10]
            ],
            "emphasis_points": [
                {"timestamp": ep["timestamp"], "intensity": ep["intensity"]}
                for ep in rhythm_map.get("emphasis_points", [])[:10]
            ],
            "pacing_style": rhythm_map.get("pacing_recommendations", {}).get("pacing_style", "steady"),
            "avg_scene_duration": rhythm_map.get("pacing_recommendations", {}).get("avg_scene_duration", 5.0)
        }
        
        # Build prompt without f-strings to avoid format conflicts
        scenes_json = json.dumps(scenes_summary, indent=1)
        breaks_json = json.dumps(rhythm_summary['natural_breaks'][:5], indent=1)
        emphasis_json = json.dumps(rhythm_summary['emphasis_points'][:5], indent=1)
        
        duration_str = str(round(rhythm_summary['duration'], 1))
        tempo_str = str(round(rhythm_summary['tempo'], 1))
        avg_duration_str = str(rhythm_summary['avg_scene_duration'])
        
        refinement_prompt = """Refine video scene timings based on audio analysis.

Current Scenes (""" + str(len(scenes_summary)) + """ total):
""" + scenes_json + """

Audio Analysis:
- Total Duration: """ + duration_str + """s
- Tempo: """ + tempo_str + """ BPM
- Pacing Style: """ + rhythm_summary['pacing_style'] + """
- Recommended Scene Duration: """ + avg_duration_str + """s

Key Natural Breaks:
""" + breaks_json + """

Key Emphasis Points:
""" + emphasis_json + """

Update scene timings to sync with audio rhythm. Calculate start_time and end_time for each scene based on:
- Natural speech breaks for scene transitions
- Emphasis points for visual highlights
- Overall audio duration and pacing

Return updated scenes JSON array with timing info only:
[
  {
    "id": "scene_id",
    "start_time": 0.0,
    "end_time": 5.0,
    "duration": 5.0
  }
]

Only include id, start_time, end_time, and duration for each scene."""
        
        try:
            response = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You are an expert video editor syncing visuals to audio rhythm. Return only JSON with timing data."},
                    {"role": "user", "content": refinement_prompt}
                ],
                temperature=0.3,
                max_tokens=3000
            )
            
            content = response.choices[0].message.content
            
            # Clean response if it has code blocks
            if content.startswith("```json"):
                content = content[7:]
                if content.endswith("```"):
                    content = content[:-3]
            elif content.startswith("```"):
                content = content[3:]
                if content.endswith("```"):
                    content = content[:-3]
            
            updated_scenes_data = json.loads(content.strip())
            
            # Update scenes in production plan with new timing
            updated_scenes = []
            for i, scene_data in enumerate(updated_scenes_data):
                # Get original scene data
                original_scene = production_plan.scenes[i] if i < len(production_plan.scenes) else production_plan.scenes[0]
                
                # Create updated scene with new timing but original content
                scene = Scene(
                    id=scene_data.get("id", original_scene.id),
                    start_time=float(scene_data.get("start_time", 0)),
                    end_time=float(scene_data.get("end_time", 5)),
                    duration_estimate=float(scene_data.get("duration", scene_data.get("end_time", 5) - scene_data.get("start_time", 0))),
                    description=original_scene.description,
                    script_segment=original_scene.script_segment,
                    visual_type=original_scene.visual_type,
                    characters=original_scene.characters,
                    mood=original_scene.mood,
                    camera_angle=original_scene.camera_angle
                )
                updated_scenes.append(scene)
            
            production_plan.scenes = updated_scenes
            production_plan.total_duration = rhythm_map.get("duration", 0.0)
            
            self.logger.info("Production plan refined with audio rhythm")
            return production_plan
            
        except Exception as e:
            self.logger.error(f"Error refining plan with audio rhythm: {e}")
            raise
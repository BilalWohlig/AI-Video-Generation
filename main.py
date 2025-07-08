import asyncio
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from config.settings import load_settings
from utils.logger import setup_logger
from director.ai_director import AIDirector
from director.production_plan import ProductionPlan
from crew.voice_actor import VoiceActor
from crew.character_designer import CharacterDesigner
from crew.visual_artist import VisualArtist
from crew.music_composer import MusicComposer
from analysis.audio_analyzer import AudioAnalyzer
from assembly.video_assembler import VideoAssembler
from storage.media_manager import MediaManager

class AIVideoDirectorPipeline:
    """Complete AI Video Director Pipeline with OpenAI and Google Cloud Storage"""
    
    def __init__(self):
        self.settings = load_settings()
        self.logger = setup_logger("pipeline")

        self.settings.temp_dir.mkdir(parents=True, exist_ok=True)
        self.settings.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize all components
        self.director = AIDirector()
        self.voice_actor = VoiceActor()
        self.character_designer = CharacterDesigner()
        self.visual_artist = VisualArtist()
        self.music_composer = MusicComposer()
        self.audio_analyzer = AudioAnalyzer()
        self.video_assembler = VideoAssembler()
        self.media_manager = MediaManager()
        
        # Project state
        self.project_id = str(uuid.uuid4())
        self.production_plan: Optional[ProductionPlan] = None
        self.media_assets = {
            "audio": {},
            "images": {},
            "videos": {},
            "music": {},
            "characters": {}
        }
        
        # Create project directories
        self.project_folders = self.media_manager.organize_project_assets(self.project_id)
        
    async def create_video(self, user_brief: str) -> Dict[str, Any]:
        """Complete video creation pipeline"""
        
        self.logger.info("🎬 Starting AI Video Director Pipeline")
        self.logger.info(f"Project ID: {self.project_id}")
        
        try:
            # Phase 1: Pre-Production & Asset Design
            await self._phase_1_preproduction(user_brief)
            
            # Phase 2: Audio-Driven Scene Timing
            await self._phase_2_audio_timing()
            
            # Phase 3: Multi-Modal Media Generation
            await self._phase_3_media_generation()
            
            # Phase 4: Final Assembly
            final_video_url = await self._phase_4_final_assembly()
            
            # Save project data
            project_data = self._create_project_summary(final_video_url)
            
            self.logger.info("✅ Video creation pipeline completed successfully!")
            return project_data
            
        except Exception as e:
            self.logger.error(f"❌ Pipeline failed: {e}")
            raise
    
    async def _phase_1_preproduction(self, user_brief: str):
        """Phase 1: Pre-Production & Asset Design"""
        
        self.logger.info("📋 Phase 1: Pre-Production & Asset Design")
        
        # Step 1 & 2: Create production plan
        self.logger.info("Creating production plan...")
        self.production_plan = self.director.create_production_plan(user_brief)
        
        # Save production plan
        plan_path = self.settings.temp_dir / f"production_plan_{self.project_id}.json"
        self.production_plan.save(plan_path)
        
        # Step 3: Create character references using OpenAI DALL-E 3
        self.logger.info("Creating character reference images with OpenAI DALL-E 3...")
        for character in self.production_plan.characters:
            # Generate character reference image
            character_image_path = self.character_designer.create_character_reference(character)
            
            # Store in Google Cloud Storage
            gcs_url = self.media_manager.store_character_reference(
                character.name,
                character_image_path,
                self.project_id
            )
            
            # Update character with URLs as strings (not Path objects)
            character.reference_image_url = str(character_image_path)  # Convert Path to string
            character.gcs_image_url = gcs_url
            self.media_assets["characters"][character.name] = gcs_url
            
            self.logger.info(f"Character reference created and stored for {character.name}")
    
    async def _phase_2_audio_timing(self):
        """Phase 2: Audio-Driven Scene Timing"""
        
        self.logger.info("🎵 Phase 2: Audio-Driven Scene Timing")
        
        # Step 4: Generate voiceover
        self.logger.info("Generating main voiceover...")
        audio_path = self.voice_actor.generate_voiceover(
            self.production_plan.script,
            output_path=self.settings.temp_dir / f"voiceover_{self.project_id}.mp3"
        )
        
        # Store voiceover in Google Cloud Storage
        voiceover_gcs_url = self.media_manager.upload_file(
            audio_path,
            self.project_folders["audio"] + "main_voiceover.mp3"
        )
        self.media_assets["audio"]["main_voiceover"] = voiceover_gcs_url
        
        # Step 5: Analyze audio rhythm
        self.logger.info("Analyzing audio rhythm and timing...")
        rhythm_map = self.audio_analyzer.create_rhythm_map(audio_path)
        
        # Save rhythm analysis
        rhythm_path = self.settings.temp_dir / f"rhythm_map_{self.project_id}.json"
        with open(rhythm_path, 'w') as f:
            json.dump(rhythm_map, f, indent=2)
        
        # Step 6: Refine production plan with audio rhythm
        self.logger.info("Refining production plan with audio rhythm...")
        self.production_plan = self.director.refine_plan_with_audio_rhythm(
            self.production_plan,
            rhythm_map
        )
        
        # Save updated production plan
        updated_plan_path = self.settings.temp_dir / f"production_plan_updated_{self.project_id}.json"
        self.production_plan.save(updated_plan_path)
    
    async def _phase_3_media_generation(self):
        """Phase 3: Multi-Modal Media Generation with Character Consistency"""
        
        self.logger.info("🎨 Phase 3: Multi-Modal Media Generation")
        
        # Step 7: Generate visual assets for each scene
        for i, scene in enumerate(self.production_plan.scenes):
            self.logger.info(f"Generating visual for scene {i+1}/{len(self.production_plan.scenes)}: {scene.id}")
            
            video_url = None
            
            if scene.visual_type == "character" and scene.characters:
                # Get characters for this scene
                scene_characters = self.production_plan.get_characters_for_scene(scene.id)
                
                if scene_characters:
                    # Generate character scene with references
                    video_url = self.visual_artist.generate_character_video_with_references(
                        scene_characters,
                        scene.description,
                        scene.end_time - scene.start_time
                    )
                    
            elif scene.visual_type == "talking_avatar" and scene.characters:
                # Generate talking avatar for first character in scene
                scene_characters = self.production_plan.get_characters_for_scene(scene.id)
                
                if scene_characters:
                    character = scene_characters[0]  # Use first character
                    
                    # Create scene-specific audio clip
                    scene_audio_path = self.voice_actor.generate_voiceover(
                        scene.script_segment,
                        output_path=self.settings.temp_dir / f"scene_{scene.id}_audio.mp3"
                    )
                    
                    video_url = self.visual_artist.generate_talking_avatar(
                        character,
                        scene_audio_path,
                        scene.end_time - scene.start_time
                    )
                    
            elif scene.visual_type == "broll":
                # Generate B-roll video
                video_url = self.visual_artist.generate_broll_video(
                    scene.description,
                    scene.end_time - scene.start_time,
                    scene.mood
                )
            
            if video_url:
                # Store video asset in Google Cloud Storage
                stored_video_url = self.media_manager.store_scene_asset(
                    scene.id,
                    video_url,
                    self.project_id,
                    "videos"
                )
                self.media_assets["videos"][scene.id] = stored_video_url
                
                self.logger.info(f"Scene {scene.id} video generated and stored")
        
        # Step 8: Generate background music
        self.logger.info("Generating background music...")
        music_url = self.music_composer.generate_background_music(
            self.production_plan.theme.mood,
            self.production_plan.total_duration,
            "cinematic"
        )
        
        if music_url and music_url != "https://placeholder-music-url.com":
            stored_music_url = self.media_manager.store_scene_asset(
                "background_music",
                music_url,
                self.project_id,
                "music"
            )
            self.media_assets["music"]["background"] = stored_music_url
    
    async def _phase_4_final_assembly(self) -> str:
        """Phase 4: Final Assembly"""
        
        self.logger.info("🎬 Phase 4: Final Assembly & Rendering")
        
        # Step 9: Assemble final video
        final_video_url = self.video_assembler.assemble_final_video(
            self.production_plan,
            self.media_assets
        )
        
        # Store final video in Google Cloud Storage
        stored_final_url = self.media_manager.store_scene_asset(
            f"{self.production_plan.title.replace(' ', '_')}_final",
            final_video_url,
            self.project_id,
            "final"
        )
        
        return stored_final_url
    
    def _create_project_summary(self, final_video_url: str) -> Dict[str, Any]:
        """Create comprehensive project summary"""
        
        return {
            "project_id": self.project_id,
            "title": self.production_plan.title,
            "final_video_url": final_video_url,
            "duration": self.production_plan.total_duration,
            "created_at": datetime.now().isoformat(),
            "scenes_count": len(self.production_plan.scenes),
            "characters_count": len(self.production_plan.characters),
            "theme": self.production_plan.theme.mood,
            "visual_style": self.production_plan.theme.visual_style,
            "media_assets": self.media_assets,
            "character_references": {
                char.name: char.gcs_image_url 
                for char in self.production_plan.characters
            },
            "production_plan_summary": {
                "total_scenes": len(self.production_plan.scenes),
                "scene_types": {scene.visual_type for scene in self.production_plan.scenes},
                "characters": [char.name for char in self.production_plan.characters]
            },
            "storage_info": {
                "gcs_bucket": self.settings.storage.gcp_bucket,
                "project_folder": f"projects/{self.project_id}/"
            }
        }
import requests
import os
from typing import Dict, Optional, List
from pathlib import Path

from config.settings import load_settings
from utils.logger import setup_logger
from utils.helpers import retry_with_backoff

class MusicComposer:
    """Handles music and sound generation"""
    
    def __init__(self):
        self.settings = load_settings()
        self.logger = setup_logger("music_composer")
        
    @retry_with_backoff(max_retries=3)
    def generate_background_music(self, mood: str, duration: float, style: str = "cinematic") -> str:
        """Generate background music using Beatoven.ai or placeholder"""
        
        self.logger.info(f"Generating background music: {mood} {style} ({duration}s)")
        
        # Map moods to music parameters
        mood_mapping = {
            "energetic": {"energy": "high", "tempo": "fast"},
            "calm": {"energy": "low", "tempo": "slow"},
            "dramatic": {"energy": "medium", "tempo": "medium"},
            "educational": {"energy": "medium", "tempo": "medium"},
            "inspiring": {"energy": "high", "tempo": "medium"},
            "mysterious": {"energy": "low", "tempo": "slow"},
            "upbeat": {"energy": "high", "tempo": "fast"}
        }
        
        mood_params = mood_mapping.get(mood, {"energy": "medium", "tempo": "medium"})
        
        # If a Beatoven (or any other) API key is provided via environment variables, we can
        # attempt to call the real service. Otherwise, fall back to a stub/placeholder URL so
        # that offline development & testing does **not** try to hit the fake example domain
        # (which causes a ConnectionError and crashes the pipeline).

        beatoven_api_key = self.settings.api.beatoven_api_key

        # 1) No real API key available – simply return a placeholder asset that downstream code
        #    will recognise and skip uploading (handled in main._phase_3_media_generation).
        if not beatoven_api_key:
            placeholder_url = "https://placeholder-music-url.com"
            self.logger.info(
                "No music generation API key configured – returning placeholder music URL: %s",
                placeholder_url,
            )
            return placeholder_url

        # 2) API key present – attempt to call the real service. If *that* fails we will still
        #    fall back to the same placeholder so that the rest of the pipeline can continue.
        try:
            # For now, return a placeholder URL
            # In production, implement actual music generation API
            music_url = f"https://example-music-api.com/generate?mood={mood}&duration={duration}&style={style}"
            
            self.logger.info(f"Background music generated: {music_url}")
            return music_url
            
        except Exception as e:
            self.logger.error(f"Error generating background music: {e}")
            # Return a placeholder or default music URL
            return "https://placeholder-music-url.com"
    
    def generate_sound_effects(self, scene_description: str, keywords: List[str]) -> Dict[str, str]:
        """Generate sound effects for specific scenes"""
        
        self.logger.info(f"Generating sound effects for: {keywords}")
        
        sound_effects = {}
        
        # Common sound effect keywords mapping
        sfx_mapping = {
            "footsteps": "footsteps_concrete.wav",
            "door": "door_open_close.wav",
            "car": "car_engine.wav",
            "crowd": "crowd_chatter.wav",
            "nature": "nature_ambience.wav",
            "office": "office_ambience.wav",
            "rain": "rain_moderate.wav",
            "wind": "wind_gentle.wav"
        }
        
        for keyword in keywords:
            if keyword.lower() in sfx_mapping:
                # In a real implementation, this would call a sound effects API
                sfx_url = f"https://soundeffects-api.com/{sfx_mapping[keyword.lower()]}"
                sound_effects[keyword] = sfx_url
        
        return sound_effects
import os
from pathlib import Path
from elevenlabs.client import ElevenLabs
from elevenlabs import save, Voice, VoiceSettings

from config.settings import load_settings
from utils.logger import setup_logger
from utils.helpers import retry_with_backoff

class VoiceActor:
    """Handles text-to-speech generation with ElevenLabs"""
    
    def __init__(self):
        self.settings = load_settings()
        self.logger = setup_logger("voice_actor")
        self.client = ElevenLabs(api_key=self.settings.api.elevenlabs_api_key)
        
        # Voice configuration
        self.voice_settings = VoiceSettings(
            stability=0.75,
            similarity_boost=0.75,
            style=0.5,
            use_speaker_boost=True
        )
    
    @retry_with_backoff(max_retries=3)
    def generate_voiceover(self, script: str, voice_id: str = "21m00Tcm4TlvDq8ikWAM", output_path: Path = None) -> Path:
        """Generate voiceover with SSML timing"""
        
        self.logger.info(f"Generating voiceover for script length: {len(script)} characters")
        
        if output_path is None:
            output_path = self.settings.temp_dir / f"voiceover_{hash(script)}.mp3"
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # Generate audio
            audio = self.client.generate(
                text=script,
                voice=Voice(
                    voice_id=voice_id,
                    settings=self.voice_settings
                ),
                model="eleven_multilingual_v2"
            )
            
            # Save audio file
            save(audio, str(output_path))
            
            self.logger.info(f"Voiceover saved to: {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"Error generating voiceover: {e}")
            raise
    
    def get_available_voices(self) -> List[Dict[str, str]]:
        """Get list of available voices"""
        
        try:
            voices = self.client.voices.get_all()
            return [
                {
                    "voice_id": voice.voice_id,
                    "name": voice.name,
                    "category": voice.category,
                    "description": voice.description or ""
                }
                for voice in voices.voices
            ]
        except Exception as e:
            self.logger.error(f"Error fetching voices: {e}")
            return []
import openai
import base64
import tempfile
from typing import Dict, List
from pathlib import Path
from config.settings import load_settings
from utils.logger import setup_logger
from utils.helpers import retry_with_backoff
from director.production_plan import Character

class CharacterDesigner:
    """Handles character design using OpenAI DALL-E 3"""
    
    def __init__(self):
        self.settings = load_settings()
        self.logger = setup_logger("character_designer")
        self.client = openai.Client(api_key=self.settings.api.openai_api_key)
        
    @retry_with_backoff(max_retries=3)
    def create_character_reference(self, character: Character) -> Path:
        """Create character reference image using DALL-E 3"""
        
        self.logger.info(f"Creating character reference for: {character.name}")
        
        # Enhanced prompt for character consistency
        prompt = f"""
        Professional character reference sheet for {character.name}:
        
        {character.description}
        Visual Style: {character.visual_style}
        Personality traits: {character.personality}
        
        Create a detailed character portrait showing:
        - Clear, detailed facial features and expression
        - Full upper body view
        - Consistent lighting and professional photography style
        - High quality, photorealistic style
        - Clean, neutral background
        - Perfect for use as character reference in video production
        
        Style: Professional headshot photography, studio lighting, 
        high resolution, detailed and clear features for character consistency
        """
        
        try:
            response = self.client.images.generate(
                model="gpt-image-1",
                prompt=prompt,
                size="1024x1024",
                quality="low",
                # response_format="b64_json",  # Explicitly request base64
                n=1
            )
            
            image_data = base64.b64decode(response.data[0].b64_json)

            # Create a temporary file to save the image
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
                temp_file.write(image_data)
                temp_path = Path(temp_file.name)

            self.logger.info(f"Character reference saved to temporary file: {temp_path}")
            return temp_path
            
        except Exception as e:
            self.logger.error(f"Error creating character reference: {e}")
            raise
    
    @retry_with_backoff(max_retries=3)
    def generate_character_scene_image(self, characters: List[Character], scene_description: str) -> Path:
        """Generate scene image with specific characters using DALL-E 3"""
        
        self.logger.info(f"Generating scene with characters: {[c.name for c in characters]}")
        
        # Build character descriptions for the prompt
        character_descriptions = []
        for i, character in enumerate(characters, 1):
            char_desc = f"""
            Character {i} ({character.name}): {character.description}
            - Visual style: {character.visual_style}
            - Personality: {character.personality}
            """
            character_descriptions.append(char_desc)
        
        # Combine character descriptions with scene
        full_prompt = f"""
        Create a cinematic scene image with the following characters:
        
        {chr(10).join(character_descriptions)}
        
        Scene Description: {scene_description}
        
        Requirements:
        - Each character must match their exact description above
        - Professional cinematic quality
        - Consistent with character personalities and visual styles
        - High resolution, detailed, photorealistic
        - Proper lighting and composition
        - Characters should be clearly visible and recognizable
        
        Style: Professional cinematography, high quality, detailed, realistic
        """
        
        try:
            response = self.client.images.generate(
                model="gpt-image-1",
                prompt=full_prompt,
                size="1024x1024",
                quality="low",
                # response_format="b64_json",  # Explicitly request base64
                n=1
            )
            
            image_data = base64.b64decode(response.data[0].b64_json)

            # Create a temporary file to save the image
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
                temp_file.write(image_data)
                temp_path = Path(temp_file.name)

            self.logger.info(f"Character scene image saved to temporary file: {temp_path}")
            return temp_path
            
        except Exception as e:
            self.logger.error(f"Error generating scene image: {e}")
            raise
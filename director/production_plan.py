from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
import json
from pathlib import Path

@dataclass
class Character:
    name: str
    description: str
    visual_style: str
    personality: str
    reference_image_url: Optional[str] = None
    gcs_image_url: Optional[str] = None  # Google Cloud Storage URL

@dataclass
class Scene:
    id: str
    description: str
    script_segment: str
    duration_estimate: float
    visual_type: str  # 'character', 'broll', 'talking_avatar', 'static'
    characters: List[str] = None  # List of character names in this scene
    mood: str = "neutral"
    camera_angle: str = "medium"
    start_time: float = 0.0
    end_time: float = 0.0
    
    def __post_init__(self):
        if self.characters is None:
            self.characters = []

@dataclass
class Theme:
    visual_style: str
    color_palette: List[str]
    mood: str
    lighting: str = "natural"
    art_style: str = "realistic"

@dataclass
class ProductionPlan:
    project_id: str
    title: str
    theme: Theme
    script: str
    scenes: List[Scene]
    characters: List[Character]
    total_duration: float = 0.0
    created_at: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProductionPlan':
        """Create from dictionary"""
        # Convert nested objects
        theme = Theme(**data['theme'])
        characters = [Character(**char) for char in data['characters']]
        scenes = [Scene(**scene) for scene in data['scenes']]
        
        return cls(
            project_id=data['project_id'],
            title=data['title'],
            theme=theme,
            script=data['script'],
            scenes=scenes,
            characters=characters,
            total_duration=data.get('total_duration', 0.0),
            created_at=data.get('created_at', '')
        )
    
    def save(self, filepath: Path) -> None:
        """Save production plan to file"""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load(cls, filepath: Path) -> 'ProductionPlan':
        """Load production plan from file"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)
    
    def get_characters_for_scene(self, scene_id: str) -> List[Character]:
        """Get character objects for a specific scene"""
        scene = next((s for s in self.scenes if s.id == scene_id), None)
        if not scene or not scene.characters:
            return []
        
        return [char for char in self.characters if char.name in scene.characters]
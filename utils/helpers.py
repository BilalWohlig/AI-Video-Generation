import hashlib
import json
import time
import asyncio
from functools import wraps
from typing import Any, Dict, Callable, List
import requests
from pathlib import Path

def retry_with_backoff(max_retries: int = 3, backoff_factor: float = 1.0):
    """Decorator for retrying functions with exponential backoff"""
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise e
                    
                    wait_time = backoff_factor * (2 ** attempt)
                    time.sleep(wait_time)
                    
            return None
        return wrapper
    return decorator

def generate_hash(content: str) -> str:
    """Generate MD5 hash for content caching"""
    return hashlib.md5(content.encode()).hexdigest()

def save_json(data: Dict[Any, Any], filepath: Path) -> None:
    """Save data as JSON file"""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)

def load_json(filepath: Path) -> Dict[Any, Any]:
    """Load JSON file"""
    with open(filepath, 'r') as f:
        return json.load(f)

def download_file(url: str, filepath: Path) -> Path:
    """Download file from URL"""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    with open(filepath, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    
    return filepath

def create_character_reference_prompt(characters: List[Dict], scene_description: str) -> str:
    """Create prompt with character references for scene generation"""
    
    if not characters:
        return scene_description
    
    # Build character reference string
    char_refs = []
    for i, char in enumerate(characters, 1):
        char_refs.append(f"{char['name']} (image {i})")
    
    # Combine with scene description
    if char_refs:
        char_ref_text = ", ".join(char_refs)
        enhanced_prompt = f"{char_ref_text} {scene_description}"
        return enhanced_prompt
    
    return scene_description
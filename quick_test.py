import asyncio
from main import AIVideoDirectorPipeline

async def main():
    """Main entry point"""
    
    # Example usage
    user_brief = """
    Create a 2-3 minute educational video about the history of artificial intelligence.
    
    Style: Modern, professional, engaging documentary style
    Tone: Informative but accessible, inspiring
    
    Content to include:
    - Brief introduction to what AI is
    - Key historical milestones (1950s-present)
    - Important figures like Alan Turing, John McCarthy
    - Current applications and future implications
    - Conclusion about AI's potential
    
    Visual style: Clean, modern, with a mix of character presentations and B-roll footage
    Mood: Inspiring and educational
    
    Characters: Include a professional AI researcher as the main presenter
    """
    
    # Initialize pipeline
    pipeline = AIVideoDirectorPipeline()
    
    try:
        # Create video
        result = await pipeline.create_video(user_brief)
        
        print("🎉 Video Creation Complete!")
        print(f"📹 Final Video: {result['final_video_url']}")
        print(f"⏱️  Duration: {result['duration']:.1f} seconds")
        print(f"🎬 Scenes: {result['scenes_count']}")
        print(f"👥 Characters: {result['characters_count']}")
        print(f"🎨 Theme: {result['theme']}")
        print(f"📁 GCS Bucket: {result['storage_info']['gcs_bucket']}")
        print(f"📂 Project Folder: {result['storage_info']['project_folder']}")
        
        # Print character references
        print("\n👥 Character References:")
        for name, url in result['character_references'].items():
            print(f"  {name}: {url}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error creating video: {e}")
        raise

if __name__ == "__main__":
    # Run the pipeline
    result = asyncio.run(main())
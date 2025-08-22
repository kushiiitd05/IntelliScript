import json
import os
from typing import Dict, Any, Optional
from .cache_manager import CacheManager

class ProgressTracker:
    def __init__(self):
        self.cache_manager = CacheManager()
    
    def update_progress(self, session_id: str, message: str, progress: int, stage: str = None):
        """Update progress for a session"""
        progress_data = {
            "session_id": session_id,
            "message": message,
            "progress": progress,
            "stage": stage or message,
            "status": "completed" if progress >= 100 else "processing" if progress >= 0 else "error"
        }
        
        # Save to cache if available
        if self.cache_manager.client:
            try:
                key = f"progress:{session_id}"
                self.cache_manager.client.setex(key, 3600, json.dumps(progress_data))
            except Exception as e:
                print(f"Progress cache error: {e}")
        
        # Always save to file as backup
        progress_dir = "progress"
        os.makedirs(progress_dir, exist_ok=True)
        
        try:
            with open(f"{progress_dir}/{session_id}.json", 'w') as f:
                json.dump(progress_data, f)
        except Exception as e:
            print(f"Progress file error: {e}")
    
    def get_progress(self, session_id: str) -> Dict[str, Any]:
        """Get current progress for a session"""
        # Try cache first
        if self.cache_manager.client:
            try:
                key = f"progress:{session_id}"
                cached_progress = self.cache_manager.client.get(key)
                if cached_progress:
                    return json.loads(cached_progress)
            except Exception as e:
                print(f"Progress cache get error: {e}")
        
        # Fallback to file
        progress_file = f"progress/{session_id}.json"
        if os.path.exists(progress_file):
            try:
                with open(progress_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Progress file read error: {e}")
        
        # Default response
        return {
            "session_id": session_id,
            "message": "Processing...",
            "progress": 0,
            "stage": "Initializing",
            "status": "processing"
        }
import os
import subprocess
import torch
from pyannote.audio import Pipeline
from typing import List, Dict, Optional

class DiarizationService:
    def __init__(self):
        self.pipeline = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.hf_token = os.getenv("HF_TOKEN")
    
    async def diarize(self, audio_path: str, num_speakers: Optional[int] = None, 
                     min_speakers: Optional[int] = None, max_speakers: Optional[int] = None) -> List[Dict]:
        """Perform speaker diarization"""
        print("--- Starting Speaker Diarization ---")
        
        if self.device == "cuda":
            print("🚀 Found GPU, using CUDA for fast processing.")
        else:
            print("⚠️ No GPU found, using CPU. This will be much slower.")
        
        # Pre-process audio
        print("Step 1: Standardizing audio format...")
        temp_dir = "temp_audio_for_diarization"
        os.makedirs(temp_dir, exist_ok=True)
        processed_audio_path = os.path.join(temp_dir, "diarization_input.wav")
        
        try:
            command = [
                "ffmpeg", "-i", audio_path,
                "-vn", "-acodec", "pcm_s16le",
                "-ar", "16000", "-ac", "1", "-y", processed_audio_path
            ]
            subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("✅ Audio standardized successfully.")
        except Exception as e:
            raise Exception(f"Error during FFmpeg pre-processing: {e}")
        
        # Load diarization pipeline
        print("Step 2: Loading diarization model...")
        try:
            if self.pipeline is None:
                self.pipeline = Pipeline.from_pretrained(
                    "pyannote/speaker-diarization-3.1",
                    use_auth_token=self.hf_token
                ).to(torch.device(self.device))
            print("✅ Model loaded successfully.")
        except Exception as e:
            raise Exception(f"Error loading diarization model: {e}")
        
        # Run diarization
        print("Step 3: Running diarization inference...")
        try:
            diarization = self.pipeline(
                processed_audio_path,
                num_speakers=num_speakers,
                min_speakers=min_speakers,
                max_speakers=max_speakers
            )
            
            results = []
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                results.append({
                    "start": round(turn.start, 2),
                    "end": round(turn.end, 2),
                    "speaker": speaker
                })
            
            print("✅ Diarization complete.")
            return results
            
        except Exception as e:
            raise Exception(f"Error during diarization inference: {e}")
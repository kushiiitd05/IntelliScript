import whisper
import torch
from typing import Dict, Any

class TranscriptionService:
    def __init__(self):
        self.model = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
    
    async def transcribe(self, audio_path: str, word_timestamps: bool = True) -> Dict[str, Any]:
        """Transcribe audio using Whisper"""
        print(f"Device used for transcription: {'GPU' if self.device == 'cuda' else 'CPU'}")
        
        try:
            # Load model if not already loaded
            if self.model is None:
                print("Loading Whisper model...")
                self.model = whisper.load_model("medium.en", device=self.device)
            
            print("Model loaded successfully.")
            
            # Load and transcribe audio
            audio_data = whisper.load_audio(audio_path)
            print("Audio loaded successfully.")
            
            result = self.model.transcribe(
                audio_data,
                verbose=False,
                word_timestamps=word_timestamps
            )
            
            print("Transcription complete.")
            return result
            
        except Exception as e:
            raise Exception(f"Transcription failed: {e}")
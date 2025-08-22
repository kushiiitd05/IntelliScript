import ffmpeg
import os
import subprocess
import json
import librosa
import soundfile as sf
import noisereduce as nr
import numpy as np
from typing import Optional

class EnhancedAudioProcessor:
    def __init__(self):
        self.temp_dir = "temp_audio"
        os.makedirs(self.temp_dir, exist_ok=True)
    
    async def extract_and_clean_audio(self, video_path: str) -> str:
        """Extract and apply enhanced cleaning to audio"""
        print("🔧 Starting enhanced audio processing...")
        
        # Step 1: Extract basic audio
        basic_audio = await self._extract_basic_audio(video_path)
        if not basic_audio:
            raise Exception("Failed to extract basic audio")
        
        # Step 2: Apply enhanced cleaning pipeline
        enhanced_audio = await self._enhanced_audio_pipeline(video_path)
        if not enhanced_audio:
            print("⚠️ Enhanced cleaning failed, using basic audio")
            return basic_audio
        
        return enhanced_audio
    
    async def _extract_basic_audio(self, video_path: str) -> str:
        """Extract basic audio as fallback"""
        output = os.path.join(self.temp_dir, f"{os.path.basename(video_path)}_basic.wav")
        try:
            (
                ffmpeg
                .input(video_path)
                .output(output, acodec='pcm_s16le', ac=1, ar='16000')
                .overwrite_output()
                .run(quiet=True)
            )
            return output
        except Exception as e:
            print(f"Basic audio extraction error: {e}")
            return None
    
    async def _enhanced_audio_pipeline(self, video_path: str, two_pass: bool = True) -> Optional[str]:
        """Apply enhanced audio cleaning pipeline with noise reduction"""
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        
        # Intermediate files
        raw_audio = os.path.join(self.temp_dir, f"{base_name}_raw.wav")
        denoised_audio = os.path.join(self.temp_dir, f"{base_name}_denoised.wav")
        cleaned_audio = os.path.join(self.temp_dir, f"{base_name}_cleaned.wav")
        final_output = os.path.join(self.temp_dir, f"{base_name}_enhanced.wav")
        
        try:
            # Step 1: Extract high-quality float32 audio
            print("  → Step 1: Extracting high-quality audio...")
            (
                ffmpeg
                .input(video_path)
                .output(raw_audio, vn=None, ac=1, acodec="pcm_f32le", ar="44100")
                .overwrite_output()
                .run(quiet=True)
            )
            
            # Step 2: AI-powered noise reduction
            print("  → Step 2: Applying AI noise reduction...")
            await self._apply_noise_reduction(raw_audio, denoised_audio)
            
            # Step 3: Advanced audio cleaning chain
            print("  → Step 3: Advanced audio filtering...")
            af_chain = [
                "highpass=f=80",           # Remove low-frequency rumble
                "lowpass=f=8000",          # Remove high-frequency noise
                "adeclick",                # Remove clicks/pops
                "afftdn=nr=25:nf=-20",     # FFT denoiser (stronger)
                "deesser=f=6000:width=4000:threshold=0.15",  # De-essing
                "compand=0.1,0.3:-80,-80,-40,-25,-10,-10,0,0:6:0:-45",  # Compressor
                "dynaudnorm=f=200:g=15:s=9:r=0.95"  # Dynamic range normalization
            ]
            
            (
                ffmpeg
                .input(denoised_audio)
                .output(cleaned_audio, af=":".join(af_chain), acodec="pcm_f32le")
                .overwrite_output()
                .run(quiet=True)
            )
            
            # Step 4: Two-pass loudness normalization (if requested)
            if two_pass:
                print("  → Step 4: Two-pass loudness normalization...")
                await self._two_pass_loudness_normalize(cleaned_audio, final_output)
            else:
                # Single-pass normalization
                (
                    ffmpeg
                    .input(cleaned_audio)
                    .output(
                        final_output,
                        af="loudnorm=I=-16:LRA=7:TP=-1.5,aresample=16000:resampler=soxr:precision=28",
                        ac=1, acodec="pcm_s16le"
                    )
                    .overwrite_output()
                    .run(quiet=True)
                )
            
            print("✅ Enhanced audio processing complete")
            return final_output
            
        except Exception as e:
            print(f"❌ Enhanced audio processing failed: {e}")
            return None
        
        finally:
            # Cleanup intermediate files
            for temp_file in [raw_audio, denoised_audio, cleaned_audio]:
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except:
                        pass
    
    async def _apply_noise_reduction(self, input_path: str, output_path: str):
        """Apply AI-powered noise reduction using noisereduce library"""
        try:
            # Load audio
            audio_data, sample_rate = librosa.load(input_path, sr=None)
            
            # Apply noise reduction
            # Use the first 1 second as noise sample
            noise_sample_length = min(sample_rate, len(audio_data) // 10)
            reduced_audio = nr.reduce_noise(
                y=audio_data,
                sr=sample_rate,
                y_noise=audio_data[:noise_sample_length],
                prop_decrease=0.8,
                stationary=False,
                n_fft=2048,
                win_length=2048,
                hop_length=512
            )
            
            # Save the processed audio
            sf.write(output_path, reduced_audio, sample_rate, format='WAV', subtype='FLOAT')
            
        except Exception as e:
            print(f"Noise reduction error: {e}")
            # If noise reduction fails, just copy the original
            import shutil
            shutil.copy2(input_path, output_path)
    
    async def _two_pass_loudness_normalize(self, input_path: str, output_path: str):
        """Perform two-pass loudness normalization for optimal results"""
        try:
            # First pass: measure loudness
            cmd = [
                "ffmpeg", "-i", input_path, 
                "-af", "loudnorm=I=-16:LRA=7:TP=-1.5:print_format=json",
                "-f", "null", "-"
            ]
            
            result = subprocess.run(
                cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True
            )
            
            # Parse measurement results
            stderr_text = result.stderr
            json_start = stderr_text.rfind("{")
            json_end = stderr_text.rfind("}") + 1
            
            if json_start != -1 and json_end != -1:
                stats = json.loads(stderr_text[json_start:json_end])
                
                # Second pass: apply measured normalization
                normalization_args = (
                    f"loudnorm=I=-16:LRA=7:TP=-1.5:"
                    f"measured_I={stats['input_i']}:"
                    f"measured_LRA={stats['input_lra']}:"
                    f"measured_TP={stats['input_tp']}:"
                    f"measured_thresh={stats['input_thresh']}:"
                    f"offset={stats['target_offset']}:linear=true"
                )
                
                (
                    ffmpeg
                    .input(input_path)
                    .output(
                        output_path,
                        af=f"{normalization_args},aresample=16000:resampler=soxr:precision=28,alimiter=limit=0.97",
                        ac=1, acodec="pcm_s16le"
                    )
                    .overwrite_output()
                    .run(quiet=True)
                )
            else:
                raise Exception("Could not parse loudness measurement")
                
        except Exception as e:
            print(f"Two-pass normalization error: {e}")
            # Fallback to single-pass
            (
                ffmpeg
                .input(input_path)
                .output(
                    output_path,
                    af="loudnorm=I=-16:LRA=7:TP=-1.5,aresample=16000:resampler=soxr:precision=28,alimiter=limit=0.97",
                    ac=1, acodec="pcm_s16le"
                )
                .overwrite_output()
                .run(quiet=True)
            )
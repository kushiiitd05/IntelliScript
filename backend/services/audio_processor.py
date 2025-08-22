import ffmpeg
import os
import subprocess
import json
from typing import Optional

class AudioProcessor:
    async def extract_and_clean_audio(self, video_path: str) -> str:
        """Extract and clean audio from video"""
        # First extract basic audio
        audio_path = await self.extract_audio(video_path)
        
        # Then apply master cleaning
        clean_audio_path = await self.master_clean_audio(video_path)
        
        return clean_audio_path
    
    async def extract_audio(self, video_path: str) -> str:
        """Extract audio from video"""
        output = os.path.splitext(video_path)[0] + '_extracted_audio.wav'
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
            raise Exception(f"Error extracting audio: {e}")
    
    async def master_clean_audio(self, video_path: str, out_wav: Optional[str] = None, two_pass: bool = True) -> str:
        """Apply master audio cleaning pipeline"""
        if out_wav is None:
            out_wav = os.path.splitext(video_path)[0] + "_master_clean.wav"
        
        tmp_f32 = os.path.splitext(out_wav)[0] + "_f32.wav"
        pre = os.path.splitext(out_wav)[0] + "_pre.wav"
        norm = os.path.splitext(out_wav)[0] + "_norm.wav"

        try:
            # 1) Extract to float32 mono
            (
                ffmpeg
                .input(video_path)
                .output(tmp_f32, vn=None, ac=1, acodec="pcm_f32le")
                .overwrite_output()
                .run(quiet=True)
            )

            # 2) Apply cleaning chain
            af = "highpass=f=80,adeclick,afftdn=nr=20,deesser=f=6000:width=4000:threshold=0.2,dynaudnorm=f=200:g=15"
            (
                ffmpeg
                .input(tmp_f32)
                .output(pre, af=af, acodec="pcm_f32le")
                .overwrite_output()
                .run(quiet=True)
            )

            if two_pass:
                # 3a) Measure loudness
                cmd = [
                    "ffmpeg", "-i", pre, "-af", "loudnorm=I=-19:LRA=7:TP=-1.5:print_format=json",
                    "-f", "null", "-"
                ]
                res = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
                
                # Parse JSON from stderr
                text = res.stderr
                start = text.rfind("{")
                end = text.rfind("}")
                if start != -1 and end != -1:
                    stats = json.loads(text[start:end+1])
                    
                    args = (
                        f"loudnorm=I=-19:LRA=7:TP=-1.5:"
                        f"measured_I={stats['input_i']}:measured_LRA={stats['input_lra']}:"
                        f"measured_TP={stats['input_tp']}:measured_thresh={stats['input_thresh']}:"
                        f"offset={stats['target_offset']}:linear=true"
                    )

                    # 3b) Apply measured loudness
                    (
                        ffmpeg
                        .input(pre)
                        .output(norm, af=args, acodec="pcm_f32le")
                        .overwrite_output()
                        .run(quiet=True)
                    )
                    src = norm
                else:
                    src = pre
            else:
                src = pre

            # 4) Final resampling and limiting
            af_final = "aresample=16000:resampler=soxr:precision=28,alimiter=limit=0.97"
            (
                ffmpeg
                .input(src)
                .output(out_wav, af=af_final, ac=1, acodec="pcm_s16le")
                .overwrite_output()
                .run(quiet=True)
            )

            # Cleanup temp files
            for temp_file in [tmp_f32, pre, norm]:
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except:
                        pass

            return out_wav
            
        except Exception as e:
            raise Exception(f"Error in master audio cleaning: {e}")
import os
import yt_dlp
import re
from typing import Optional

class VideoProcessor:
    def __init__(self):
        self.download_dir = "downloads"
        os.makedirs(self.download_dir, exist_ok=True)
    
    def is_youtube_url(self, url: str) -> bool:
        """Check if the input is a YouTube URL"""
        youtube_patterns = [
            r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=[\w-]+',
            r'(?:https?://)?(?:www\.)?youtu\.be/[\w-]+',
            r'(?:https?://)?(?:www\.)?youtube\.com/embed/[\w-]+',
            r'(?:https?://)?(?:www\.)?youtube\.com/v/[\w-]+',
            r'(?:https?://)?(?:m\.)?youtube\.com/watch\?v=[\w-]+'
        ]
        
        for pattern in youtube_patterns:
            if re.match(pattern, url.strip()):
                return True
        return False
    
    async def download_video(self, url: str) -> str:
        """Download video from YouTube URL"""
        if not self.is_youtube_url(url):
            raise ValueError("Invalid YouTube URL")
        
        ydl_opts = {
            'format': 'bestvideo[height<=720]+bestaudio/best',
            'outtmpl': os.path.join(self.download_dir, '%(title)s.%(ext)s'),
            'merge_output_format': 'mp4',
            'concurrent_fragments': 10,
            'http_chunk_size': 10485760,
            'retries': 10,
            'fragment_retries': 10,
            'nopart': True
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                print(f"Video downloaded: {filename}")
                return filename
        except Exception as e:
            raise Exception(f"Error downloading video: {e}")
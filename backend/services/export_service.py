import os
import json
import zipfile
from typing import Dict, Any
from datetime import timedelta

class ExportService:
    async def export_results(self, session_id: str, format: str) -> str:
        """Export results in various formats"""
        results_dir = f"results/{session_id}"
        export_dir = f"exports/{session_id}"
        os.makedirs(export_dir, exist_ok=True)
        
        # Load results
        with open(f"{results_dir}/results.json", 'r', encoding='utf-8') as f:
            results = json.load(f)
        
        if format == "txt":
            return await self._export_txt(results, export_dir)
        elif format == "md":
            return await self._export_markdown(results, export_dir)
        elif format == "srt":
            return await self._export_srt(results, export_dir)
        elif format == "vtt":
            return await self._export_vtt(results, export_dir)
        elif format == "json":
            return await self._export_json(results, export_dir)
        elif format == "zip":
            return await self._export_zip(results, export_dir)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    async def _export_txt(self, results: Dict[str, Any], export_dir: str) -> str:
        """Export as plain text"""
        file_path = os.path.join(export_dir, "transcript.txt")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(results['transcript']['text'])
        return file_path
    
    async def _export_markdown(self, results: Dict[str, Any], export_dir: str) -> str:
        """Export as formatted markdown"""
        file_path = os.path.join(export_dir, "transcript.md")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("# Video Transcript\n\n")
            
            # Add summary if available
            if 'summary' in results and results['summary']:
                f.write("## Summary\n\n")
                f.write(results['summary'])
                f.write("\n\n")
            
            f.write("## Transcript\n\n")
            
            # Add speaker-aware transcript if diarization available
            if 'diarization' in results and results['diarization']:
                # Merge with diarization (simplified version)
                for segment in results['transcript'].get('segments', []):
                    start_time = str(timedelta(seconds=int(segment['start'])))
                    f.write(f"**[{start_time}]** {segment['text']}\n\n")
            else:
                f.write(results['transcript']['text'])
        
        return file_path
    
    async def _export_srt(self, results: Dict[str, Any], export_dir: str) -> str:
        """Export as SRT subtitles"""
        file_path = os.path.join(export_dir, "subtitles.srt")
        with open(file_path, 'w', encoding='utf-8') as f:
            segments = results['transcript'].get('segments', [])
            for i, segment in enumerate(segments, 1):
                start_time = self._format_srt_time(segment['start'])
                end_time = self._format_srt_time(segment['end'])
                f.write(f"{i}\n")
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{segment['text']}\n\n")
        return file_path
    
    async def _export_vtt(self, results: Dict[str, Any], export_dir: str) -> str:
        """Export as WebVTT subtitles"""
        file_path = os.path.join(export_dir, "subtitles.vtt")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("WEBVTT\n\n")
            segments = results['transcript'].get('segments', [])
            for segment in segments:
                start_time = self._format_vtt_time(segment['start'])
                end_time = self._format_vtt_time(segment['end'])
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{segment['text']}\n\n")
        return file_path
    
    async def _export_json(self, results: Dict[str, Any], export_dir: str) -> str:
        """Export as JSON"""
        file_path = os.path.join(export_dir, "analysis.json")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
        return file_path
    
    async def _export_zip(self, results: Dict[str, Any], export_dir: str) -> str:
        """Export all formats in a ZIP file"""
        zip_path = os.path.join(export_dir, "complete_analysis.zip")
        
        # Create individual exports
        txt_path = await self._export_txt(results, export_dir)
        md_path = await self._export_markdown(results, export_dir)
        srt_path = await self._export_srt(results, export_dir)
        vtt_path = await self._export_vtt(results, export_dir)
        json_path = await self._export_json(results, export_dir)
        
        # Create ZIP file
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            zipf.write(txt_path, "transcript.txt")
            zipf.write(md_path, "transcript.md")
            zipf.write(srt_path, "subtitles.srt")
            zipf.write(vtt_path, "subtitles.vtt")
            zipf.write(json_path, "analysis.json")
        
        return zip_path
    
    def _format_srt_time(self, seconds: float) -> str:
        """Format time for SRT format"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millisecs = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"
    
    def _format_vtt_time(self, seconds: float) -> str:
        """Format time for WebVTT format"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"
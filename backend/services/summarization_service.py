import os
from openai import OpenAI
from typing import List, Optional

class SummarizationService:
    def __init__(self):
        self.nebius_client = OpenAI(
            base_url="https://api.studio.nebius.ai/v1",
            api_key=os.getenv("NEBIUS_API_KEY")
        )
    
    def split_text_into_chunks(self, text: str, chunk_size: int = 1500, overlap: int = 150) -> List[str]:
        """Split text into overlapping chunks"""
        words = text.split()
        if not words:
            return []
        
        chunks = []
        start = 0
        while start < len(words):
            end = start + chunk_size
            chunk_words = words[start:end]
            chunks.append(" ".join(chunk_words))
            if end >= len(words):
                break
            start += (chunk_size - overlap)
        return chunks
    
    def call_nebius_llm(self, prompt: str, system_prompt: str = "You are a helpful assistant.") -> Optional[str]:
        """Call Nebius LLM API"""
        try:
            response = self.nebius_client.chat.completions.create(
                model="meta-llama/Meta-Llama-3.1-405B-Instruct",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1024,
                temperature=0.3,
                top_p=0.9
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"API Error: {e}")
            return None
    
    async def summarize(self, transcript: str) -> Optional[str]:
        """Perform map-reduce summarization"""
        print("Starting Summarization Process")
        
        # Step A: Split transcript into chunks
        print("Step A: Splitting the transcript into chunks...")
        chunks = self.split_text_into_chunks(transcript)
        if not chunks:
            return None
        print(f"Successfully split into {len(chunks)} chunks.")
        
        # Step B: Summarize each chunk
        print("Step B: Summarizing each chunk individually...")
        chunk_summaries = []
        for i, chunk in enumerate(chunks):
            print(f"Summarizing chunk {i+1}/{len(chunks)}...")
            prompt = f"This is one part of a longer meeting transcript. Provide a concise summary of THIS SPECIFIC SEGMENT. Focus on the main points, decisions, and action items mentioned.\n\nTranscript Segment:\n---\n{chunk}"
            summary = self.call_nebius_llm(prompt, "You are an expert at summarizing text.")
            if summary:
                chunk_summaries.append(summary)
        
        if not chunk_summaries:
            return None
        
        # Step C: Create final report
        print("Step C: Creating the final report...")
        combined_summaries = "\n\n---\n\n".join(chunk_summaries)
        final_prompt = f"""
        You are an expert meeting analyst. You will be provided with a series of summaries from a single meeting.
        Your task is to synthesize these into a single, cohesive, and well-structured final report.

        The final report must have the following three sections:
        1. **Overall Summary:** A brief, 2-4 sentence paragraph that captures the essence of the meeting.
        2. **Main Topics Discussed:** A short list of the primary topics covered.
        3. **Key Points & Action Items:** A bulleted list detailing the most important points, decisions made, and specific action items.

        Here are the summaries from the meeting chunks:\n---\n{combined_summaries}\n---

        Generate the final, structured report.
        """
        final_summary = self.call_nebius_llm(final_prompt, "You are an expert meeting analyst creating a final report.")
        
        return final_summary
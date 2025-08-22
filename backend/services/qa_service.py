import os
import json
from typing import Dict, Any
from langchain_groq import ChatGroq
from langchain.prompts import PromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

class QAService:
    def __init__(self):
        self.groq_llm = ChatGroq(
            model="llama-3.1-8b-instant",
            groq_api_key=os.getenv("GROQ_API_KEY")
        )
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    def create_speaker_aware_documents(self, speaker_chunks):
        """Create LangChain documents with speaker metadata"""
        documents = []
        for i, chunk in enumerate(speaker_chunks):
            content = chunk['text']
            metadata = {
                "speaker": chunk['speaker'],
                "start_time": round(chunk['start'], 2),
                "end_time": round(chunk['end'], 2),
                "chunk_id": i
            }
            doc = Document(page_content=content, metadata=metadata)
            documents.append(doc)
        return documents
    
    async def answer_question(self, session_id: str, question: str) -> Dict[str, Any]:
        """Answer question using RAG pipeline"""
        try:
            # Load session results
            results_path = f"results/{session_id}/results.json"
            with open(results_path, 'r', encoding='utf-8') as f:
                results = json.load(f)
            
            # Merge transcription and diarization for context-aware chunks
            speaker_chunks = self.merge_transcription_diarization(
                results['transcript'], 
                results['diarization']
            )
            
            # Create documents
            documents = self.create_speaker_aware_documents(speaker_chunks)
            
            # Create vector store
            vectorstore = FAISS.from_documents(documents, self.embeddings)
            
            # Create Q&A chain
            prompt = PromptTemplate.from_template(
                """
                Answer the question based ONLY on the provided context.
                Be concise and do not make up information. If the context does not contain the answer, say "I cannot answer the question based on the provided context."
                For context, each piece of text is attributed to a speaker (e.g., SPEAKER_01) and has start/end timestamps in seconds.

                <context>
                {context}
                </context>

                Question: {input}
                """
            )
            
            document_chain = create_stuff_documents_chain(self.groq_llm, prompt)
            retriever = vectorstore.as_retriever()
            chain = create_retrieval_chain(retriever, document_chain)
            
            # Get answer
            response = chain.invoke({"input": question})
            
            return {
                "answer": response["answer"],
                "context": [{"content": doc.page_content, "metadata": doc.metadata} 
                          for doc in response.get("context", [])]
            }
            
        except Exception as e:
            return {"answer": f"Error processing question: {str(e)}", "context": []}
    
    def merge_transcription_diarization(self, whisper_result, diarization_result, min_gap_seconds=0.3):
        """Merge word-level timestamps with speaker diarization"""
        import pandas as pd
        
        if not whisper_result or 'words' not in whisper_result:
            return []
        if not diarization_result:
            return []
        
        # Create speaker turns dataframe
        speaker_turns = []
        for turn in diarization_result:
            speaker_turns.append({
                'start': turn['start'],
                'end': turn['end'],
                'speaker': turn['speaker']
            })
        speaker_df = pd.DataFrame(speaker_turns)
        
        def find_speaker(time):
            match = speaker_df[(speaker_df['start'] <= time) & (speaker_df['end'] >= time)]
            return match['speaker'].iloc[0] if not match.empty else "UNKNOWN"
        
        # Assign speakers to words
        words_with_speakers = []
        for word in whisper_result['words']:
            midpoint = word.get('start', 0) + (word.get('end', 0) - word.get('start', 0)) / 2
            speaker = find_speaker(midpoint)
            words_with_speakers.append({**word, 'speaker': speaker})
        
        # Group into speaker chunks
        speaker_chunks = []
        if not words_with_speakers:
            return []
        
        current_chunk = {
            'speaker': words_with_speakers[0]['speaker'],
            'text': words_with_speakers[0]['word'],
            'start': words_with_speakers[0]['start'],
            'end': words_with_speakers[0]['end']
        }
        
        for i in range(1, len(words_with_speakers)):
            word_info = words_with_speakers[i]
            prev_word_info = words_with_speakers[i-1]
            
            speaker_changed = word_info['speaker'] != current_chunk['speaker']
            is_long_pause = (word_info.get('start', 0) - prev_word_info.get('end', 0)) > min_gap_seconds
            
            if speaker_changed or is_long_pause:
                speaker_chunks.append(current_chunk)
                current_chunk = {
                    'speaker': word_info['speaker'],
                    'text': word_info['word'],
                    'start': word_info['start'],
                    'end': word_info['end']
                }
            else:
                current_chunk['text'] += word_info['word']
                current_chunk['end'] = word_info['end']
        
        speaker_chunks.append(current_chunk)
        
        # Clean up text
        for chunk in speaker_chunks:
            chunk['text'] = chunk['text'].strip()
        
        return speaker_chunks
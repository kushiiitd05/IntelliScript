import React, { useState, useRef, useCallback } from 'react';
import { Upload, Youtube, Play, Pause, Download, MessageSquare, FileText, Users, Clock, Zap, CheckCircle, AlertCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import axios from 'axios';

interface ProcessingProgress {
  stage: string;
  progress: number;
  status: 'pending' | 'processing' | 'completed' | 'error';
  message: string;
}

interface TranscriptResult {
  transcript: any;
  diarization: any;
  summary: string;
  chapters: any[];
  video_path: string;
  audio_path: string;
}

interface QAResponse {
  answer: string;
  context: Array<{
    content: string;
    metadata: {
      speaker?: string;
      start_time?: number;
      end_time?: number;
    };
  }>;
}

function App() {
  const [currentView, setCurrentView] = useState<'upload' | 'processing' | 'results'>('upload');
  const [sessionId, setSessionId] = useState<string>('');
  const [progress, setProgress] = useState<ProcessingProgress[]>([]);
  const [results, setResults] = useState<TranscriptResult | null>(null);
  const [activeTab, setActiveTab] = useState<'transcript' | 'summary' | 'qa' | 'chapters'>('transcript');
  const [question, setQuestion] = useState('');
  const [qaResponse, setQAResponse] = useState<QAResponse | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [urlInput, setUrlInput] = useState('');

  const API_BASE = 'http://localhost:8000';

  const handleFileUpload = useCallback(async (file: File) => {
    if (!file) return;
    
    setIsUploading(true);
    setCurrentView('processing');

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await axios.post(`${API_BASE}/api/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      setSessionId(response.data.session_id);
      startProgressTracking(response.data.session_id);
    } catch (error) {
      console.error('Upload error:', error);
      alert('Upload failed. Please try again.');
      setCurrentView('upload');
    } finally {
      setIsUploading(false);
    }
  }, []);

  const handleUrlSubmit = useCallback(async () => {
    if (!urlInput.trim()) return;

    setIsProcessing(true);
    setCurrentView('processing');

    try {
      const tempSessionId = Date.now().toString();
      const response = await axios.post(`${API_BASE}/api/process-url`, {
        session_id: tempSessionId,
        url: urlInput.trim(),
        language: 'en'
      });

      setSessionId(tempSessionId);
      startProgressTracking(tempSessionId);
    } catch (error) {
      console.error('URL processing error:', error);
      alert('URL processing failed. Please check the URL and try again.');
      setCurrentView('upload');
    } finally {
      setIsProcessing(false);
    }
  }, [urlInput]);

  const startProgressTracking = useCallback((id: string) => {
    const interval = setInterval(async () => {
      try {
        const progressResponse = await axios.get(`${API_BASE}/api/progress/${id}`);
        const progressData = progressResponse.data;

        if (progressData.progress >= 100 || progressData.status === 'completed') {
          clearInterval(interval);
          
          // Fetch results
          const resultsResponse = await axios.get(`${API_BASE}/api/results/${id}`);
          if (resultsResponse.data.status === 'completed') {
            setResults(resultsResponse.data.results);
            setCurrentView('results');
          }
        }

        // Update progress display
        setProgress(prevProgress => {
          const newStage = {
            stage: progressData.stage || 'Processing',
            progress: progressData.progress || 0,
            status: progressData.progress >= 100 ? 'completed' as const : 'processing' as const,
            message: progressData.message || ''
          };

          const existingIndex = prevProgress.findIndex(p => p.stage === newStage.stage);
          if (existingIndex >= 0) {
            const updated = [...prevProgress];
            updated[existingIndex] = newStage;
            return updated;
          } else {
            return [...prevProgress, newStage];
          }
        });

      } catch (error) {
        console.error('Progress tracking error:', error);
        clearInterval(interval);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, []);

  const handleQuestionSubmit = useCallback(async () => {
    if (!question.trim() || !sessionId) return;

    try {
      const response = await axios.post(`${API_BASE}/api/ask`, {
        session_id: sessionId,
        question: question.trim()
      });

      setQAResponse(response.data);
    } catch (error) {
      console.error('Q&A error:', error);
      alert('Failed to get answer. Please try again.');
    }
  }, [question, sessionId]);

  const handleExport = useCallback(async (format: string) => {
    if (!sessionId) return;

    try {
      const response = await axios.get(`${API_BASE}/api/export/${sessionId}/${format}`, {
        responseType: 'blob'
      });

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `transcript.${format}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Export error:', error);
      alert('Export failed. Please try again.');
    }
  }, [sessionId]);

  const formatTimestamp = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  if (currentView === 'upload') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100">
        <div className="container mx-auto px-6 py-12">
          {/* Header */}
          <motion.div 
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center mb-16"
          >
            <div className="flex items-center justify-center gap-3 mb-6">
              <div className="p-3 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-2xl text-white shadow-lg">
                <Zap size={32} />
              </div>
              <h1 className="text-5xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
                IntelliScript
              </h1>
            </div>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto leading-relaxed">
              Transform your videos into intelligent insights with AI-powered transcription, speaker identification, 
              and interactive analysis. Upload a video or paste a YouTube URL to get started.
            </p>
          </motion.div>

          {/* Upload Area */}
          <motion.div 
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.2 }}
            className="max-w-4xl mx-auto"
          >
            <div className="bg-white rounded-3xl shadow-xl border border-gray-200 overflow-hidden">
              <div className="p-12">
                {/* URL Input */}
                <div className="mb-12">
                  <div className="flex items-center gap-3 mb-4">
                    <Youtube className="text-red-500" size={24} />
                    <h3 className="text-xl font-semibold text-gray-800">YouTube URL</h3>
                  </div>
                  <div className="flex gap-4">
                    <input
                      type="text"
                      value={urlInput}
                      onChange={(e) => setUrlInput(e.target.value)}
                      placeholder="https://youtube.com/watch?v=..."
                      className="flex-1 px-4 py-4 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200"
                    />
                    <motion.button
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      onClick={handleUrlSubmit}
                      disabled={isProcessing || !urlInput.trim()}
                      className="px-8 py-4 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-xl font-medium hover:shadow-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {isProcessing ? 'Processing...' : 'Process URL'}
                    </motion.button>
                  </div>
                </div>

                {/* Divider */}
                <div className="flex items-center gap-4 mb-12">
                  <div className="flex-1 h-px bg-gray-200"></div>
                  <span className="text-gray-500 font-medium">OR</span>
                  <div className="flex-1 h-px bg-gray-200"></div>
                </div>

                {/* File Upload */}
                <div>
                  <div className="flex items-center gap-3 mb-4">
                    <Upload className="text-blue-600" size={24} />
                    <h3 className="text-xl font-semibold text-gray-800">Upload Video File</h3>
                  </div>
                  
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="video/*,audio/*"
                    onChange={(e) => e.target.files?.[0] && handleFileUpload(e.target.files[0])}
                    className="hidden"
                  />
                  
                  <motion.div
                    whileHover={{ scale: 1.01 }}
                    onClick={() => fileInputRef.current?.click()}
                    className="border-2 border-dashed border-gray-300 hover:border-blue-500 rounded-2xl p-12 text-center cursor-pointer transition-all duration-200 bg-gray-50 hover:bg-blue-50"
                  >
                    <div className="p-4 bg-white rounded-full w-20 h-20 mx-auto mb-4 flex items-center justify-center shadow-sm">
                      <Upload size={32} className="text-blue-600" />
                    </div>
                    <h4 className="text-xl font-medium text-gray-800 mb-2">
                      {isUploading ? 'Uploading...' : 'Drop your video here or click to browse'}
                    </h4>
                    <p className="text-gray-600">Supports MP4, AVI, MOV, MP3, WAV and more</p>
                  </motion.div>
                </div>
              </div>
            </div>
          </motion.div>

          {/* Features */}
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="max-w-6xl mx-auto mt-16"
          >
            <div className="grid md:grid-cols-3 gap-8">
              {[
                {
                  icon: <FileText size={24} />,
                  title: "AI Transcription",
                  description: "State-of-the-art Whisper AI provides accurate, word-level transcription with timestamps"
                },
                {
                  icon: <Users size={24} />,
                  title: "Speaker Identification",
                  description: "Advanced diarization identifies and separates different speakers automatically"
                },
                {
                  icon: <MessageSquare size={24} />,
                  title: "Interactive Q&A",
                  description: "Ask questions about your content and get intelligent, context-aware answers"
                }
              ].map((feature, index) => (
                <div key={index} className="bg-white rounded-2xl p-8 shadow-lg border border-gray-200 hover:shadow-xl transition-all duration-200">
                  <div className="p-3 bg-gradient-to-r from-blue-100 to-indigo-100 rounded-xl w-fit mb-4 text-blue-600">
                    {feature.icon}
                  </div>
                  <h3 className="text-xl font-semibold text-gray-800 mb-3">{feature.title}</h3>
                  <p className="text-gray-600 leading-relaxed">{feature.description}</p>
                </div>
              ))}
            </div>
          </motion.div>
        </div>
      </div>
    );
  }

  if (currentView === 'processing') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100 flex items-center justify-center">
        <motion.div 
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className="max-w-2xl mx-auto p-8"
        >
          <div className="bg-white rounded-3xl shadow-2xl border border-gray-200 p-12">
            <div className="text-center mb-12">
              <div className="p-4 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-2xl w-20 h-20 mx-auto mb-6 flex items-center justify-center text-white">
                <Zap size={32} />
              </div>
              <h2 className="text-3xl font-bold text-gray-800 mb-4">Processing Your Content</h2>
              <p className="text-gray-600">Our AI is analyzing your video. This may take a few minutes...</p>
            </div>

            {/* Progress Steps */}
            <div className="space-y-6">
              {[
                'Extracting audio',
                'Transcribing with Whisper',
                'Analyzing speakers',
                'Generating summary',
                'Finalizing results'
              ].map((step, index) => {
                const currentProgress = progress.find(p => p.stage.toLowerCase().includes(step.toLowerCase()));
                const isCompleted = currentProgress?.status === 'completed';
                const isProcessing = currentProgress?.status === 'processing';
                const isError = currentProgress?.status === 'error';

                return (
                  <div key={index} className="flex items-center gap-4 p-4 rounded-xl bg-gray-50">
                    <div className={`p-2 rounded-full ${
                      isCompleted ? 'bg-green-100 text-green-600' :
                      isProcessing ? 'bg-blue-100 text-blue-600' :
                      isError ? 'bg-red-100 text-red-600' :
                      'bg-gray-100 text-gray-400'
                    }`}>
                      {isCompleted ? <CheckCircle size={20} /> :
                       isError ? <AlertCircle size={20} /> :
                       <Clock size={20} />}
                    </div>
                    <div className="flex-1">
                      <div className="text-sm font-medium text-gray-800">{step}</div>
                      {currentProgress && (
                        <div className="text-xs text-gray-600 mt-1">{currentProgress.message}</div>
                      )}
                    </div>
                    {isProcessing && (
                      <div className="w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </motion.div>
      </div>
    );
  }

  if (currentView === 'results' && results) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100">
        <div className="container mx-auto px-6 py-8">
          {/* Header */}
          <div className="flex items-center justify-between mb-8">
            <div>
              <h1 className="text-3xl font-bold text-gray-800">Analysis Complete</h1>
              <p className="text-gray-600 mt-2">Your video has been processed and analyzed</p>
            </div>
            <div className="flex gap-3">
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => handleExport('txt')}
                className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 rounded-lg hover:shadow-md transition-all duration-200"
              >
                <Download size={16} />
                Export TXT
              </motion.button>
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => handleExport('srt')}
                className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 rounded-lg hover:shadow-md transition-all duration-200"
              >
                <Download size={16} />
                Export SRT
              </motion.button>
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => handleExport('zip')}
                className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-lg hover:shadow-lg transition-all duration-200"
              >
                <Download size={16} />
                Download All
              </motion.button>
            </div>
          </div>

          {/* Tabs */}
          <div className="flex gap-2 mb-8 p-1 bg-white rounded-xl shadow-sm">
            {[
              { key: 'transcript', label: 'Transcript', icon: <FileText size={18} /> },
              { key: 'summary', label: 'AI Summary', icon: <Zap size={18} /> },
              { key: 'qa', label: 'Ask Questions', icon: <MessageSquare size={18} /> },
              { key: 'chapters', label: 'Chapters', icon: <Clock size={18} /> }
            ].map((tab) => (
              <motion.button
                key={tab.key}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => setActiveTab(tab.key as any)}
                className={`flex items-center gap-2 px-6 py-3 rounded-lg font-medium transition-all duration-200 ${
                  activeTab === tab.key
                    ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-md'
                    : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                {tab.icon}
                {tab.label}
              </motion.button>
            ))}
          </div>

          {/* Tab Content */}
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2 }}
            className="bg-white rounded-2xl shadow-xl border border-gray-200"
          >
            {activeTab === 'transcript' && (
              <div className="p-8">
                <h2 className="text-2xl font-bold text-gray-800 mb-6">Transcript</h2>
                <div className="space-y-4 max-h-96 overflow-y-auto">
                  {results.transcript.segments?.map((segment: any, index: number) => (
                    <div key={index} className="p-4 bg-gray-50 rounded-xl border-l-4 border-blue-500">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-sm font-mono text-blue-600 bg-blue-100 px-2 py-1 rounded">
                          {formatTimestamp(segment.start)}
                        </span>
                        <span className="text-sm text-gray-500">
                          → {formatTimestamp(segment.end)}
                        </span>
                      </div>
                      <p className="text-gray-800 leading-relaxed">{segment.text}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {activeTab === 'summary' && (
              <div className="p-8">
                <h2 className="text-2xl font-bold text-gray-800 mb-6">AI Summary</h2>
                <div className="prose max-w-none">
                  <div className="bg-gradient-to-r from-blue-50 to-indigo-50 p-6 rounded-xl border border-blue-200">
                    <pre className="whitespace-pre-wrap text-gray-800 font-sans leading-relaxed">
                      {results.summary || 'Summary not available'}
                    </pre>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'qa' && (
              <div className="p-8">
                <h2 className="text-2xl font-bold text-gray-800 mb-6">Ask Questions</h2>
                
                {/* Question Input */}
                <div className="mb-8">
                  <div className="flex gap-4">
                    <input
                      type="text"
                      value={question}
                      onChange={(e) => setQuestion(e.target.value)}
                      placeholder="Ask anything about the video content..."
                      className="flex-1 px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      onKeyPress={(e) => e.key === 'Enter' && handleQuestionSubmit()}
                    />
                    <motion.button
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      onClick={handleQuestionSubmit}
                      disabled={!question.trim()}
                      className="px-6 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-xl font-medium hover:shadow-lg transition-all duration-200 disabled:opacity-50"
                    >
                      Ask
                    </motion.button>
                  </div>
                </div>

                {/* Answer */}
                {qaResponse && (
                  <div className="space-y-6">
                    <div className="bg-gradient-to-r from-green-50 to-blue-50 p-6 rounded-xl border border-green-200">
                      <h3 className="font-semibold text-gray-800 mb-3">Answer:</h3>
                      <p className="text-gray-800 leading-relaxed">{qaResponse.answer}</p>
                    </div>

                    {qaResponse.context.length > 0 && (
                      <div>
                        <h3 className="font-semibold text-gray-800 mb-4">Sources:</h3>
                        <div className="space-y-3">
                          {qaResponse.context.map((ctx, index) => (
                            <div key={index} className="p-4 bg-gray-50 rounded-xl border-l-4 border-blue-500">
                              <div className="flex items-center gap-2 mb-2">
                                {ctx.metadata.speaker && (
                                  <span className="text-xs font-medium text-blue-600 bg-blue-100 px-2 py-1 rounded">
                                    {ctx.metadata.speaker}
                                  </span>
                                )}
                                {ctx.metadata.start_time && (
                                  <span className="text-xs text-gray-500">
                                    {formatTimestamp(ctx.metadata.start_time)}
                                  </span>
                                )}
                              </div>
                              <p className="text-sm text-gray-700">{ctx.content}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {activeTab === 'chapters' && (
              <div className="p-8">
                <h2 className="text-2xl font-bold text-gray-800 mb-6">Chapters</h2>
                {results.chapters && results.chapters.length > 0 ? (
                  <div className="space-y-4">
                    {results.chapters.map((chapter: any, index: number) => (
                      <div key={index} className="p-6 bg-gray-50 rounded-xl border border-gray-200 hover:shadow-md transition-all duration-200">
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <h3 className="text-lg font-semibold text-gray-800 mb-2">{chapter.title}</h3>
                            <p className="text-gray-600 text-sm mb-3">{chapter.description}</p>
                            <div className="flex items-center gap-4 text-sm text-gray-500">
                              <span className="flex items-center gap-1">
                                <Play size={14} />
                                {chapter.start_time}
                              </span>
                              <span>→</span>
                              <span className="flex items-center gap-1">
                                <Pause size={14} />
                                {chapter.end_time}
                              </span>
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center text-gray-500 py-8">
                    <Clock size={48} className="mx-auto mb-4 text-gray-300" />
                    <p>Chapters not available for this video</p>
                  </div>
                )}
              </div>
            )}
          </motion.div>
        </div>
      </div>
    );
  }

  return null;
}

export default App;
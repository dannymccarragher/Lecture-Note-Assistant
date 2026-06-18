import { useEffect, useMemo, useState, useRef } from 'react';

type LectureStatus = 'processing' | 'transcribing' | 'extracting' | 'summarizing' | 'indexing' | 'complete' | 'error';

type LectureData = {
  lecture_id: string;
  status: LectureStatus;
  filename?: string;
  transcript?: string;
  summary?: string;
  key_points?: string[];
  quiz?: { question: string; answer?: string; choices?: string[] }[];
  error?: string;
};

type SearchResult = {
  answer: string;
  sources: Array<{ text: string; start?: number; end?: number }>;
};

const supportedExtensions = ['.mp3', '.mp4', '.wav', '.m4a', '.webm', '.ogg', '.mov', '.avi', '.flac', '.aac', '.mkv', '.mpg', '.mpeg'];
const backendUrl = 'http://127.0.0.1:8000';

export default function App() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [lectureId, setLectureId] = useState<string>('');
  const [lectureData, setLectureData] = useState<LectureData | null>(null);
  const [statusMessage, setStatusMessage] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResult, setSearchResult] = useState<SearchResult | null>(null);
  const [polling, setPolling] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (!polling || !lectureId) return;

    const interval = setInterval(async () => {
      try {
        const response = await fetch(`${backendUrl}/api/status/${lectureId}`);
        if (!response.ok) throw new Error(`Status request failed: ${response.statusText}`);
        const data = await response.json();
        setLectureData({
          lecture_id: lectureId,
          status: data.status,
          filename: data.filename,
          transcript: data.transcript,
          summary: data.summary,
          key_points: data.key_points,
          quiz: data.quiz,
          error: data.error,
        });
        setStatusMessage(data.status === 'complete' ? 'Processing complete.' : `Current status: ${data.status}`);
        if (data.status === 'complete' || data.status === 'error') {
          setPolling(false);
          clearInterval(interval);
        }
      } catch (error) {
        setStatusMessage('Unable to get status.');
        setPolling(false);
        clearInterval(interval);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [polling, lectureId]);

  const validateFile = (file: File | null) => {
    if (!file) return false;
    const ext = file.name.slice(file.name.lastIndexOf('.')).toLowerCase();
    return supportedExtensions.includes(ext);
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setUploadError('');
    setSearchResult(null);
    const file = event.target.files?.[0] ?? null;
    if (file && !validateFile(file)) {
      setSelectedFile(null);
      setUploadError(`Unsupported file type. Supported: ${supportedExtensions.join(', ')}`);
      return;
    }
    setSelectedFile(file);
  };

  const handleUpload = async () => {
    setUploadError('');
    setStatusMessage('');
    setLectureData(null);
    setSearchResult(null);

    if (!selectedFile) {
      setUploadError('Please select a file to upload.');
      return;
    }

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const response = await fetch(`${backendUrl}/api/upload`, {
        method: 'POST',
        body: formData,
      });
      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
        throw new Error(error.detail || 'Upload failed');
      }
      const data = await response.json();
      setLectureId(data.lecture_id);
      setLectureData({ lecture_id: data.lecture_id, status: data.status, filename: selectedFile.name });
      setStatusMessage('Upload received. Processing started.');
      setPolling(true);
    } catch (error) {
      setUploadError((error as Error).message);
    }
  };

  const handleSearch = async () => {
    if (!lectureId || !searchQuery.trim()) return;

    try {
      const response = await fetch(`${backendUrl}/api/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lecture_id: lectureId, query: searchQuery }),
      });
      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Search failed' }));
        throw new Error(error.detail || 'Search failed');
      }
      const data = await response.json();
      setSearchResult({ answer: data.answer, sources: data.sources ?? [] });
    } catch (error) {
      setSearchResult({ answer: `Search failed: ${(error as Error).message}`, sources: [] });
    }
  };

  const transcriptLines = useMemo(() => {
    if (!lectureData?.transcript) return [];
    return lectureData.transcript.split('\n').filter(Boolean);
  }, [lectureData]);

  return (
    <div className="app-shell">
      <header>
        <h1>Lecture Note Assistant</h1>
        <p>Upload lecture audio/video or documents; view transcript, summaries, quizzes, and search content.</p>
      </header>

      <section className="card upload-card">
        <h2>Upload Lecture</h2>
        <div className="upload-controls">
          <input ref={fileInputRef} type="file" accept="audio/*,video/*" onChange={handleFileChange} />
          <button onClick={handleUpload}>Upload &amp; Process</button>
        </div>
        <p className="hint-text">Upload lecture audio or video files. Supported formats: {supportedExtensions.join(', ')}.</p>
        {uploadError && <p className="error-text">{uploadError}</p>}
        {statusMessage && <p className="status-text">{statusMessage}</p>}
        {lectureData?.filename && <p className="meta-text">File: {lectureData.filename}</p>}
      </section>

      {lectureData && (
        <section className="card status-card">
          <h2>Lecture Status</h2>
          <p>Status: <strong>{lectureData.status}</strong></p>
          {lectureData.error && <p className="error-text">Error: {lectureData.error}</p>}
        </section>
      )}

      {lectureData?.status === 'complete' && (
        <>
          <section className="card summary-card">
            <h2>Summary</h2>
            <p>{lectureData.summary ?? 'No summary available.'}</p>
            {lectureData.key_points?.length ? (
              <div>
                <h3>Key Points</h3>
                <ul>
                  {lectureData.key_points.map((point, index) => (
                    <li key={index}>{point}</li>
                  ))}
                </ul>
              </div>
            ) : null}
          </section>

          <section className="card quiz-card">
            <h2>Quiz</h2>
            {lectureData.quiz?.length ? (
              <ol>
                {lectureData.quiz.map((item, index) => (
                  <li key={index} className="quiz-item">
                    <p className="quiz-question">{item.question}</p>
                    {item.choices && (
                      <ul>
                        {item.choices.map((choice) => (
                          <li key={choice}>{choice}</li>
                        ))}
                      </ul>
                    )}
                    {item.answer && (
                      <details>
                        <summary>Show answer</summary>
                        <p>{item.answer}</p>
                      </details>
                    )}
                  </li>
                ))}
              </ol>
            ) : (
              <p>No quiz generated.</p>
            )}
          </section>

          <section className="card search-card">
            <h2>Search Lecture Notes</h2>
            <div className="search-controls">
              <input
                type="text"
                placeholder="Ask a question about the lecture"
                value={searchQuery}
                onChange={(event) => setSearchQuery(event.target.value)}
              />
              <button disabled={lectureData.status !== 'complete'} onClick={handleSearch}>Search</button>
            </div>
            {searchResult && (
              <div className="search-result">
                <h3>Answer</h3>
                <p>{searchResult.answer}</p>
                {/* {searchResult.sources.length > 0 && (
                  <div>
                    <h4>Sources</h4>
                    <ul>
                      {searchResult.sources.map((source, index) => (
                        <li key={index}>{source.text ?? JSON.stringify(source)}</li>
                      ))}
                    </ul>
                  </div>
                )} */}
              </div>
            )}
          </section>

          <section className="card transcript-card">
            <h2>Transcript</h2>
            {transcriptLines.length ? (
              <div className="transcript-pane">
                {transcriptLines.map((line, index) => (
                  <p key={index}>{line}</p>
                ))}
              </div>
            ) : (
              <p>No transcript available.</p>
            )}
          </section>
        </>
      )}
    </div>
  );
}

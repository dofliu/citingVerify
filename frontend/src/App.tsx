import React, { useState, ChangeEvent, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import jsPDF from 'jspdf';
import html2canvas from 'html2canvas';
import './App.css';

// Data structures match the backend schemas
interface Reference {
  raw_text: string;
  status: string;
  authors?: string[];
  year?: number;
  title?: string;
  source?: string;
  verified_doi?: string;
  verification_score: number;
  format_suggestion?: string;
  source_url?: string;
}

interface Summary {
  total_references: number;
  verified_count: number;
  not_found_count: number;
  format_error_count: number;
}

interface PaperMetadata {
  title?: string;
  authors?: string[];
  year?: number;
  affiliation?: string;
}

const App: React.FC = () => {
  const { t, i18n } = useTranslation();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [references, setReferences] = useState<Reference[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [paperMetadata, setPaperMetadata] = useState<PaperMetadata | null>(null);
  const [statusLog, setStatusLog] = useState<string[]>([]);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [error, setError] = useState<string>('');
  const logContainerRef = useRef<HTMLDivElement>(null);
  const reportContentRef = useRef<HTMLDivElement>(null);

  const [selectedModel, setSelectedModel] = useState<string>('gemini-1.5-pro');

  useEffect(() => {
    // Auto-scroll the log container
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [statusLog]);

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    if (event.target.files) {
      setSelectedFile(event.target.files[0]);
      // Reset states for a new file upload
      setReferences([]);
      setSummary(null);
      setPaperMetadata(null);
      setStatusLog([]);
      setError('');
    }
  };

  const handleModelChange = (event: ChangeEvent<HTMLSelectElement>) => {
    setSelectedModel(event.target.value);
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      alert('Please select a file first!');
      return;
    }

    setIsProcessing(true);
    setReferences([]);
    setSummary(null);
    setPaperMetadata(null);
    setStatusLog(['Process started...']);
    setError('');

    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('model_name', selectedModel);

    try {
      const response = await fetch('http://localhost:8000/stream-verify/', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('Failed to get response reader');
      }

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n'); // SSE messages are separated by double newlines
        buffer = lines.pop() || ''; // Keep the last, possibly incomplete message

        for (const line of lines) {
          if (line.startsWith('data:')) {
            const dataString = line.substring(5).trim();
            try {
              const eventData = JSON.parse(dataString);
              const { type, payload } = eventData;

              if (type === 'status') {
                setStatusLog(prev => [...prev, payload.message]);
              } else if (type === 'summary') {
                setSummary(payload);
              } else if (type === 'reference') {
                setReferences(prev => [...prev, payload]);
              } else if (type === 'metadata') {
                setPaperMetadata(payload);
              } else if (type === 'end') {
                setStatusLog(prev => [...prev, payload.message]);
                setIsProcessing(false);
              } else if (type === 'error') {
                setError(payload.message);
                setStatusLog(prev => [...prev, `Error: ${payload.message}`]);
                setIsProcessing(false);
              }
            } catch (e) {
              console.error('Failed to parse SSE data chunk:', dataString);
            }
          }
        }
      }
    } catch (err: any) {
      setError(`A critical error occurred: ${err.message}`);
      setIsProcessing(false);
    }
  };

  const SummaryCard = ({ title, value }: { title: string, value: number | string }) => (
    <div className="summary-card">
      <h4>{title}</h4>
      <p>{value}</p>
    </div>
  );

  const changeLanguage = (lng: string) => {
    i18n.changeLanguage(lng);
  };

  const getRowClass = (score: number): string => {
    if (score >= 95) return 'score-high';
    if (score >= 85) return 'score-medium';
    if (score > 0) return 'score-low';
    return 'score-zero';
  };

  const handleExport = () => {
    const input = reportContentRef.current;
    if (!input) {
      alert('Could not find the report content to export.');
      return;
    }
  
    // Temporarily add a class to the body to override link colors for the screenshot
    document.body.classList.add('pdf-export-active');
  
    html2canvas(input, {
      scale: 2, // Increase scale for better resolution
      useCORS: true,
      onclone: (document: Document) => {
        // You can modify the cloned document here if needed before capture
      }
    }).then((canvas: HTMLCanvasElement) => {
      // Remove the temporary class after the canvas is created
      document.body.classList.remove('pdf-export-active');
  
      const imgData = canvas.toDataURL('image/png');
      const pdf = new jsPDF({
        orientation: 'landscape',
        unit: 'mm',
        format: 'a4'
      });
  
      const pdfWidth = pdf.internal.pageSize.getWidth();
      const pdfHeight = pdf.internal.pageSize.getHeight();
      const canvasWidth = canvas.width;
      const canvasHeight = canvas.height;
      const ratio = canvasWidth / canvasHeight;
      const imgWidth = pdfWidth;
      const imgHeight = imgWidth / ratio;
  
      // Check if the image height exceeds the page height
      if (imgHeight > pdfHeight) {
        // This basic implementation just adds the image and lets it get cut off.
        // For multi-page, a more complex logic is needed to split the canvas.
        console.warn("Report content is too long for a single PDF page.");
      }
  
      pdf.addImage(imgData, 'PNG', 0, 0, imgWidth, imgHeight);
      
      const safeFilename = (selectedFile?.name || 'report').replace('.pdf', '');
      pdf.save(`${safeFilename}_CitingVerify_Report.pdf`);
    }).catch((err: any) => {
      // Make sure to remove the class even if there's an error
      document.body.classList.remove('pdf-export-active');
      console.error("Error exporting to PDF:", err);
      alert("An error occurred while exporting the report to PDF.");
    });
  };

  return (
    <div className="app-container">
      <aside className="sidebar">
        <header className="sidebar-header">
          <h1>{t('app_title')}</h1>
          <p>{t('app_subtitle')}</p>
        </header>
        
        <div className="upload-section">
          <div className="model-selector">
            <label htmlFor="model-select">{t('model_select_label')}</label>
            <select id="model-select" value={selectedModel} onChange={handleModelChange} disabled={isProcessing}>
              <option value="gemini-1.5-pro">Gemini 1.5 Pro</option>
              <option value="gemini-1.5-flash">Gemini 1.5 Flash</option>
              <option value="gemini-2.5-flash">Gemini 2.5 Flash</option>
              <option value="deepseek-chat">DeepSeek Chat</option>
              <option value="deepseek-reasoner">DeepSeek Reasoner</option>
            </select>
          </div>
          <input type="file" id="file-upload" accept=".pdf" onChange={handleFileChange} />
          <label htmlFor="file-upload" className="file-upload-label">
            {selectedFile ? selectedFile.name : t('upload_label')}
          </label>
          <button onClick={handleUpload} disabled={!selectedFile || isProcessing}>
            {isProcessing ? t('upload_button_processing') : t('upload_button_ready')}
          </button>
        </div>

        <div className="status-log-container">
          <h3>{t('log_title')}</h3>
          <div className="status-log" ref={logContainerRef}>
            {statusLog.map((log, index) => (
              <div key={index} className="log-entry">{log}</div>
            ))}
          </div>
        </div>
        <div className="language-switcher">
          <button onClick={() => changeLanguage('en')}>English</button>
          <button onClick={() => changeLanguage('zh')}>中文</button>
        </div>
      </aside>

      <main className="main-content" ref={reportContentRef}>
        {error && <div className="error-message">{error}</div>}
        
        {!summary && !isProcessing && !error && (
          <div className="welcome-message">
            <h2>{t('welcome_title')}</h2>
            <p>{t('welcome_subtitle')}</p>
          </div>
        )}

        {paperMetadata && (
          <div className="paper-metadata-container">
            <h3>{t('paper_info_title')}</h3>
            <h2>{paperMetadata.title || 'Title not found'}</h2>
            <p><strong>{t('paper_info_authors')}:</strong> {paperMetadata.authors?.join(', ') || t('value_na')}</p>
            <p><strong>{t('paper_info_year')}:</strong> {paperMetadata.year || t('value_na')} | <strong>{t('paper_info_affiliation')}:</strong> {paperMetadata.affiliation || t('value_na')}</p>
          </div>
        )}

        {summary && (
          <div className="summary-section">
            <div className="summary-grid">
              <SummaryCard title={t('summary_total')} value={summary.total_references} />
              <SummaryCard title={t('summary_verified')} value={summary.verified_count} />
              <SummaryCard title={t('summary_unverified')} value={summary.not_found_count + summary.format_error_count} />
            </div>
            <button onClick={handleExport} className="export-button" disabled={isProcessing || references.length === 0}>
              {t('export_button')}
            </button>
          </div>
        )}

        <div className="results-table-container">
          <table className="results-table">
            <thead>
              <tr>
                <th style={{width: '12%'}}>{t('table_header_status')}</th>
                <th style={{width: '20%'}}>{t('table_header_authors')}</th>
                <th style={{width: '5%'}}>{t('table_header_year')}</th>
                <th style={{width: '30%'}}>{t('table_header_title')}</th>
                <th style={{width: '18%'}}>{t('table_header_source')}</th>
                <th style={{width: '15%'}}>{t('table_header_suggestion')}</th>
              </tr>
            </thead>
            <tbody>
              {references.map((ref, index) => (
                <tr key={index} className={getRowClass(ref.verification_score)}>
                  <td>
                    <span className="status-text">{ref.status === 'Verified' ? t('status_verified') : `${t('status_unverified_prefix')}${t('status_' + ref.status.replace(/ /g, '_'))}`}</span>
                    <span className="score-badge">{ref.verification_score > 0 ? `${ref.verification_score.toFixed(0)}` : ''}</span>
                  </td>
                  <td>{ref.authors?.join(', ') || t('value_na')}</td>
                  <td>{ref.year || t('value_na')}</td>
                  <td>
                    {ref.title}
                    {ref.verified_doi && (
                      <a href={`https://doi.org/${ref.verified_doi}`} target="_blank" rel="noopener noreferrer" className="link">
                        {t('link_doi')}: {ref.verified_doi}
                      </a>
                    )}
                    {ref.source_url && (
                      <a href={ref.source_url} target="_blank" rel="noopener noreferrer" className="link">
                        {t('link_source')}
                      </a>
                    )}
                  </td>
                  <td>{ref.source || t('value_na')}</td>
                  <td className="suggestion-cell">
                    {ref.status !== 'Verified' ? ref.format_suggestion || t('value_na') : ''}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  );
};

export default App;


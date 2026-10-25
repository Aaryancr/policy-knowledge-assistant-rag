import React, { useState, useEffect, useCallback, useRef } from 'react';
import { listDocuments, deleteDocument } from '../../api/documents';
import { DocumentUpload } from './DocumentUpload';
import { DocumentList } from './DocumentList';
import { ChunksModal } from './ChunksModal';
import { FileTextIcon, CheckCircleIcon, ClockIcon, AlertCircleIcon, RefreshCwIcon } from '../common/Icons';
import { Button } from '../common/Button';

export function AdminDashboard() {
  const [documents, setDocuments] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [selectedDocForChunks, setSelectedDocForChunks] = useState(null);
  const [errorMsg, setErrorMsg] = useState('');
  const pollTimerRef = useRef(null);

  const fetchDocuments = useCallback(async (showRefreshing = false) => {
    if (showRefreshing) {
      setIsRefreshing(true);
    }
    setErrorMsg('');
    try {
      const response = await listDocuments({ limit: 100 });
      const docs = response?.documents || [];
      setDocuments(docs);
      return docs;
    } catch (err) {
      setErrorMsg(err.message || 'Failed to fetch policy documents.');
      return [];
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  // Initial load
  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  // Polling for active background jobs
  useEffect(() => {
    const hasActiveJobs = documents.some(
      (d) => d.status === 'processing' || d.status === 'queued'
    );

    if (hasActiveJobs) {
      // Start 3-second polling interval
      pollTimerRef.current = setInterval(() => {
        fetchDocuments();
      }, 3000);
    } else {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
        pollTimerRef.current = null;
      }
    }

    return () => {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
      }
    };
  }, [documents, fetchDocuments]);

  const handleDelete = async (docId) => {
    await deleteDocument(docId);
    setDocuments((prev) => prev.filter((d) => d.id !== docId));
  };

  const handleUploadSuccess = () => {
    fetchDocuments(true);
  };

  // Derive metrics strictly from actual API data
  const totalCount = documents.length;
  const completedCount = documents.filter((d) => d.status === 'completed').length;
  const processingCount = documents.filter((d) => d.status === 'processing' || d.status === 'queued').length;
  const failedCount = documents.filter((d) => d.status === 'failed').length;

  return (
    <div className="admin-dashboard-container">
      {/* Page Header */}
      <div className="dashboard-page-header">
        <div>
          <h1 className="page-title">Knowledge Administration</h1>
          <p className="page-subtitle">
            Upload, inspect, and manage enterprise policy documents and vector ingestion jobs.
          </p>
        </div>
        <div className="page-actions">
          <Button
            variant="outline"
            size="md"
            onClick={() => fetchDocuments(true)}
            isLoading={isRefreshing}
            icon={<RefreshCwIcon size={14} />}
          >
            Refresh Data
          </Button>
        </div>
      </div>

      {errorMsg && (
        <div className="alert alert-danger" role="alert" style={{ marginBottom: '1.5rem' }}>
          <AlertCircleIcon size={16} className="alert-icon" />
          <span className="alert-text">{errorMsg}</span>
        </div>
      )}

      {/* Metrics Row */}
      <div className="metrics-grid">
        <div className="metric-card">
          <div className="metric-icon metric-icon-primary">
            <FileTextIcon size={20} />
          </div>
          <div className="metric-content">
            <span className="metric-label">Total Documents</span>
            <span className="metric-value">{totalCount}</span>
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-icon metric-icon-success">
            <CheckCircleIcon size={20} />
          </div>
          <div className="metric-content">
            <span className="metric-label">Completed & Indexed</span>
            <span className="metric-value">{completedCount}</span>
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-icon metric-icon-warning">
            <ClockIcon size={20} className={processingCount > 0 ? 'spin' : ''} />
          </div>
          <div className="metric-content">
            <span className="metric-label">In Processing / Queue</span>
            <span className="metric-value">{processingCount}</span>
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-icon metric-icon-danger">
            <AlertCircleIcon size={20} />
          </div>
          <div className="metric-content">
            <span className="metric-label">Failed Ingestions</span>
            <span className="metric-value">{failedCount}</span>
          </div>
        </div>
      </div>

      {/* Upload Section */}
      <DocumentUpload onUploadSuccess={handleUploadSuccess} />

      {/* Document List Section */}
      <DocumentList
        documents={documents}
        isLoading={isLoading}
        onDeleteDocument={handleDelete}
        onSelectChunks={(doc) => setSelectedDocForChunks(doc)}
      />

      {/* Chunks Inspection Modal */}
      <ChunksModal
        document={selectedDocForChunks}
        isOpen={Boolean(selectedDocForChunks)}
        onClose={() => setSelectedDocForChunks(null)}
      />
    </div>
  );
}

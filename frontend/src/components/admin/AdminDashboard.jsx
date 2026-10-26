import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  listDocuments,
  deleteDocument,
  parseDocumentListResponse,
  calculateDocumentStats,
} from '../../api/documents';
import { DocumentUpload } from './DocumentUpload';
import { DocumentList } from './DocumentList';
import { ChunksModal } from './ChunksModal';
import { FileTextIcon, CheckCircleIcon, ClockIcon, AlertCircleIcon, RefreshCwIcon } from '../common/Icons';
import { Button } from '../common/Button';

export function AdminDashboard() {
  const [documents, setDocuments] = useState([]);
  const [serverTotal, setServerTotal] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [selectedDocForChunks, setSelectedDocForChunks] = useState(null);
  const [errorMsg, setErrorMsg] = useState('');
  const pollTimerRef = useRef(null);
  const isFetchingRef = useRef(false);

  const fetchDocuments = useCallback(async (showRefreshing = false) => {
    if (isFetchingRef.current) {
      return;
    }
    isFetchingRef.current = true;
    if (showRefreshing) {
      setIsRefreshing(true);
    }
    setErrorMsg('');
    try {
      const response = await listDocuments({ limit: 100 });
      const { items, total } = parseDocumentListResponse(response);
      setDocuments(items);
      setServerTotal(total);
      return items;
    } catch (err) {
      const message = err.message || 'Failed to fetch policy documents.';
      setErrorMsg(message);
      return null;
    } finally {
      isFetchingRef.current = false;
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
      (d) => d.status === 'processing' || d.status === 'queued' || d.status === 'pending'
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
    setServerTotal((prev) => (prev !== null && prev > 0 ? prev - 1 : 0));
  };

  const handleUploadSuccess = () => {
    fetchDocuments(true);
  };

  // Derive metrics strictly from actual API data
  const stats = calculateDocumentStats(documents, serverTotal);
  const totalCount = stats.total;
  const completedCount = stats.completed;
  const processingCount = stats.processing;
  const failedCount = stats.failed;

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
        error={errorMsg}
        onRetry={() => fetchDocuments(true)}
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

import React, { useState } from 'react';
import { StatusBadge } from '../common/Badge';
import { Button } from '../common/Button';
import { FileTextIcon, TrashIcon, LayersIcon, AlertCircleIcon, RefreshCwIcon } from '../common/Icons';
import { Modal } from '../common/Modal';

function formatFileSize(bytes) {
  if (!bytes || bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
}

function formatDate(dateStr) {
  if (!dateStr) return 'N/A';
  try {
    const d = new Date(dateStr);
    return d.toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return dateStr;
  }
}

export function DocumentList({
  documents = [],
  isLoading = false,
  error = null,
  onRetry = null,
  onDeleteDocument,
  onSelectChunks,
}) {
  const [docToDelete, setDocToDelete] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const confirmDelete = async () => {
    if (!docToDelete) return;
    setIsDeleting(true);
    try {
      await onDeleteDocument(docToDelete.id);
      setDocToDelete(null);
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div className="card document-list-card">
      <div className="card-header">
        <div>
          <h2 className="card-title">Policy Documents</h2>
          <p className="card-subtitle">
            {error && documents.length === 0
              ? 'Unable to retrieve knowledge base records.'
              : `${documents.length} ${documents.length === 1 ? 'document' : 'documents'} registered in the knowledge base.`}
          </p>
        </div>
      </div>

      {isLoading && documents.length === 0 ? (
        <div className="table-loading-skeleton">
          <div className="skeleton-row" />
          <div className="skeleton-row" />
          <div className="skeleton-row" />
        </div>
      ) : error && documents.length === 0 ? (
        <div className="empty-table-state error-table-state">
          <AlertCircleIcon size={40} className="text-danger" />
          <p className="empty-title">Failed to load policy documents</p>
          <p className="empty-desc">{error}</p>
          {onRetry && (
            <Button
              variant="outline"
              size="sm"
              onClick={onRetry}
              style={{ marginTop: '0.75rem' }}
              icon={<RefreshCwIcon size={14} />}
            >
              Retry
            </Button>
          )}
        </div>
      ) : documents.length === 0 ? (
        <div className="empty-table-state">
          <FileTextIcon size={40} className="text-muted" />
          <p className="empty-title">No policy documents found</p>
          <p className="empty-desc">
            Upload your first HR, IT, or leave policy document above to start indexing.
          </p>
        </div>
      ) : (
        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th>Document Name</th>
                <th>Format</th>
                <th>File Size</th>
                <th>Status</th>
                <th>Chunks</th>
                <th>Uploaded At</th>
                <th className="text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((doc) => {
                const ext = doc.filename.split('.').pop()?.toUpperCase() || 'FILE';
                const isProcessing = doc.status === 'processing' || doc.status === 'queued';

                return (
                  <tr key={doc.id} className={isProcessing ? 'row-processing' : ''}>
                    {/* Document Title & File Info */}
                    <td className="doc-main-cell">
                      <div className="doc-title-row">
                        <span className="doc-title">{doc.title}</span>
                      </div>
                      <div className="doc-filename-row">
                        <span className="doc-filename">{doc.filename}</span>
                        {doc.error_message && (
                          <span className="doc-error-inline" title={doc.error_message}>
                            <AlertCircleIcon size={12} />
                            <span>{doc.error_message}</span>
                          </span>
                        )}
                      </div>
                    </td>

                    {/* Format */}
                    <td>
                      <span className="badge-format">{ext}</span>
                    </td>

                    {/* File Size */}
                    <td className="text-secondary">{formatFileSize(doc.file_size_bytes)}</td>

                    {/* Status Badge */}
                    <td>
                      <StatusBadge status={doc.status} />
                    </td>

                    {/* Total Chunks */}
                    <td>
                      <span className="chunks-count-pill">
                        {doc.total_chunks || 0}
                      </span>
                    </td>

                    {/* Uploaded Date */}
                    <td className="text-secondary text-sm">
                      {formatDate(doc.created_at)}
                    </td>

                    {/* Action Buttons */}
                    <td className="text-right actions-cell">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => onSelectChunks(doc)}
                        title="Inspect extracted chunks"
                        icon={<LayersIcon size={14} />}
                      >
                        Chunks
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setDocToDelete(doc)}
                        className="btn-delete"
                        title="Delete document and chunks"
                        icon={<TrashIcon size={14} />}
                      >
                        Delete
                      </Button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={Boolean(docToDelete)}
        onClose={() => setDocToDelete(null)}
        title="Confirm Document Deletion"
        subtitle="This action cannot be undone."
        maxWidth="460px"
      >
        <div className="delete-modal-content">
          <p className="delete-warning-text">
            Are you sure you want to delete{' '}
            <strong>"{docToDelete?.title || docToDelete?.filename}"</strong>?
          </p>
          <p className="delete-consequences-text">
            This will permanently remove the source document file, all associated vector embeddings from PostgreSQL, and cancel any pending background tasks.
          </p>
          <div className="modal-footer-actions">
            <Button
              variant="danger"
              size="md"
              isLoading={isDeleting}
              onClick={confirmDelete}
              icon={<TrashIcon size={16} />}
            >
              Permanently Delete
            </Button>
            <Button
              variant="ghost"
              size="md"
              onClick={() => setDocToDelete(null)}
              disabled={isDeleting}
            >
              Cancel
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}

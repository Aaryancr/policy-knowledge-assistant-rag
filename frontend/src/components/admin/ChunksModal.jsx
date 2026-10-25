import React, { useState, useEffect } from 'react';
import { getDocumentChunks } from '../../api/documents';
import { Modal } from '../common/Modal';
import { LayersIcon, CheckCircleIcon, ClockIcon, AlertCircleIcon } from '../common/Icons';

export function ChunksModal({ document, isOpen, onClose }) {
  const [chunks, setChunks] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    if (!isOpen || !document?.id) {
      setChunks([]);
      setErrorMsg('');
      return;
    }

    let isMounted = true;
    async function fetchChunks() {
      setIsLoading(true);
      setErrorMsg('');
      try {
        const data = await getDocumentChunks(document.id);
        if (isMounted) {
          setChunks(Array.isArray(data) ? data : []);
        }
      } catch (err) {
        if (isMounted) {
          setErrorMsg(err.message || 'Failed to load document chunks.');
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    fetchChunks();
    return () => {
      isMounted = false;
    };
  }, [isOpen, document?.id]);

  if (!document) return null;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Document Chunks: ${document.title}`}
      subtitle={`Source file: ${document.filename} • ${chunks.length} total indexed chunks`}
      maxWidth="780px"
    >
      <div className="chunks-modal-content">
        {errorMsg && (
          <div className="alert alert-danger" role="alert">
            <AlertCircleIcon size={16} className="alert-icon" />
            <span className="alert-text">{errorMsg}</span>
          </div>
        )}

        {isLoading ? (
          <div className="chunks-loading-state">
            <div className="skeleton-line" style={{ width: '60%', height: '1.25rem' }} />
            <div className="skeleton-card" />
            <div className="skeleton-card" />
            <div className="skeleton-card" />
          </div>
        ) : chunks.length === 0 ? (
          <div className="chunks-empty-state">
            <LayersIcon size={36} className="text-muted" />
            <p className="empty-title">No chunks available yet</p>
            <p className="empty-desc">
              {document.status === 'completed'
                ? 'This document produced 0 indexed chunks.'
                : `Document is currently in "${document.status}" state. Chunks will appear once ingestion completes.`}
            </p>
          </div>
        ) : (
          <div className="chunks-list">
            {chunks.map((c) => (
              <div key={c.id || c.chunk_index} className="chunk-card">
                <div className="chunk-header">
                  <div className="chunk-badges">
                    <span className="badge badge-default badge-sm">
                      Chunk #{c.chunk_index + 1}
                    </span>
                    {c.page_number !== null && c.page_number !== undefined && (
                      <span className="badge badge-default badge-sm">
                        Page {c.page_number}
                      </span>
                    )}
                    {c.section_title && (
                      <span className="badge badge-default badge-sm chunk-section-badge">
                        {c.section_title}
                      </span>
                    )}
                  </div>

                  <div className="chunk-vector-status">
                    {c.has_embedding ? (
                      <span className="badge badge-completed badge-sm" title="Vector(1536) embedded in pgvector">
                        <CheckCircleIcon size={11} />
                        <span>Embedded</span>
                      </span>
                    ) : (
                      <span className="badge badge-queued badge-sm" title="Embedding pending">
                        <ClockIcon size={11} />
                        <span>Vector Pending</span>
                      </span>
                    )}
                  </div>
                </div>

                <div className="chunk-body">
                  <p className="chunk-text">{c.content}</p>
                </div>

                <div className="chunk-footer">
                  <span className="chunk-length-meta">
                    {c.content.length} characters • ~{Math.round(c.content.length / 4)} tokens
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </Modal>
  );
}

import React, { useState } from 'react';
import { FileTextIcon, ChevronDownIcon, ChevronUpIcon } from '../common/Icons';

export function CitationCard({ citation, index }) {
  const [isExpanded, setIsExpanded] = useState(false);

  const {
    document_title,
    document_filename,
    page_number,
    section_title,
    snippet,
    chunk_id,
  } = citation;

  const shortChunkId = chunk_id ? String(chunk_id).slice(0, 8) : '';

  return (
    <div className={`citation-card ${isExpanded ? 'citation-expanded' : ''}`}>
      <div
        className="citation-header"
        onClick={() => setIsExpanded((prev) => !prev)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            setIsExpanded((prev) => !prev);
          }
        }}
      >
        <div className="citation-header-left">
          <span className="citation-index-badge">[{index + 1}]</span>
          <FileTextIcon size={14} className="citation-doc-icon text-primary" />
          <div className="citation-title-group">
            <span className="citation-doc-title">{document_title || document_filename}</span>
            <span className="citation-doc-filename">({document_filename})</span>
          </div>
        </div>

        <div className="citation-header-right">
          {page_number !== null && page_number !== undefined && (
            <span className="badge badge-default badge-sm">Page {page_number}</span>
          )}
          {section_title && (
            <span className="badge badge-default badge-sm citation-section-badge">
              {section_title}
            </span>
          )}
          <span className="citation-toggle-icon">
            {isExpanded ? <ChevronUpIcon size={14} /> : <ChevronDownIcon size={14} />}
          </span>
        </div>
      </div>

      {/* Snippet Content */}
      <div className={`citation-snippet-container ${isExpanded ? 'snippet-visible' : 'snippet-preview'}`}>
        <p className="citation-snippet-text">
          "{snippet}"
        </p>
        {shortChunkId && (
          <div className="citation-provenance-meta">
            <span>Verified Source Chunk: <code>chunk-{shortChunkId}</code></span>
          </div>
        )}
      </div>
    </div>
  );
}

import React, { useState, useRef } from 'react';
import { uploadDocument } from '../../api/documents';
import { UploadCloudIcon, FileTextIcon, AlertCircleIcon, CheckCircleIcon, XIcon } from '../common/Icons';
import { Button } from '../common/Button';

const MAX_SIZE_BYTES = 15 * 1024 * 1024; // 15 MB
const ALLOWED_EXTENSIONS = ['.pdf', '.docx', '.txt'];

export function DocumentUpload({ onUploadSuccess }) {
  const [selectedFile, setSelectedFile] = useState(null);
  const [customTitle, setCustomTitle] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const fileInputRef = useRef(null);

  const validateFile = (file) => {
    if (!file) return false;
    const name = file.name.toLowerCase();
    const hasValidExt = ALLOWED_EXTENSIONS.some((ext) => name.endsWith(ext));

    if (!hasValidExt) {
      setErrorMsg(`Unsupported file type. Only PDF, DOCX, and TXT files are allowed.`);
      return false;
    }

    if (file.size === 0) {
      setErrorMsg('The selected file is empty (0 bytes).');
      return false;
    }

    if (file.size > MAX_SIZE_BYTES) {
      setErrorMsg(`File exceeds maximum size limit of 15 MB (${(file.size / (1024 * 1024)).toFixed(1)} MB).`);
      return false;
    }

    return true;
  };

  const handleFileSelect = (file) => {
    setErrorMsg('');
    setSuccessMsg('');
    if (validateFile(file)) {
      setSelectedFile(file);
      if (!customTitle) {
        // Auto-derive clean title without extension
        const rawName = file.name.replace(/\.[^/.]+$/, '').replace(/[-_]/g, ' ');
        setCustomTitle(rawName.charAt(0).toUpperCase() + rawName.slice(1));
      }
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!selectedFile) {
      setErrorMsg('Please select a policy document to upload.');
      return;
    }

    setIsUploading(true);
    setErrorMsg('');
    setSuccessMsg('');

    try {
      const response = await uploadDocument(selectedFile, customTitle);
      setSuccessMsg(`Document "${response.title}" uploaded successfully. Ingestion job enqueued.`);
      setSelectedFile(null);
      setCustomTitle('');
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      if (typeof onUploadSuccess === 'function') {
        onUploadSuccess(response);
      }
    } catch (err) {
      setErrorMsg(err.message || 'Failed to upload document. Please try again.');
    } finally {
      setIsUploading(false);
    }
  };

  const clearSelection = () => {
    setSelectedFile(null);
    setCustomTitle('');
    setErrorMsg('');
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="card upload-card">
      <div className="card-header">
        <div>
          <h2 className="card-title">Upload Policy Document</h2>
          <p className="card-subtitle">
            Upload enterprise PDF, DOCX, or TXT policies for background ingestion and vector embedding.
          </p>
        </div>
      </div>

      {errorMsg && (
        <div className="alert alert-danger" role="alert">
          <AlertCircleIcon size={16} className="alert-icon" />
          <span className="alert-text">{errorMsg}</span>
        </div>
      )}

      {successMsg && (
        <div className="alert alert-success" role="alert">
          <CheckCircleIcon size={16} className="alert-icon" />
          <span className="alert-text">{successMsg}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="upload-form">
        {/* Drop Zone */}
        <div
          className={`dropzone ${isDragging ? 'dropzone-active' : ''} ${selectedFile ? 'dropzone-has-file' : ''}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => !selectedFile && fileInputRef.current?.click()}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              fileInputRef.current?.click();
            }
          }}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.docx,.txt"
            style={{ display: 'none' }}
            onChange={(e) => e.target.files?.[0] && handleFileSelect(e.target.files[0])}
            disabled={isUploading}
          />

          {selectedFile ? (
            <div className="selected-file-preview">
              <div className="file-icon-box">
                <FileTextIcon size={24} className="text-primary" />
              </div>
              <div className="file-meta">
                <span className="file-name">{selectedFile.name}</span>
                <span className="file-size">
                  {(selectedFile.size / 1024).toFixed(1)} KB
                </span>
              </div>
              <button
                type="button"
                className="btn-remove-file"
                onClick={(e) => {
                  e.stopPropagation();
                  clearSelection();
                }}
                disabled={isUploading}
                aria-label="Remove selected file"
              >
                <XIcon size={16} />
              </button>
            </div>
          ) : (
            <div className="dropzone-empty-content">
              <div className="dropzone-icon">
                <UploadCloudIcon size={32} />
              </div>
              <p className="dropzone-text">
                <span className="dropzone-link">Click to browse</span> or drag and drop your document here
              </p>
              <p className="dropzone-hints">
                Supported formats: PDF, Word (DOCX), Text (TXT) • Max size: 15 MB
              </p>
            </div>
          )}
        </div>

        {/* Optional Document Title Field */}
        {selectedFile && (
          <div className="form-group" style={{ marginTop: '1rem' }}>
            <label htmlFor="doc-title-input" className="form-label">
              Document Title <span className="label-optional">(Optional)</span>
            </label>
            <input
              id="doc-title-input"
              type="text"
              placeholder="e.g. Remote Work and Flexibility Policy"
              value={customTitle}
              onChange={(e) => setCustomTitle(e.target.value)}
              className="form-input"
              disabled={isUploading}
            />
          </div>
        )}

        {/* Upload Action Button */}
        {selectedFile && (
          <div className="upload-actions" style={{ marginTop: '1rem' }}>
            <Button
              type="submit"
              variant="primary"
              size="md"
              isLoading={isUploading}
              icon={<UploadCloudIcon size={16} />}
            >
              Start Ingestion Pipeline
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="md"
              onClick={clearSelection}
              disabled={isUploading}
            >
              Cancel
            </Button>
          </div>
        )}
      </form>
    </div>
  );
}

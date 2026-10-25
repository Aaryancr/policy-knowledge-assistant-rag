import React, { useState, useEffect } from 'react';
import { listChatLogs } from '../../api/chat';
import { Modal } from '../common/Modal';
import { ClockIcon, SparklesIcon, AlertTriangleIcon, CheckCircleIcon, RefreshCwIcon } from '../common/Icons';
import { Button } from '../common/Button';

function formatDate(dateStr) {
  if (!dateStr) return '';
  try {
    const d = new Date(dateStr);
    return d.toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return dateStr;
  }
}

export function ChatHistoryDrawer({ isOpen, onClose, onSelectPastQuery }) {
  const [logs, setLogs] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const fetchLogs = async () => {
    setIsLoading(true);
    setErrorMsg('');
    try {
      const data = await listChatLogs({ limit: 50 });
      setLogs(Array.isArray(data) ? data : []);
    } catch (err) {
      setErrorMsg(err.message || 'Failed to retrieve query audit history.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchLogs();
    }
  }, [isOpen]);

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Recent Query Audit History"
      subtitle="Inspect previous policy queries, grounded responses, and verified retrieval logs."
      maxWidth="680px"
    >
      <div className="history-modal-content">
        <div className="history-toolbar">
          <span className="text-secondary text-sm">
            {logs.length} previous {logs.length === 1 ? 'query' : 'queries'} recorded
          </span>
          <Button
            variant="ghost"
            size="sm"
            onClick={fetchLogs}
            isLoading={isLoading}
            icon={<RefreshCwIcon size={13} />}
          >
            Refresh
          </Button>
        </div>

        {errorMsg && (
          <div className="alert alert-danger" role="alert">
            <span className="alert-text">{errorMsg}</span>
          </div>
        )}

        {isLoading && logs.length === 0 ? (
          <div className="history-loading-skeleton">
            <div className="skeleton-card" />
            <div className="skeleton-card" />
          </div>
        ) : logs.length === 0 ? (
          <div className="history-empty-state">
            <ClockIcon size={32} className="text-muted" />
            <p className="empty-title">No previous questions logged</p>
            <p className="empty-desc">Your policy queries will appear here after asking.</p>
          </div>
        ) : (
          <div className="history-list">
            {logs.map((log) => {
              const isAbstention = log.is_unanswerable;
              return (
                <div
                  key={log.id}
                  className="history-item-card"
                  onClick={() => {
                    if (typeof onSelectPastQuery === 'function') {
                      onSelectPastQuery(log);
                      onClose();
                    }
                  }}
                  role="button"
                  tabIndex={0}
                >
                  <div className="history-item-header">
                    <span className="history-query-text">{log.query}</span>
                    <span className="history-date text-muted text-xs">
                      {formatDate(log.created_at)}
                    </span>
                  </div>

                  <p className="history-answer-preview">
                    {log.answer.length > 140 ? `${log.answer.slice(0, 137)}...` : log.answer}
                  </p>

                  <div className="history-item-footer">
                    <span className="history-meta-pill">
                      {isAbstention ? (
                        <span className="text-warning flex-row-inline">
                          <AlertTriangleIcon size={12} />
                          <span>Abstained (No Evidence)</span>
                        </span>
                      ) : (
                        <span className="text-success flex-row-inline">
                          <CheckCircleIcon size={12} />
                          <span>Grounded Answer</span>
                        </span>
                      )}
                    </span>

                    {typeof log.latency_ms === 'number' && (
                      <span className="history-latency-text text-muted text-xs">
                        {log.latency_ms} ms
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </Modal>
  );
}

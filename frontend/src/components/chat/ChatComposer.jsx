import React, { useRef, useEffect } from 'react';
import { SendIcon, RefreshCwIcon } from '../common/Icons';

const MAX_QUESTION_CHARS = 1000;

export function ChatComposer({ value, onChange, onSend, isLoading }) {
  const textareaRef = useRef(null);

  // Auto-resize textarea height as user types
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`;
    }
  }, [value]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (value.trim() && !isLoading) {
        onSend();
      }
    }
  };

  const isOverLimit = value.length > MAX_QUESTION_CHARS;
  const canSubmit = value.trim().length > 0 && !isOverLimit && !isLoading;

  return (
    <div className="chat-composer-container">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (canSubmit) onSend();
        }}
        className="chat-composer-form"
      >
        <div className="composer-textarea-wrapper">
          <textarea
            ref={textareaRef}
            rows={1}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a policy question (e.g. PTO carryover rules, travel per diem, password requirements)..."
            disabled={isLoading}
            className={`composer-textarea ${isOverLimit ? 'input-error' : ''}`}
            aria-label="Policy query input"
          />

          <div className="composer-bottom-bar">
            <span
              className={`char-counter ${isOverLimit ? 'text-danger' : value.length > 900 ? 'text-warning' : 'text-muted'}`}
            >
              {value.length} / {MAX_QUESTION_CHARS}
            </span>

            <button
              type="submit"
              disabled={!canSubmit}
              className={`composer-send-btn ${canSubmit ? 'btn-active' : ''}`}
              title={canSubmit ? 'Send question (Enter)' : 'Type a question to send'}
              aria-label="Send message"
            >
              {isLoading ? (
                <RefreshCwIcon size={16} className="spin" />
              ) : (
                <SendIcon size={16} />
              )}
            </button>
          </div>
        </div>
      </form>
      <div className="composer-hints">
        <span>Press <strong>Enter</strong> to send, <strong>Shift + Enter</strong> for a new line</span>
      </div>
    </div>
  );
}

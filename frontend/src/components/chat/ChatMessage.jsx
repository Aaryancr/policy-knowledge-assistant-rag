import React from 'react';
import { CitationCard } from './CitationCard';
import { SparklesIcon, UserIcon, AlertTriangleIcon, LayersIcon, ClockIcon } from '../common/Icons';

/**
 * Parses simple markdown paragraphs, bullet points, and inline bold text safely
 * without requiring external heavy markdown parser dependencies or dangerouslySetInnerHTML.
 */
function FormattedText({ text }) {
  if (!text) return null;

  // Clean out raw [Chunk <uuid>] artifacts if left in the model response
  const cleaned = text.replace(/\[(?:Chunk\s*|chunk:\s*)?[a-f0-9-]{36}\]/gi, '').trim();

  // Split into paragraphs by double line break
  const paragraphs = cleaned.split(/\n\n+/);

  return (
    <div className="formatted-text">
      {paragraphs.map((p, pIdx) => {
        const trimmed = p.trim();
        if (!trimmed) return null;

        // Check if paragraph is a bullet list (lines starting with - or * or numbered 1.)
        const lines = trimmed.split('\n');
        const isBulletList = lines.every((l) => /^[-*•]\s+/.test(l.trim()));
        const isNumberedList = lines.every((l) => /^\d+\.\s+/.test(l.trim()));

        if (isBulletList) {
          return (
            <ul key={pIdx} className="message-list message-ul">
              {lines.map((l, lIdx) => (
                <li key={lIdx}>
                  <InlineFormatting line={l.replace(/^[-*•]\s+/, '')} />
                </li>
              ))}
            </ul>
          );
        }

        if (isNumberedList) {
          return (
            <ol key={pIdx} className="message-list message-ol">
              {lines.map((l, lIdx) => (
                <li key={lIdx}>
                  <InlineFormatting line={l.replace(/^\d+\.\s+/, '')} />
                </li>
              ))}
            </ol>
          );
        }

        // Standard paragraph
        return (
          <p key={pIdx} className="message-paragraph">
            <InlineFormatting line={trimmed} />
          </p>
        );
      })}
    </div>
  );
}

function InlineFormatting({ line }) {
  // Support **bold** syntax safely
  const parts = line.split(/(\*\*[^*]+\*\*)/g);
  return (
    <>
      {parts.map((part, i) => {
        if (part.startsWith('**') && part.endsWith('**')) {
          return <strong key={i}>{part.slice(2, -2)}</strong>;
        }
        return part;
      })}
    </>
  );
}

export function ChatMessage({ message }) {
  const isUser = message.sender === 'user';
  const isAbstention =
    message.is_unanswerable ||
    (message.text && message.text.includes("I don't know based on the provided documents."));

  return (
    <div className={`chat-message-row ${isUser ? 'message-user' : 'message-assistant'}`}>
      <div className="message-avatar">
        {isUser ? <UserIcon size={18} /> : <SparklesIcon size={18} />}
      </div>

      <div className="message-bubble-wrapper">
        <div className="message-bubble">
          {/* User Message */}
          {isUser ? (
            <p className="user-query-text">{message.text}</p>
          ) : isAbstention ? (
            /* Explicit Abstention State */
            <div className="abstention-alert-box">
              <div className="abstention-header">
                <AlertTriangleIcon size={18} className="abstention-icon text-warning" />
                <span className="abstention-title">Insufficient Evidence in Knowledge Base</span>
              </div>
              <p className="abstention-message">
                "I don't know based on the provided documents."
              </p>
              <p className="abstention-explanation">
                The uploaded corporate policies do not contain sufficient evidence or verified clauses to answer this question accurately. No speculative inferences were generated.
              </p>
            </div>
          ) : (
            /* Grounded Answer */
            <FormattedText text={message.text} />
          )}

          {/* Citations Section */}
          {!isUser && !isAbstention && message.citations && message.citations.length > 0 && (
            <div className="message-citations-section">
              <div className="citations-header">
                <LayersIcon size={13} className="text-primary" />
                <span className="citations-label">
                  Supporting Policy Citations ({message.citations.length})
                </span>
              </div>
              <div className="citations-list">
                {message.citations.map((c, idx) => (
                  <CitationCard key={c.chunk_id || idx} citation={c} index={idx} />
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Assistant Metadata Footer (Latency & Similarity) */}
        {!isUser && (message.latency_ms || message.confidence_score) && (
          <div className="message-meta-footer">
            {typeof message.latency_ms === 'number' && (
              <span className="meta-item">
                <ClockIcon size={11} />
                <span>{message.latency_ms} ms</span>
              </span>
            )}
            {typeof message.confidence_score === 'number' && (
              <span
                className="meta-item meta-item-similarity"
                title="Top passage cosine similarity score (not a calibrated probability of factual correctness)"
              >
                <span>Similarity: {Math.round(message.confidence_score * 100)}%</span>
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

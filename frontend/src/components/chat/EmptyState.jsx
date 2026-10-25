import React from 'react';
import { SparklesIcon, BookOpenIcon, ChevronRightIcon } from '../common/Icons';

const SUGGESTIONS = [
  {
    title: 'PTO Accrual & Rollover',
    question: 'How many days of paid time off do full-time employees accrue per year?',
  },
  {
    title: 'Remote Work Stipend',
    question: 'What is the one-time home office equipment stipend for remote workers?',
  },
  {
    title: 'Password Security Rules',
    question: 'What is the minimum password length required for corporate accounts?',
  },
  {
    title: 'Business Travel Per Diem',
    question: 'How much is the domestic daily meal per diem allowance?',
  },
  {
    title: 'Test Abstention Behavior',
    question: 'What is the company subsidy for pet insurance?',
  },
];

export function EmptyState({ onSelectSuggestion }) {
  return (
    <div className="chat-empty-state">
      <div className="empty-state-badge">
        <SparklesIcon size={14} className="text-primary" />
        <span>Grounded Knowledge Retrieval</span>
      </div>

      <h2 className="empty-state-title">How can I assist you today?</h2>
      <p className="empty-state-description">
        Ask any question about company HR benefits, leave allowances, IT security guidelines, or corporate travel policies. Answers are strictly grounded in uploaded documentation with verified citations.
      </p>

      <div className="suggestions-container">
        <p className="suggestions-label">
          <BookOpenIcon size={14} />
          <span>Suggested Policy Questions</span>
        </p>

        <div className="suggestions-grid">
          {SUGGESTIONS.map((s, idx) => (
            <button
              key={idx}
              type="button"
              className="suggestion-card"
              onClick={() => onSelectSuggestion(s.question)}
            >
              <div className="suggestion-content">
                <span className="suggestion-title">{s.title}</span>
                <span className="suggestion-question">{s.question}</span>
              </div>
              <ChevronRightIcon size={16} className="suggestion-arrow" />
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

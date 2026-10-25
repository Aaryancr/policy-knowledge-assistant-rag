import React, { useState, useRef, useEffect } from 'react';
import { queryChat } from '../../api/chat';
import { ChatMessage } from './ChatMessage';
import { ChatComposer } from './ChatComposer';
import { EmptyState } from './EmptyState';
import { ChatHistoryDrawer } from './ChatHistoryDrawer';
import { Button } from '../common/Button';
import { SparklesIcon, RefreshCwIcon, ClockIcon, AlertCircleIcon } from '../common/Icons';

export function ChatInterface() {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [chatError, setChatError] = useState('');
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [lastQuery, setLastQuery] = useState('');

  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleSendQuery = async (queryText) => {
    const textToSend = (queryText || inputValue).trim();
    if (!textToSend || isLoading) return;

    setChatError('');
    setLastQuery(textToSend);
    setInputValue('');

    // Append user message
    const userMsg = {
      id: `user-${Date.now()}`,
      sender: 'user',
      text: textToSend,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    try {
      const response = await queryChat({ question: textToSend });

      const assistantMsg = {
        id: response.chat_log_id || `asst-${Date.now()}`,
        sender: 'assistant',
        text: response.answer,
        citations: response.citations || [],
        is_unanswerable: response.is_unanswerable,
        confidence_score: response.confidence_score,
        latency_ms: response.latency_ms,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      setChatError(err.message || 'Failed to generate answer. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleNewConversation = () => {
    setMessages([]);
    setInputValue('');
    setChatError('');
  };

  const handleSelectPastQuery = (log) => {
    // Replay log in message view
    const userMsg = {
      id: `past-user-${log.id}`,
      sender: 'user',
      text: log.query,
      timestamp: new Date(log.created_at),
    };
    const asstMsg = {
      id: `past-asst-${log.id}`,
      sender: 'assistant',
      text: log.answer,
      citations: [], // Past log list summarizes retrieved chunk IDs
      is_unanswerable: log.is_unanswerable,
      confidence_score: log.confidence_score,
      latency_ms: log.latency_ms,
      timestamp: new Date(log.created_at),
    };
    setMessages([userMsg, asstMsg]);
  };

  return (
    <div className="chat-layout-wrapper">
      {/* Chat Top Toolbar */}
      <div className="chat-top-bar">
        <div className="chat-top-bar-left">
          <div className="chat-status-indicator">
            <span className="status-dot-pulse" />
            <span className="chat-status-text">Grounded Assistant Active</span>
          </div>
        </div>

        <div className="chat-top-bar-right">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsHistoryOpen(true)}
            icon={<ClockIcon size={14} />}
            title="View query history"
          >
            History
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={handleNewConversation}
            icon={<SparklesIcon size={14} />}
            title="Start a new question thread"
          >
            New Conversation
          </Button>
        </div>
      </div>

      {/* Messages Scroll Area */}
      <div className="chat-messages-viewport">
        {messages.length === 0 ? (
          <EmptyState onSelectSuggestion={(q) => handleSendQuery(q)} />
        ) : (
          <div className="chat-messages-list">
            {messages.map((msg) => (
              <ChatMessage key={msg.id} message={msg} />
            ))}

            {/* Assistant Loading Bubble */}
            {isLoading && (
              <div className="chat-message-row message-assistant message-loading-row">
                <div className="message-avatar">
                  <SparklesIcon size={18} className="spin text-primary" />
                </div>
                <div className="message-bubble-wrapper">
                  <div className="message-bubble loading-bubble">
                    <div className="typing-indicator">
                      <span className="dot" />
                      <span className="dot" />
                      <span className="dot" />
                    </div>
                    <span className="loading-stage-text">
                      Searching pgvector & synthesizing evidence...
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* Inline Error Alert with Retry */}
            {chatError && (
              <div className="alert alert-danger chat-inline-error" role="alert">
                <AlertCircleIcon size={16} className="alert-icon" />
                <div className="alert-content-row">
                  <span className="alert-text">{chatError}</span>
                  {lastQuery && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleSendQuery(lastQuery)}
                      icon={<RefreshCwIcon size={12} />}
                      className="btn-retry"
                    >
                      Retry
                    </Button>
                  )}
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Bottom Composer */}
      <ChatComposer
        value={inputValue}
        onChange={setInputValue}
        onSend={() => handleSendQuery()}
        isLoading={isLoading}
      />

      {/* Past Queries Drawer */}
      <ChatHistoryDrawer
        isOpen={isHistoryOpen}
        onClose={() => setIsHistoryOpen(false)}
        onSelectPastQuery={handleSelectPastQuery}
      />
    </div>
  );
}

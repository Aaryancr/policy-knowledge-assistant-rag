import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { ShieldIcon, SparklesIcon, LogOutIcon, UserIcon, BookOpenIcon } from '../common/Icons';
import { RoleBadge } from '../common/Badge';

export function AppHeader({ activeTab, onTabChange }) {
  const { user, isAdmin, logout } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <header className="app-header">
      <div className="header-inner">
        {/* Brand Group */}
        <div className="header-brand-group">
          <div className="header-logo">
            <ShieldIcon size={22} className="text-primary" />
          </div>
          <div className="header-title-column">
            <span className="header-app-title">Policy & Knowledge Assistant</span>
            <span className="header-env-badge">Enterprise RAG</span>
          </div>
        </div>

        {/* Desktop Navigation Tabs */}
        <nav className="header-nav" aria-label="Main navigation">
          <button
            type="button"
            className={`nav-tab-btn ${activeTab === 'chat' ? 'active' : ''}`}
            onClick={() => {
              onTabChange('chat');
              setMobileMenuOpen(false);
            }}
          >
            <SparklesIcon size={16} />
            <span>Policy Assistant</span>
          </button>

          {isAdmin && (
            <button
              type="button"
              className={`nav-tab-btn ${activeTab === 'admin' ? 'active' : ''}`}
              onClick={() => {
                onTabChange('admin');
                setMobileMenuOpen(false);
              }}
            >
              <BookOpenIcon size={16} />
              <span>Document Management</span>
            </button>
          )}
        </nav>

        {/* User Profile & Logout */}
        <div className="header-user-group">
          <div className="user-profile-summary">
            <div className="user-avatar-circle">
              <UserIcon size={14} />
            </div>
            <div className="user-meta-column">
              <span className="user-display-name">{user?.full_name || user?.email}</span>
              <RoleBadge role={user?.role} />
            </div>
          </div>

          <button
            type="button"
            className="btn-logout"
            onClick={logout}
            title="Log out of workspace"
            aria-label="Log out"
          >
            <LogOutIcon size={16} />
            <span className="logout-text">Sign Out</span>
          </button>

          {/* Mobile Menu Toggle Button */}
          <button
            type="button"
            className="mobile-menu-toggle"
            onClick={() => setMobileMenuOpen((prev) => !prev)}
            aria-label="Toggle navigation menu"
          >
            <span className="hamburger-bar" />
            <span className="hamburger-bar" />
            <span className="hamburger-bar" />
          </button>
        </div>
      </div>

      {/* Mobile Collapsible Navigation */}
      {mobileMenuOpen && (
        <div className="mobile-nav-drawer">
          <button
            type="button"
            className={`mobile-nav-btn ${activeTab === 'chat' ? 'active' : ''}`}
            onClick={() => {
              onTabChange('chat');
              setMobileMenuOpen(false);
            }}
          >
            <SparklesIcon size={16} />
            <span>Policy Assistant</span>
          </button>

          {isAdmin && (
            <button
              type="button"
              className={`mobile-nav-btn ${activeTab === 'admin' ? 'active' : ''}`}
              onClick={() => {
                onTabChange('admin');
                setMobileMenuOpen(false);
              }}
            >
              <BookOpenIcon size={16} />
              <span>Document Management</span>
            </button>
          )}

          <div className="mobile-nav-footer">
            <button type="button" className="mobile-logout-btn" onClick={logout}>
              <LogOutIcon size={16} />
              <span>Sign Out ({user?.email})</span>
            </button>
          </div>
        </div>
      )}
    </header>
  );
}

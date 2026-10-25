import React, { useState } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { LoginForm } from './components/auth/LoginForm';
import { Shell } from './components/layout/Shell';
import { ChatInterface } from './components/chat/ChatInterface';
import { AdminDashboard } from './components/admin/AdminDashboard';
import { ShieldIcon, RefreshCwIcon } from './components/common/Icons';
import './App.css';

function AppContent() {
  const { isAuthenticated, isLoading, isAdmin } = useAuth();
  const [activeTab, setActiveTab] = useState('chat'); // 'chat' | 'admin'

  // Initial Auth Splash Loading Screen
  if (isLoading) {
    return (
      <div className="auth-splash-screen">
        <div className="splash-content">
          <div className="splash-icon-wrapper">
            <ShieldIcon size={36} className="text-primary" />
          </div>
          <h2 className="splash-title">Policy & Knowledge Assistant</h2>
          <div className="splash-spinner-row">
            <RefreshCwIcon size={16} className="spin text-muted" />
            <span className="splash-text">Verifying enterprise session...</span>
          </div>
        </div>
      </div>
    );
  }

  // Unauthenticated -> Login Screen
  if (!isAuthenticated) {
    return <LoginForm />;
  }

  // Enforce role navigation guard
  const currentTab = !isAdmin && activeTab === 'admin' ? 'chat' : activeTab;

  return (
    <Shell
      activeTab={currentTab}
      onTabChange={(tab) => {
        if (tab === 'admin' && !isAdmin) {
          setActiveTab('chat');
        } else {
          setActiveTab(tab);
        }
      }}
    >
      {currentTab === 'admin' ? <AdminDashboard /> : <ChatInterface />}
    </Shell>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

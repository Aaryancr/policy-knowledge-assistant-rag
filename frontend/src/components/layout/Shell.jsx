import React from 'react';
import { AppHeader } from './AppHeader';

export function Shell({ activeTab, onTabChange, children }) {
  return (
    <div className="app-shell">
      <AppHeader activeTab={activeTab} onTabChange={onTabChange} />
      <main className="shell-main-content">
        <div className="shell-container">{children}</div>
      </main>
    </div>
  );
}

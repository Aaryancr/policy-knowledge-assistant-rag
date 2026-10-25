import React from 'react';
import { CheckCircleIcon, AlertCircleIcon, RefreshCwIcon, ClockIcon, ShieldIcon, UserIcon } from './Icons';

export function StatusBadge({ status, size = 'md' }) {
  const norm = (status || 'unknown').toLowerCase();

  const configs = {
    completed: {
      label: 'Completed',
      className: 'badge-completed',
      icon: <CheckCircleIcon size={12} />,
    },
    processing: {
      label: 'Processing',
      className: 'badge-processing',
      icon: <RefreshCwIcon size={12} className="spin" />,
    },
    queued: {
      label: 'Queued',
      className: 'badge-queued',
      icon: <ClockIcon size={12} />,
    },
    failed: {
      label: 'Failed',
      className: 'badge-failed',
      icon: <AlertCircleIcon size={12} />,
    },
    pending: {
      label: 'Pending',
      className: 'badge-pending',
      icon: <ClockIcon size={12} />,
    },
  };

  const conf = configs[norm] || {
    label: status,
    className: 'badge-default',
    icon: null,
  };

  return (
    <span className={`badge ${conf.className} badge-${size}`}>
      {conf.icon}
      <span>{conf.label}</span>
    </span>
  );
}

export function RoleBadge({ role }) {
  const isAdmin = role === 'admin';
  return (
    <span className={`badge ${isAdmin ? 'badge-admin' : 'badge-employee'} badge-sm`}>
      {isAdmin ? <ShieldIcon size={11} /> : <UserIcon size={11} />}
      <span>{isAdmin ? 'Admin' : 'Employee'}</span>
    </span>
  );
}

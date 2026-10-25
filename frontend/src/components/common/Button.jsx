import React from 'react';
import { RefreshCwIcon } from './Icons';

export function Button({
  children,
  variant = 'primary', // 'primary' | 'secondary' | 'danger' | 'ghost' | 'outline'
  size = 'md',         // 'sm' | 'md' | 'lg'
  isLoading = false,
  disabled = false,
  icon = null,
  iconPosition = 'left',
  type = 'button',
  className = '',
  onClick,
  ...rest
}) {
  const isDisabled = disabled || isLoading;

  return (
    <button
      type={type}
      disabled={isDisabled}
      onClick={onClick}
      className={`btn btn-${variant} btn-${size} ${className}`}
      {...rest}
    >
      {isLoading ? (
        <RefreshCwIcon size={size === 'sm' ? 12 : 16} className="spin btn-icon" />
      ) : icon && iconPosition === 'left' ? (
        <span className="btn-icon">{icon}</span>
      ) : null}

      <span className="btn-text">{children}</span>

      {!isLoading && icon && iconPosition === 'right' ? (
        <span className="btn-icon btn-icon-right">{icon}</span>
      ) : null}
    </button>
  );
}

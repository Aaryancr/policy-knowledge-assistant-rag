import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { EyeIcon, EyeOffIcon, ShieldIcon, AlertCircleIcon, SparklesIcon } from '../common/Icons';
import { Button } from '../common/Button';

export function LoginForm() {
  const { login, isLoading } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [validationErrors, setValidationErrors] = useState({});

  // Demo credential autofill is only enabled in local development or when explicitly enabled
  const showDemoCredentials = Boolean(
    import.meta.env.DEV && import.meta.env.VITE_ENABLE_DEMO_CREDENTIALS !== 'false'
  ) || import.meta.env.VITE_ENABLE_DEMO_CREDENTIALS === 'true';

  const validate = () => {
    const errs = {};
    if (!email.trim()) {
      errs.email = 'Email address is required';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
      errs.email = 'Please enter a valid email address';
    }

    if (!password) {
      errs.password = 'Password is required';
    }
    setValidationErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMessage('');

    if (!validate()) {
      return;
    }

    try {
      await login(email.trim(), password);
    } catch (err) {
      setErrorMessage(err.message || 'Login failed. Please verify your credentials.');
    }
  };

  const handleFillDemo = (demoEmail, demoPassword) => {
    setEmail(demoEmail);
    setPassword(demoPassword);
    setValidationErrors({});
    setErrorMessage('');
  };

  return (
    <div className="login-page">
      <div className="login-card">
        {/* Brand Header */}
        <div className="login-brand">
          <div className="brand-logo-icon">
            <ShieldIcon size={28} />
          </div>
          <h1 className="brand-title">Policy & Knowledge Assistant</h1>
          <p className="brand-subtitle">
            Enterprise Retrieval-Augmented Generation for HR, IT, and internal corporate guidelines.
          </p>
        </div>

        {/* Server Error Alert */}
        {errorMessage && (
          <div className="alert alert-danger" role="alert">
            <AlertCircleIcon size={16} className="alert-icon" />
            <span className="alert-text">{errorMessage}</span>
          </div>
        )}

        {/* Login Form */}
        <form onSubmit={handleSubmit} className="login-form" noValidate>
          <div className="form-group">
            <label htmlFor="login-email" className="form-label">
              Corporate Email
            </label>
            <input
              id="login-email"
              type="email"
              autoComplete="email"
              placeholder="name@company.com"
              value={email}
              onChange={(e) => {
                setEmail(e.target.value);
                if (validationErrors.email) {
                  setValidationErrors((prev) => ({ ...prev, email: null }));
                }
              }}
              className={`form-input ${validationErrors.email ? 'input-error' : ''}`}
              disabled={isLoading}
            />
            {validationErrors.email && (
              <span className="form-error">{validationErrors.email}</span>
            )}
          </div>

          <div className="form-group">
            <label htmlFor="login-password" className="form-label">
              Password
            </label>
            <div className="password-input-wrapper">
              <input
                id="login-password"
                type={showPassword ? 'text' : 'password'}
                autoComplete="current-password"
                placeholder="Enter your password"
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  if (validationErrors.password) {
                    setValidationErrors((prev) => ({ ...prev, password: null }));
                  }
                }}
                className={`form-input password-input ${validationErrors.password ? 'input-error' : ''}`}
                disabled={isLoading}
              />
              <button
                type="button"
                className="password-toggle-btn"
                onClick={() => setShowPassword((prev) => !prev)}
                aria-label={showPassword ? 'Hide password' : 'Show password'}
                tabIndex={0}
              >
                {showPassword ? <EyeOffIcon size={18} /> : <EyeIcon size={18} />}
              </button>
            </div>
            {validationErrors.password && (
              <span className="form-error">{validationErrors.password}</span>
            )}
          </div>

          <Button
            type="submit"
            variant="primary"
            size="lg"
            isLoading={isLoading}
            className="w-full login-submit-btn"
          >
            Sign In to Workspace
          </Button>
        </form>

        {/* Development Demo Quick-Fill Helpers (strictly disabled in production builds) */}
        {showDemoCredentials && (
          <div className="login-demo-section">
            <div className="demo-divider">
              <span>Local Dev Quick-Fill</span>
            </div>
            <p className="demo-disclaimer" style={{ fontSize: '0.75rem', color: 'var(--color-slate-400)', textAlign: 'center', marginBottom: '0.75rem' }}>
              Sample dev accounts for local testing. Disabled in production.
            </p>
            <div className="demo-buttons-grid">
              <button
                type="button"
                className="demo-chip-btn"
                onClick={() => handleFillDemo('admin@example.com', 'Admin@ChangeMe123!')}
                title="Sign in as System Administrator (Local Dev)"
              >
                <ShieldIcon size={13} className="text-primary" />
                <span>Admin Dev</span>
              </button>
              <button
                type="button"
                className="demo-chip-btn"
                onClick={() => handleFillDemo('employee@example.com', 'EmployeePass123!')}
                title="Sign in as Policy Employee (Local Dev)"
              >
                <SparklesIcon size={13} className="text-cyan" />
                <span>Employee Dev</span>
              </button>
            </div>
          </div>
        )}

        {/* Security Footer Note */}
        <div className="login-security-notice">
          <p>
            Protected by role-based access control and JWT bearer authorization.
          </p>
        </div>
      </div>
    </div>
  );
}

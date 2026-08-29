'use client';

import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { setAuthToken } from '@/lib/apiClient';
import styles from './AuthForm.module.css';

export default function LoginForm({ onSuccess, onToggle }) {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      if (!email || !password) {
        setError('Please fill in all fields');
        setLoading(false);
        return;
      }

      // Call real backend login endpoint
      const apiUrl = import.meta.env.REACT_APP_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });

      if (!response.ok) {
        const data = await response.json();
        setError(data.detail || 'Login failed. Please check your credentials.');
        setLoading(false);
        return;
      }

      const data = await response.json();
      const token = data.token;
      const user = data.user;
      const streamerId = data.streamer_id;

      // Store real auth token using apiClient helper (sets correct storage key + clears caches)
      setAuthToken(token, true);
      localStorage.setItem('userRole', user.role);
      localStorage.setItem('streamerEmail', user.email);
      localStorage.setItem('streamerName', user.email.split('@')[0]);
      if (streamerId) {
        localStorage.setItem('streamerId', streamerId.toString());
      }

      console.log('✓ Real auth successful:', {
        token: token.substring(0, 20) + '...',
        email: user.email,
        role: user.role
      });

      // Navigate to dashboard
      if (onSuccess) {
        onSuccess();
      } else {
        navigate('/dashboard');
      }
    } catch (err) {
      console.error('Login error:', err);
      setError('Network error. Please try again.');
      setLoading(false);
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.card}>
        {/* Logo */}
        <div className={styles.logoSection}>
          <img src="/logo.png" alt="Kazumee" className={styles.logo} />
          <p className={styles.logoText}>kazumee</p>
          <p className={styles.logoSubtext}>STREAM • ENGAGE • GROW</p>
        </div>

        <h1 className={styles.title}>Log In</h1>

        <form onSubmit={handleSubmit} className={styles.form}>
          <div className={styles.formGroup}>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Email"
              required
              className={styles.input}
            />
          </div>

          <div className={styles.formGroup}>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Password"
              required
              className={styles.input}
            />
          </div>

          {error && <div className={styles.error}>{error}</div>}

          <button type="submit" className={styles.submit} disabled={loading}>
            {loading ? 'Signing in...' : 'Log In'}
          </button>
        </form>

        <Link to="/forgot-password" className={styles.forgotPassword}>
          Forgot Password?
        </Link>

        <div className={styles.divider}>or</div>

        <button className={styles.googleButton}>
          <svg className={styles.googleIcon} viewBox="0 0 24 24" fill="currentColor">
            <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
            <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
            <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
            <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
          </svg>
          Log in with Google
        </button>

        <p className={styles.signup}>
          Don't have an account? <button type="button" onClick={onToggle} className={styles.signupLink} style={{background: 'none', border: 'none', cursor: 'pointer', padding: 0}}>Sign Up</button>
        </p>
      </div>
    </div>
  );
}


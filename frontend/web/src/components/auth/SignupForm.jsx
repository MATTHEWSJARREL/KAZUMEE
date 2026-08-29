'use client';

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { setAuthToken } from '@/lib/apiClient';
import styles from './AuthForm.module.css';

export default function SignupForm({ onSuccess, onToggle }) {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    streamerName: '',
    email: '',
    password: '',
    confirmPassword: '',
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      if (!formData.streamerName || !formData.email || !formData.password) {
        setError('Please fill in all fields');
        setLoading(false);
        return;
      }

      if (formData.password !== formData.confirmPassword) {
        setError('Passwords do not match');
        setLoading(false);
        return;
      }

      if (formData.password.length < 6) {
        setError('Password must be at least 6 characters');
        setLoading(false);
        return;
      }

      // Call real backend registration endpoint
      const apiUrl = import.meta.env.REACT_APP_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: formData.email,
          password: formData.password,
          role: 'streamer'
        })
      });

      if (!response.ok) {
        const data = await response.json();
        setError(data.detail || 'Signup failed. Please try again.');
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
      localStorage.setItem('streamerName', formData.streamerName);
      if (streamerId) {
        localStorage.setItem('streamerId', streamerId.toString());
      }

      console.log('✓ Real signup successful:', {
        token: token.substring(0, 20) + '...',
        email: user.email,
        role: user.role
      });

      // Navigate to dashboard
      if (onSuccess) {
        onSuccess();
      } else {
        navigate('/dashboard', { replace: true });
      }
    } catch (err) {
      console.error('Signup error:', err);
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

        <h1 className={styles.title}>Sign Up</h1>

        <form onSubmit={handleSubmit} className={styles.form}>
          <div className={styles.formGroup}>
            <input
              id="streamerName"
              name="streamerName"
              type="text"
              value={formData.streamerName}
              onChange={handleChange}
              placeholder="Streamer Name"
              required
              className={styles.input}
            />
          </div>

          <div className={styles.formGroup}>
            <input
              id="email"
              name="email"
              type="email"
              value={formData.email}
              onChange={handleChange}
              placeholder="Email"
              required
              className={styles.input}
            />
          </div>

          <div className={styles.formGroup}>
            <input
              id="password"
              name="password"
              type="password"
              value={formData.password}
              onChange={handleChange}
              placeholder="Password"
              required
              className={styles.input}
            />
          </div>

          <div className={styles.formGroup}>
            <input
              id="confirmPassword"
              name="confirmPassword"
              type="password"
              value={formData.confirmPassword}
              onChange={handleChange}
              placeholder="Confirm Password"
              required
              className={styles.input}
            />
          </div>

          {error && <div className={styles.error}>{error}</div>}

          <button type="submit" className={styles.submit} disabled={loading}>
            {loading ? 'Creating account...' : 'Sign Up Free'}
          </button>
        </form>

        <p className={styles.signup}>
          Already have an account? <button type="button" onClick={onToggle} className={styles.signupLink} style={{background: 'none', border: 'none', cursor: 'pointer', padding: 0}}>Log In</button>
        </p>
      </div>
    </div>
  );
}


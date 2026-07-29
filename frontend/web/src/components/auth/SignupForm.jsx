'use client';

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
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
      if (formData.password !== formData.confirmPassword) {
        setError('Passwords do not match');
        setLoading(false);
        return;
      }

      if (formData.streamerName && formData.email && formData.password) {
        // Store auth token
        const token = 'mock-token-' + Date.now();
        localStorage.setItem('kazumi_auth_token', token);
        localStorage.setItem('kazumi_auth_bypass', 'true');
        localStorage.setItem('userRole', 'streamer');
        localStorage.setItem('streamerEmail', formData.email);
        localStorage.setItem('streamerName', formData.streamerName);

        console.log('✓ Signup stored:', {
          token,
          role: 'streamer',
          email: formData.email,
          name: formData.streamerName,
        });

        if (onSuccess) {
          onSuccess();
        } else {
          navigate('/dashboard', { replace: true });
        }
      } else {
        setError('Please fill in all fields');
        setLoading(false);
      }
    } catch (err) {
      console.error('Signup error:', err);
      setError('Signup failed. Please try again.');
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


'use client';

import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import LoginForm from '@/components/auth/LoginForm';
import SignupForm from '@/components/auth/SignupForm';
import styles from './auth.module.css';

export default function AuthPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [isSignup, setIsSignup] = useState(false);

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    if (params.get('tab') === 'signup') {
      setIsSignup(true);
    }
  }, [location.search]);

  const handleAuthSuccess = () => {
    navigate('/dashboard');
  };

  const toggleForm = () => {
    setIsSignup(!isSignup);
  };

  return (
    <div className={styles.container}>
      <div className={styles.background} />

      <div className={styles.content}>
        {/* Left Side - Branding */}
        <div className={styles.branding}>
          <div className={styles.brandingContent}>
            <img src="/logo.png" alt="Kazumee" className={styles.brandLogo} />
            <h1 className={styles.brandTitle}>Kazumee</h1>
            <p className={styles.brandTagline}>Auto-Clip Creation</p>

            <div className={styles.features}>
              <div className={styles.featureItem}>
                <span className={styles.featureIcon}>⚡</span>
                <span>AI detects epic moments</span>
              </div>
              <div className={styles.featureItem}>
                <span className={styles.featureIcon}>🎬</span>
                <span>Instant formatted clips</span>
              </div>
              <div className={styles.featureItem}>
                <span className={styles.featureIcon}>📊</span>
                <span>Growth analytics</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right Side - Auth Form */}
        <div className={styles.authContainer}>
          {isSignup ? (
            <SignupForm onSuccess={handleAuthSuccess} onToggle={toggleForm} />
          ) : (
            <LoginForm onSuccess={handleAuthSuccess} onToggle={toggleForm} />
          )}
        </div>
      </div>
    </div>
  );
}

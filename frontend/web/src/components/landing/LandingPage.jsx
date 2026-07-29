'use client';

import Hero from './Hero';
import Features from './Features';
import CTA from './CTA';
import styles from './LandingPage.module.css';

export default function LandingPage() {
  return (
    <div className={styles.container}>
      <Hero />
      <Features />
      <CTA />
    </div>
  );
}

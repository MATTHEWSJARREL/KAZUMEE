'use client';

import Navbar from '@/components/landing/Navbar';
import Hero from '@/components/landing/Hero';
import Features from '@/components/landing/Features';
import CTA from '@/components/landing/CTA';
import Footer from '@/components/landing/Footer';
import styles from './page.module.css';

export default function HomePage() {
  return (
    <div className={styles.container}>
      <Navbar />
      <Hero />
      <Features />
      <CTA />
      <Footer />
    </div>
  );
}

import React from "react";

interface LandingPageProps {
  onExplore: () => void;
}

export default function LandingPage({ onExplore }: LandingPageProps) {
  return (
    <div className="prof-landing-container">
      <div className="prof-landing-bg">
        <div className="bg-pattern" />
        <div className="bg-glow" />
      </div>

      <header className="prof-landing-nav">
        <div className="logo-section">
          <div className="logo-icon" />
          <span className="logo-text">Graph-Based Data Modeling and Query System</span>
        </div>
        <div className="nav-status">
          <span className="status-indicator" /> System Online
        </div>
      </header>

      <main className="prof-landing-hero">
        <div className="hero-content">
          <div className="badge-premium">Intelligent Tracing Engine</div>
          <h1 className="hero-title">
            The Next Dimension of <span className="text-accent">Order Visibility.</span>
          </h1>
          <p className="hero-subtitle">
            A high-fidelity graph explorer for end-to-end Order-to-Cash lifecycles.
            Trace every document, item, and accounting bridge with absolute precision.
          </p>

          <div className="cta-wrapper">
            <button className="btn-primary-prof" onClick={onExplore}>
              Initialize Explorer
              <svg
                viewBox="0 0 24 24"
                width="20"
                height="20"
                stroke="currentColor"
                strokeWidth="2.5"
                fill="none"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <line x1="5" y1="12" x2="19" y2="12"></line>
                <polyline points="12 5 19 12 12 19"></polyline>
              </svg>
            </button>
          </div>
        </div>

        <div className="hero-visual">
          <div className="visual-monolith-mock">
            <div className="mock-header">
              <div className="dots">
                <span className="d red" />
                <span className="d yellow" />
                <span className="d green" />
              </div>
            </div>
            <div className="mock-body">
              <div className="graph-node-sample" />
              <div className="graph-node-sample" />
              <div className="graph-node-sample" />
              <div className="line-sample" />
            </div>
          </div>
        </div>
      </main>

      <footer className="prof-landing-footer">
        <div className="footer-grid">
          <div className="footer-item">
            <span className="f-label">Precision</span>
          </div>
          <div className="footer-item">
            <span className="f-label">Speed</span>
          </div>
          <div className="footer-item">
            <span className="f-label">Schema</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

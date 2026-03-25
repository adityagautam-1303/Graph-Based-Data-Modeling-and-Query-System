
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
        <div className="hero-split">
          <div className="hero-copy">
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
        </div>

        <div className="landing-info-sections">
          <div className="info-group">
            <h3 className="section-label">Core Flow</h3>
            <ul className="info-list">
              <li>Orders</li>
              <li>Deliveries</li>
              <li>Invoices</li>
              <li>Payments</li>
            </ul>
          </div>
          <div className="info-group">
            <h3 className="section-label">Supporting Entities</h3>
            <ul className="info-list">
              <li>Customers</li>
              <li>Products</li>
              <li>Address</li>
            </ul>
          </div>
        </div>

        <div className="hero-queries">
          <div className="queries-card">
            <h3 className="section-label">Example Queries</h3>
            <div className="query-examples">
              <div className="query-item">
                <span className="q-bullet">a</span>
                <p>Which products are associated with the highest number of billing documents?</p>
              </div>
              <div className="query-item">
                <span className="q-bullet">b</span>
                <p>Trace the full flow of a given billing document (Sales Order → Delivery → Billing → Journal Entry)</p>
              </div>
              <div className="query-item">
                <span className="q-bullet">c</span>
                <p>Identify sales orders that have broken or incomplete flows (e.g. delivered but not billed, billed without delivery)</p>
              </div>
              <div className="query-item">
                <span className="q-bullet">d</span>
                <p>"Trace the full flow for Delivery 80737921. Does it have multiple billing documents?"</p>
              </div>
              <div className="query-item">
                <span className="q-bullet">e</span>
                <p>"Trace Billing Document 90504274. Show its related delivery and journal entry."</p>
              </div>
            </div>
          </div>
        </div>
      </main>

      <footer className="prof-landing-footer">
        <div className="footer-grid">
          <div className="footer-item">
            <span className="f-label">Precision</span>
            <span className="f-value">High-Fidelity Graph</span>
          </div>
          <div className="footer-item">
            <span className="f-label">Speed</span>
            <span className="f-value">Real-time Tracing</span>
          </div>
          <div className="footer-item">
            <span className="f-label">Schema</span>
            <span className="f-value">SAP O2C Standard</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

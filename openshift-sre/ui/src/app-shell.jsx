import React from 'react';
import { createRoot } from 'react-dom/client';

const NAV_ITEMS = [
  { key: 'console', label: 'Agent Console', href: 'console.html', short: 'AC' },
  { key: 'security', label: 'Security Console', href: 'security-console.html', short: 'SC' },
  { key: 'architect', label: 'Architect Workspace', href: 'architect.html', short: 'AR' },
  { key: 'openshift-builder', label: 'OpenShift Builder', href: 'openshift-builder.html', short: 'OB' },
  { key: 'platform', label: 'Platform Console', href: 'platform-console.html', short: 'PF' },
  { key: 'posture-radar', label: 'Posture Radar', href: 'posture-radar.html', short: 'PR' },
  { key: 'watchlists', label: 'Watchlists', href: 'watchlists.html', short: 'WL' },
  { key: 'drift-diff', label: 'Drift Diff', href: 'drift-diff.html', short: 'DD' },
  { key: 'finops', label: 'FinOps Console', href: 'finops-console.html', short: 'FO' },
  { key: 'troubleshooting', label: 'Troubleshooting', href: 'troubleshooting.html', short: 'TR' },
  { key: 'history', label: 'History', href: 'history.html', short: 'HS' },
  { key: 'llm', label: 'LLM Utilization', href: 'llm-utilization.html', short: 'AI' },
  { key: 'tool-drilldown', label: 'Tool Drilldown', href: 'tool-drilldown.html', short: 'TD' },
];

const PAGE_THEMES = {
  console: { short: 'AC', tone: 'Live operator workspace', eyebrow: 'Direct run surface' },
  security: { short: 'SC', tone: 'Audit and security review lane', eyebrow: 'Dedicated cloud security workspace' },
  architect: { short: 'AR', tone: 'Architecture design and handoff lane', eyebrow: 'OpenShift-native design studio' },
  'openshift-builder': { short: 'OB', tone: 'Delivery implementation workspace', eyebrow: 'Architect-to-pipeline builder' },
  platform: { short: 'PF', tone: 'Lifecycle and resiliency workspace', eyebrow: 'Platform operations control lane' },
  'posture-radar': { short: 'PR', tone: 'Cross-account posture command lane', eyebrow: 'Multi-region sweep visualizer' },
  watchlists: { short: 'WL', tone: 'Saved investigation workspace', eyebrow: 'Operator watch automation' },
  'drift-diff': { short: 'DD', tone: 'Run-to-run drift analysis', eyebrow: 'Baseline comparison cockpit' },
  finops: { short: 'FO', tone: 'Cost intelligence workspace', eyebrow: 'Financial operations control deck' },
  troubleshooting: { short: 'TR', tone: 'Failure isolation workspace', eyebrow: 'Incident-first design' },
  history: { short: 'HS', tone: 'Analytics and trend review', eyebrow: 'Observability-informed review' },
  llm: { short: 'AI', tone: 'Model runtime snapshot', eyebrow: 'Inference visibility' },
  'tool-drilldown': { short: 'TD', tone: 'Per-tool inspection lane', eyebrow: 'Focused evidence analysis' },
};

const STORAGE_KEYS = {
  theme: 'openshift-sre-shell-theme',
  density: 'openshift-sre-shell-density',
  motion: 'openshift-sre-shell-motion',
};

function getStoredValue(key, fallback) {
  try {
    return window.localStorage.getItem(key) || fallback;
  } catch {
    return fallback;
  }
}

function setStoredValue(key, value) {
  try {
    window.localStorage.setItem(key, value);
  } catch {
    // Ignore storage failures in locked-down preview contexts.
  }
}

function useStoredState(key, fallback) {
  const [value, setValue] = React.useState(() => getStoredValue(key, fallback));

  React.useEffect(() => {
    setStoredValue(key, value);
  }, [key, value]);

  return [value, setValue];
}

function readProps(node) {
  const script = node.querySelector('[data-app-shell-props]');
  if (!script) {
    return {};
  }

  try {
    return JSON.parse(script.textContent || '{}');
  } catch (error) {
    console.error('Unable to parse app shell props.', error);
    return {};
  }
}

function ActionLink({ action, primary = false }) {
  if (!action?.href || !action?.label) {
    return null;
  }

  return (
    <a
      className={`agent-shell__action ${primary ? 'agent-shell__action--primary' : 'agent-shell__action--secondary'}`}
      href={action.href}
    >
      <span className="agent-shell__action-label">{action.label}</span>
      <span className="agent-shell__action-glyph" aria-hidden="true">→</span>
    </a>
  );
}

function UtilityToggle({ label, active, onClick }) {
  return (
    <button
      className={`agent-shell__utility-toggle ${active ? 'agent-shell__utility-toggle--active' : ''}`}
      type="button"
      onClick={onClick}
      aria-pressed={active}
    >
      {label}
    </button>
  );
}

function ShortcutPill({ shortcut }) {
  if (!shortcut) {
    return null;
  }

  if (typeof shortcut === 'string') {
    return <span className="agent-shell__shortcut-pill">{shortcut}</span>;
  }

  if (shortcut.href) {
    return (
      <a className="agent-shell__shortcut-pill agent-shell__shortcut-pill--link" href={shortcut.href}>
        {shortcut.label}
      </a>
    );
  }

  return <span className="agent-shell__shortcut-pill">{shortcut.label}</span>;
}

function FeatureGroup({ group }) {
  const items = Array.isArray(group?.items) ? group.items : [];
  if (!group?.title || items.length === 0) {
    return null;
  }

  return (
    <article className="agent-shell__feature-group agent-shell__tilt">
      <div className="agent-shell__feature-header">
        {group.kicker ? <p className="agent-shell__feature-kicker">{group.kicker}</p> : null}
        <h2 className="agent-shell__feature-title">{group.title}</h2>
        {group.description ? <p className="agent-shell__feature-copy">{group.description}</p> : null}
      </div>
      <div className="agent-shell__feature-grid">
        {items.map((item) => (
          <article key={`${group.title}-${item.title}`} className="agent-shell__feature-card">
            <div className="agent-shell__feature-card-topline">
              <span className="agent-shell__feature-dot" aria-hidden="true"></span>
              {item.meta ? <span className="agent-shell__feature-meta">{item.meta}</span> : null}
            </div>
            <h3 className="agent-shell__feature-card-title">{item.title}</h3>
            <p className="agent-shell__feature-card-copy">{item.description}</p>
            {item.href ? (
              <a className="agent-shell__feature-link" href={item.href}>
                Jump in <span aria-hidden="true">↗</span>
              </a>
            ) : null}
          </article>
        ))}
      </div>
    </article>
  );
}

function AppShell({ page }) {
  const [themeMode, setThemeMode] = useStoredState(STORAGE_KEYS.theme, document.body.dataset.theme || 'light');
  const [density, setDensity] = useStoredState(STORAGE_KEYS.density, 'comfortable');
  const [motion, setMotion] = useStoredState(STORAGE_KEYS.motion, 'full');
  const [clock, setClock] = React.useState(() => new Date());

  React.useEffect(() => {
    document.body.dataset.shellPage = page.key || 'default';
    document.body.dataset.theme = themeMode;
    document.body.dataset.density = density;
    document.body.dataset.motion = motion;
  }, [page.key, themeMode, density, motion]);

  React.useEffect(() => {
    const timer = window.setInterval(() => setClock(new Date()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  React.useEffect(() => {
    if (motion === 'off' || window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      return undefined;
    }

    const tiltNodes = Array.from(document.querySelectorAll('.agent-shell__tilt'));
    const cleanups = tiltNodes.map((node) => {
      const onMove = (event) => {
        const bounds = node.getBoundingClientRect();
        const x = ((event.clientX - bounds.left) / bounds.width) - 0.5;
        const y = ((event.clientY - bounds.top) / bounds.height) - 0.5;
        node.style.setProperty('--agent-tilt-x', `${(x * 10).toFixed(2)}deg`);
        node.style.setProperty('--agent-tilt-y', `${(y * -10).toFixed(2)}deg`);
        node.style.setProperty('--agent-glow-x', `${((x + 0.5) * 100).toFixed(2)}%`);
        node.style.setProperty('--agent-glow-y', `${((y + 0.5) * 100).toFixed(2)}%`);
      };

      const onLeave = () => {
        node.style.setProperty('--agent-tilt-x', '0deg');
        node.style.setProperty('--agent-tilt-y', '0deg');
        node.style.setProperty('--agent-glow-x', '50%');
        node.style.setProperty('--agent-glow-y', '50%');
      };

      node.addEventListener('pointermove', onMove);
      node.addEventListener('pointerleave', onLeave);
      return () => {
        node.removeEventListener('pointermove', onMove);
        node.removeEventListener('pointerleave', onLeave);
      };
    });

    return () => cleanups.forEach((cleanup) => cleanup());
  }, [page.key, motion, page.featureGroups, page.highlights, page.stats]);

  const pageTheme = PAGE_THEMES[page.key] || { short: 'OP', tone: 'Operator workspace', eyebrow: 'Shared workspace' };
  const previewMode = window.location.protocol === 'file:';
  const badges = Array.isArray(page.badges) ? page.badges : [];
  const actions = Array.isArray(page.actions) ? page.actions : [];
  const secondaryActions = Array.isArray(page.secondaryActions) ? page.secondaryActions : [];
  const stats = Array.isArray(page.stats) ? page.stats : [];
  const highlights = Array.isArray(page.highlights) ? page.highlights : [];
  const sectionNav = Array.isArray(page.sectionNav) ? page.sectionNav : [];
  const shortcuts = Array.isArray(page.shortcuts) ? page.shortcuts : [];
  const featureGroups = Array.isArray(page.featureGroups) ? page.featureGroups : [];
  const workspaceSignals = Array.isArray(page.workspaceSignals) ? page.workspaceSignals : [
    `${previewMode ? 'Static preview' : 'Live origin'} mode`,
    `${themeMode === 'dark' ? 'Dark' : 'Light'} theme`,
    density === 'compact' ? 'Compact density' : 'Comfortable density',
    motion === 'off' ? 'Motion reduced' : 'Motion enabled',
  ];
  const liveTime = clock.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  const liveDate = clock.toLocaleDateString([], { day: '2-digit', month: 'short', year: 'numeric' });

  return (
    <div className={`agent-shell agent-shell--${page.key || 'default'}`}>
      <div className="agent-shell__orb agent-shell__orb--primary" aria-hidden="true"></div>
      <div className="agent-shell__orb agent-shell__orb--secondary" aria-hidden="true"></div>
      <div className="agent-shell__frame agent-shell__tilt">
        <header className="agent-shell__chrome">
          <div className="agent-shell__brand-block">
            <div className="agent-shell__brand-row">
              <span className="agent-shell__brand-mark" aria-hidden="true">{pageTheme.short}</span>
              <span className="agent-shell__eyebrow">OpenShift SRE local agent</span>
            </div>
            <a className="agent-shell__brand" href="index.html">
              Operator workspace
            </a>
          </div>
          <div className="agent-shell__chrome-tools">
            <nav className="agent-shell__nav" aria-label="Documentation tools">
              {NAV_ITEMS.map((item) => (
                <a
                  key={item.key}
                  className={`agent-shell__nav-link ${page.key === item.key ? 'agent-shell__nav-link--active' : ''}`}
                  href={item.href}
                  aria-current={page.key === item.key ? 'page' : undefined}
                >
                  <span className="agent-shell__nav-icon" aria-hidden="true">{item.short}</span>
                  <span>{item.label}</span>
                </a>
              ))}
            </nav>
            <div className="agent-shell__utility-row" aria-label="Workspace controls">
              <UtilityToggle label={`${themeMode === 'dark' ? 'Dark' : 'Light'} theme`} active={themeMode === 'dark'} onClick={() => setThemeMode(themeMode === 'dark' ? 'light' : 'dark')} />
              <UtilityToggle label={density === 'compact' ? 'Compact' : 'Comfortable'} active={density === 'compact'} onClick={() => setDensity(density === 'compact' ? 'comfortable' : 'compact')} />
              <UtilityToggle label={motion === 'off' ? 'Motion off' : 'Motion on'} active={motion !== 'off'} onClick={() => setMotion(motion === 'off' ? 'full' : 'off')} />
            </div>
          </div>
        </header>

        <section className="agent-shell__hero">
          <div className="agent-shell__hero-copy">
            {page.eyebrow ? <p className="agent-shell__hero-eyebrow">{page.eyebrow}</p> : null}
            <div className="agent-shell__hero-title-row">
              <span className="agent-shell__hero-icon" aria-hidden="true">{pageTheme.short}</span>
              <h1 className="agent-shell__hero-title">{page.title || 'OpenShift SRE workspace'}</h1>
            </div>
            {page.description ? <p className="agent-shell__hero-description">{page.description}</p> : null}
            <div className="agent-shell__hero-meta">
              <span className="agent-shell__hero-meta-chip">{pageTheme.tone}</span>
              <span className="agent-shell__hero-meta-chip">{pageTheme.eyebrow}</span>
            </div>
            {badges.length > 0 ? (
              <div className="agent-shell__badge-row">
                {badges.map((badge) => (
                  <span key={badge} className="agent-shell__badge">
                    <span className="agent-shell__badge-dot" aria-hidden="true"></span>
                    {badge}
                  </span>
                ))}
              </div>
            ) : null}
            {(actions.length > 0 || secondaryActions.length > 0) ? (
              <div className="agent-shell__actions">
                {actions.map((action) => (
                  <ActionLink key={`${action.label}-${action.href}`} action={action} primary />
                ))}
                {secondaryActions.map((action) => (
                  <ActionLink key={`${action.label}-${action.href}`} action={action} />
                ))}
              </div>
            ) : null}
          </div>

          <aside className="agent-shell__hero-panel agent-shell__tilt">
            <section className="agent-shell__workspace-panel">
              <div className="agent-shell__workspace-topline">
                <span className={`agent-shell__live-pill ${previewMode ? 'agent-shell__live-pill--preview' : ''}`}>
                  <span className="agent-shell__live-dot" aria-hidden="true"></span>
                  {previewMode ? 'Static preview' : 'Live workspace'}
                </span>
                <span className="agent-shell__workspace-time">{liveTime}</span>
              </div>
              <div className="agent-shell__workspace-grid">
                <article>
                  <p className="agent-shell__workspace-label">Date</p>
                  <p className="agent-shell__workspace-value">{liveDate}</p>
                </article>
                <article>
                  <p className="agent-shell__workspace-label">Theme</p>
                  <p className="agent-shell__workspace-value">{themeMode === 'dark' ? 'Dark' : 'Light'}</p>
                </article>
                <article>
                  <p className="agent-shell__workspace-label">Density</p>
                  <p className="agent-shell__workspace-value">{density === 'compact' ? 'Compact' : 'Comfortable'}</p>
                </article>
                <article>
                  <p className="agent-shell__workspace-label">Motion</p>
                  <p className="agent-shell__workspace-value">{motion === 'off' ? 'Reduced' : 'Full'}</p>
                </article>
              </div>
              <div className="agent-shell__workspace-signals">
                {workspaceSignals.map((signal) => (
                  <span key={signal} className="agent-shell__workspace-chip">{signal}</span>
                ))}
              </div>
            </section>
            {stats.length > 0 ? (
              <div className="agent-shell__stats">
                {stats.map((item, index) => (
                  <article key={`${item.label}-${item.value}`} className="agent-shell__stat-card agent-shell__tilt">
                    <div className="agent-shell__stat-topline">
                      <span className="agent-shell__stat-icon" aria-hidden="true">0{index + 1}</span>
                      <p className="agent-shell__stat-label">{item.label}</p>
                    </div>
                    <p className="agent-shell__stat-value">{item.value}</p>
                    {item.detail ? <p className="agent-shell__stat-detail">{item.detail}</p> : null}
                  </article>
                ))}
              </div>
            ) : null}
          </aside>
        </section>

        {(sectionNav.length > 0 || shortcuts.length > 0) ? (
          <section className="agent-shell__command-deck agent-shell__tilt" aria-label="Workspace command deck">
            {sectionNav.length > 0 ? (
              <div className="agent-shell__deck-block">
                <p className="agent-shell__deck-kicker">Section jump</p>
                <div className="agent-shell__deck-links">
                  {sectionNav.map((item) => (
                    <a key={`${item.label}-${item.href}`} className="agent-shell__deck-link" href={item.href}>
                      {item.label}
                    </a>
                  ))}
                </div>
              </div>
            ) : null}
            {shortcuts.length > 0 ? (
              <div className="agent-shell__deck-block">
                <p className="agent-shell__deck-kicker">Operator shortcuts</p>
                <div className="agent-shell__shortcut-row">
                  {shortcuts.map((shortcut) => {
                    const key = typeof shortcut === 'string'
                      ? shortcut
                      : `${shortcut.label}-${shortcut.href || 'static'}`;
                    return <ShortcutPill key={key} shortcut={shortcut} />;
                  })}
                </div>
              </div>
            ) : null}
          </section>
        ) : null}

        {previewMode ? (
          <section className="agent-shell__notice agent-shell__notice--warning" aria-label="Preview mode notice">
            <strong>Static preview mode:</strong> interactive API-backed panels will not load from <code>file://</code>. Open the running app on <code>http://127.0.0.1:8000/</code> or start the local stack for live data.
          </section>
        ) : null}

        {page.notice ? (
          <section className="agent-shell__notice" aria-label="Workspace note">
            {page.notice}
          </section>
        ) : null}

        {highlights.length > 0 ? (
          <section className="agent-shell__highlights" aria-label="Page highlights">
            {highlights.map((item, index) => (
              <article key={item.title} className="agent-shell__highlight-card agent-shell__tilt">
                <div className="agent-shell__highlight-topline">
                  <span className="agent-shell__highlight-index" aria-hidden="true">0{index + 1}</span>
                  <span className="agent-shell__highlight-kicker">Workspace highlight</span>
                </div>
                <h2 className="agent-shell__highlight-title">{item.title}</h2>
                <p className="agent-shell__highlight-copy">{item.description}</p>
              </article>
            ))}
          </section>
        ) : null}

        {featureGroups.length > 0 ? (
          <section className="agent-shell__feature-stack" aria-label="Expanded workspace features">
            {featureGroups.map((group) => <FeatureGroup key={group.title} group={group} />)}
          </section>
        ) : null}
      </div>
    </div>
  );
}

for (const node of document.querySelectorAll('[data-app-shell]')) {
  const root = createRoot(node);
  root.render(<AppShell page={readProps(node)} />);
}

document.body.classList.add('agent-shell--ready');

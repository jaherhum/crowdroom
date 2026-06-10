import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

function makeMatchMedia(prefersDark) {
  const listeners = new Set();
  const mql = {
    matches: prefersDark,
    media: '(prefers-color-scheme: dark)',
    addEventListener: (_event, cb) => listeners.add(cb),
    removeEventListener: (_event, cb) => listeners.delete(cb),
    dispatch(matches) {
      this.matches = matches;
      listeners.forEach((cb) => cb({ matches }));
    },
  };
  const matchMedia = vi.fn(() => mql);
  return { matchMedia, mql };
}

async function loadComposable({ stored = null, prefersDark = false } = {}) {
  vi.resetModules();
  localStorage.clear();
  if (stored !== null) localStorage.setItem('theme', stored);
  document.documentElement.removeAttribute('data-theme');
  const { matchMedia, mql } = makeMatchMedia(prefersDark);
  vi.stubGlobal('matchMedia', matchMedia);
  window.matchMedia = matchMedia;
  const mod = await import('./useTheme.js');
  return { useTheme: mod.useTheme, mql };
}

describe('useTheme', () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.removeAttribute('data-theme');
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('uses stored theme when present, ignoring OS preference', async () => {
    const { useTheme } = await loadComposable({ stored: 'dark', prefersDark: false });
    const { theme } = useTheme();
    expect(theme.value).toBe('dark');
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
  });

  it('falls back to prefers-color-scheme: dark when no stored value', async () => {
    const { useTheme } = await loadComposable({ stored: null, prefersDark: true });
    const { theme } = useTheme();
    expect(theme.value).toBe('dark');
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
  });

  it('falls back to light when no stored value and OS prefers light', async () => {
    const { useTheme } = await loadComposable({ stored: null, prefersDark: false });
    const { theme } = useTheme();
    expect(theme.value).toBe('light');
    expect(document.documentElement.getAttribute('data-theme')).toBe('light');
  });

  it('toggleTheme persists to localStorage and applies to documentElement', async () => {
    const { useTheme } = await loadComposable({ stored: 'light', prefersDark: false });
    const { theme, toggleTheme } = useTheme();
    toggleTheme();
    expect(theme.value).toBe('dark');
    expect(localStorage.getItem('theme')).toBe('dark');
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
    toggleTheme();
    expect(theme.value).toBe('light');
    expect(localStorage.getItem('theme')).toBe('light');
    expect(document.documentElement.getAttribute('data-theme')).toBe('light');
  });

  it('reacts to OS preference changes only when no manual override', async () => {
    const { useTheme, mql } = await loadComposable({ stored: null, prefersDark: false });
    const { theme } = useTheme();
    expect(theme.value).toBe('light');
    mql.dispatch(true);
    expect(theme.value).toBe('dark');
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
  });

  it('ignores OS preference changes once a manual override is stored', async () => {
    const { useTheme, mql } = await loadComposable({ stored: 'light', prefersDark: false });
    const { theme } = useTheme();
    mql.dispatch(true);
    expect(theme.value).toBe('light');
    expect(document.documentElement.getAttribute('data-theme')).toBe('light');
  });
});

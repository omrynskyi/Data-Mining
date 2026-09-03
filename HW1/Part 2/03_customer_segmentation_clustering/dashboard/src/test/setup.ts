import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach, vi } from 'vitest';

/**
 * JSDOM has no layout engine, so Recharts' ResponsiveContainer would measure 0x0 and
 * skip rendering its SVG. Reporting a fixed box lets the real charts mount and be
 * asserted on, which is what the acceptance criteria require.
 */
const CHART_WIDTH = 800;
const CHART_HEIGHT = 400;

class ResizeObserverStub {
  private readonly callback: ResizeObserverCallback;

  constructor(callback: ResizeObserverCallback) {
    this.callback = callback;
  }

  observe(target: Element): void {
    const entry = {
      target,
      contentRect: {
        width: CHART_WIDTH,
        height: CHART_HEIGHT,
        top: 0,
        left: 0,
        bottom: CHART_HEIGHT,
        right: CHART_WIDTH,
        x: 0,
        y: 0,
        toJSON: () => ({}),
      },
    } as unknown as ResizeObserverEntry;
    this.callback([entry], this as unknown as ResizeObserver);
  }

  unobserve(): void {}

  disconnect(): void {}
}

vi.stubGlobal('ResizeObserver', ResizeObserverStub);

Object.defineProperty(HTMLElement.prototype, 'offsetWidth', {
  configurable: true,
  value: CHART_WIDTH,
});

Object.defineProperty(HTMLElement.prototype, 'offsetHeight', {
  configurable: true,
  value: CHART_HEIGHT,
});

Object.defineProperty(HTMLElement.prototype, 'getBoundingClientRect', {
  configurable: true,
  value: () => ({
    width: CHART_WIDTH,
    height: CHART_HEIGHT,
    top: 0,
    left: 0,
    bottom: CHART_HEIGHT,
    right: CHART_WIDTH,
    x: 0,
    y: 0,
    toJSON: () => ({}),
  }),
});

if (!window.matchMedia) {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: (query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    }),
  });
}

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

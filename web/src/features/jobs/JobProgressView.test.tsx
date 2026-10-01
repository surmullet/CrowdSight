import { describe, it, expect, vi, beforeAll, afterAll } from 'vitest';
import { render, screen } from '@testing-library/react';
import { JobProgressView } from './JobProgressView';

// Mock EventSource for Vitest jsdom
class MockEventSource {
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: (() => void) | null = null;
  close() {}
}

beforeAll(() => {
  global.EventSource = MockEventSource as unknown as typeof global.EventSource;
});

afterAll(() => {
  // cleanup
});

describe('JobProgressView', () => {
  it('renders initial job progress and running quality counts', () => {
    render(
      <JobProgressView
        sessionId="sess-test-123"
        initialData={{
          sessionId: 'sess-test-123',
          mediaName: 'test_crowd.mp4',
          status: 'RUNNING',
          progress: 0.45,
          currentFrame: 450,
          totalFrames: 1000,
          fps: 18.2,
          etaSeconds: 30,
          qualityCounts: { valid: 380, partial: 50, unknown: 20, stale: 0 },
        }}
        onComplete={vi.fn()}
        onOpenPartialResults={vi.fn()}
        onBackToLibrary={vi.fn()}
      />
    );

    expect(screen.getByText('45%')).toBeInTheDocument();
    expect(screen.getByText(/450 \/ 1000/i)).toBeInTheDocument();
    expect(screen.getByText('380')).toBeInTheDocument();
    expect(screen.getByText('50')).toBeInTheDocument();
    expect(screen.getByText('20')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Hủy phân tích/i })).toBeInTheDocument();
  });
});

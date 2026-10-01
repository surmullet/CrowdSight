import { describe, it, expect, vi, beforeAll } from 'vitest';
import { render } from '@testing-library/react';
import { AnnotatedPlayer } from './AnnotatedPlayer';

beforeAll(() => {
  // Mock ResizeObserver for jsdom
  global.ResizeObserver = class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof global.ResizeObserver;

  // Mock HTMLMediaElement functions
  window.HTMLMediaElement.prototype.play = vi.fn().mockResolvedValue(undefined);
  window.HTMLMediaElement.prototype.pause = vi.fn();
});

describe('AnnotatedPlayer', () => {
  it('renders video and canvas elements with proper attributes', () => {
    const { container } = render(
      <AnnotatedPlayer
        videoSrc="/test.mp4"
        imageWidth={1920}
        imageHeight={1080}
        zones={[]}
        observation={null}
      />
    );

    const video = container.querySelector('video');
    const canvas = container.querySelector('canvas');

    expect(video).toBeInTheDocument();
    expect(video).toHaveAttribute('src', '/test.mp4');
    expect(canvas).toBeInTheDocument();
  });
});

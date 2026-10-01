import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ZoneEditor } from './ZoneEditor';

describe('ZoneEditor', () => {
  it('renders zone editor studio and SVG canvas', () => {
    render(
      <ZoneEditor
        imageWidth={1920}
        imageHeight={1080}
        sampleFrameUrl="/test-frame.png"
        onSave={vi.fn()}
        onCancel={vi.fn()}
      />
    );

    expect(screen.getByText('Trình soạn thảo tập vùng quan sát')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Khu vực A')).toBeInTheDocument();
    expect(screen.getByText('Hình học hợp lệ')).toBeInTheDocument();
  });

  it('renders interactive edge lines and vertex circles', () => {
    const initialZones = [
      {
        zoneId: 'z1',
        name: 'Zone 1',
        color: '#0072B2',
        vertices: [
          [100, 100],
          [300, 100],
          [300, 300],
          [100, 300],
        ] as [number, number][],
      },
    ];

    render(
      <ZoneEditor
        imageWidth={1920}
        imageHeight={1080}
        initialZones={initialZones}
        sampleFrameUrl="/test-frame.png"
        onSave={vi.fn()}
        onCancel={vi.fn()}
      />
    );

    expect(screen.getByText('4 đỉnh')).toBeInTheDocument();
  });
});

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
});

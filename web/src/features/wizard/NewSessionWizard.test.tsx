import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { NewSessionWizard } from './NewSessionWizard';

const mockCatalog = [
  {
    id: 'm1',
    name: 'plaza_cam.mp4',
    duration: 60,
    fps: 30,
    width: 1920,
    height: 1080,
    codec: 'h264',
    browserPlayable: true,
  },
];

const mockZoneSets = [
  {
    id: 'z1',
    name: 'Zone Set 1',
    version: 1,
    zoneCount: 2,
  },
];

const mockProfile = {
  profileId: 'crowd_best_local_v2',
  profileSha256: 'abc123profile',
  checkpointSha256: 'def456checkpoint',
  applicabilityStatus: 'EXPERIMENTAL_NO_APPROVAL',
  operationalAlertsAllowed: false,
};

describe('NewSessionWizard', () => {
  it('steps through wizard and displays model identity', () => {
    const onSubmit = vi.fn();
    render(
      <NewSessionWizard
        mediaCatalog={mockCatalog}
        zoneSets={mockZoneSets}
        modelProfile={mockProfile}
        onSubmit={onSubmit}
        onCancel={vi.fn()}
      />
    );

    // Step 1: Media select
    expect(screen.getByText(/Bước 1: Chọn video/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Tiếp tục/i }));

    // Step 2: Zone set select
    expect(screen.getByText(/Bước 2: Chọn tập vùng/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Tiếp tục/i }));

    // Step 3: Model and applicability
    expect(screen.getByText(/Bước 3: Danh tính mô hình/i)).toBeInTheDocument();
    expect(screen.getByText('crowd_best_local_v2')).toBeInTheDocument();
    expect(screen.getByText('EXPERIMENTAL_NO_APPROVAL')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Tiếp tục/i }));

    // Step 4: Options & Submit
    expect(screen.getByText(/Bước 4: Tùy chọn xử lý/i)).toBeInTheDocument();
    const submitBtn = screen.getByRole('button', { name: /Bắt đầu phân tích/i });
    expect(submitBtn).toBeInTheDocument();
  });
});

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { SessionLibrary, type SessionSummaryItem } from './SessionLibrary';

const mockSessions: SessionSummaryItem[] = [
  {
    id: 'sess-001',
    sourceId: 'med-01',
    mediaName: 'test_gate_video.mp4',
    duration: 60,
    status: 'COMPLETED',
    progress: 1.0,
    synthetic: false,
    createdAt: '2026-09-30 10:00:00',
    zoneSetName: 'Khu vực chính',
  },
  {
    id: 'sess-002',
    sourceId: 'med-02',
    mediaName: 'another_camera.mp4',
    duration: 120,
    status: 'RUNNING',
    progress: 0.5,
    synthetic: true,
    createdAt: '2026-09-30 10:30:00',
  },
];

describe('SessionLibrary', () => {
  it('renders session cards with titles and status badges', () => {
    render(
      <SessionLibrary
        sessions={mockSessions}
        onSelectSession={vi.fn()}
        onNewSession={vi.fn()}
        onDeleteSession={vi.fn()}
      />
    );

    expect(screen.getByText('test_gate_video.mp4')).toBeInTheDocument();
    expect(screen.getByText('another_camera.mp4')).toBeInTheDocument();
    expect(screen.getByText('Mô phỏng')).toBeInTheDocument();
  });

  it('filters sessions by search term', () => {
    render(
      <SessionLibrary
        sessions={mockSessions}
        onSelectSession={vi.fn()}
        onNewSession={vi.fn()}
        onDeleteSession={vi.fn()}
      />
    );

    const searchInput = screen.getByPlaceholderText(/Tìm theo tên video/i);
    fireEvent.change(searchInput, { target: { value: 'gate' } });

    expect(screen.getByText('test_gate_video.mp4')).toBeInTheDocument();
    expect(screen.queryByText('another_camera.mp4')).not.toBeInTheDocument();
  });

  it('opens delete confirmation modal with artifact warning', () => {
    render(
      <SessionLibrary
        sessions={mockSessions}
        onSelectSession={vi.fn()}
        onNewSession={vi.fn()}
        onDeleteSession={vi.fn()}
      />
    );

    const deleteBtns = screen.getAllByTitle('Xóa phiên phân tích');
    fireEvent.click(deleteBtns[0]!);

    expect(screen.getByText('Xác nhận xóa phiên phân tích')).toBeInTheDocument();
    expect(screen.getByText(/toàn bộ tệp kết quả/i)).toBeInTheDocument();
  });
});

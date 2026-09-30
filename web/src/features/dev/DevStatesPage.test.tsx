import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { DevStatesPage } from './DevStatesPage';

describe('DevStatesPage and State Invariant Renderers', () => {
  it('renders all 6 fixture sections truthfully', () => {
    render(<DevStatesPage />);

    // 1. VALID with count > 0
    expect(screen.getByText(/1\. Khung hình VALID \(Có người nhìn thấy\)/i)).toBeInTheDocument();
    expect(screen.getByText('14')).toBeInTheDocument();
    expect(screen.getAllByText('người nhìn thấy').length).toBeGreaterThan(0);

    // 2. VALID with count = 0
    expect(screen.getByText(/2\. Khung hình VALID \(0 người nhìn thấy\)/i)).toBeInTheDocument();
    expect(
      screen.getAllByText('người được nhìn thấy — vùng đã quan sát đầy đủ').length
    ).toBeGreaterThan(0);

    // 3. PARTIAL unobserved zone
    expect(screen.getByText(/3\. Khung hình PARTIAL/i)).toBeInTheDocument();
    expect(
      screen.getByText('Chưa quan sát đầy đủ vùng này')
    ).toBeInTheDocument();

    // 4. UNKNOWN frame
    expect(screen.getByText(/4\. Khung hình UNKNOWN/i)).toBeInTheDocument();
    expect(
      screen.getAllByText('Không có số liệu đáng tin cậy ở khung hình này').length
    ).toBeGreaterThan(0);

    // 5. STALE frame
    expect(screen.getByText(/5\. Khung hình STALE/i)).toBeInTheDocument();
    expect(
      screen.getByText(/Số liệu đã cũ \(cách 4\.8s\)/i)
    ).toBeInTheDocument();

    // 6. Tracked frame
    expect(screen.getByText(/6\. Khung hình Tracked/i)).toBeInTheDocument();
  });

  it('strictly forbids prohibited terms in all rendered cards', () => {
    const { container } = render(<DevStatesPage />);
    const textContent = container.textContent?.toLowerCase() || '';

    // Invariant: Prohibited words
    expect(textContent).not.toContain('sức chứa');
    expect(textContent).not.toContain('độ đông');
    expect(textContent).not.toContain('attendance');
  });

  it('supports language switching between Vietnamese and English', () => {
    render(<DevStatesPage />);

    const langBtn = screen.getByRole('button', { name: /switch to english/i });
    fireEvent.click(langBtn);

    // Should now be in English
    expect(screen.getByText(/1\. VALID Frame \(Visible detections\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Zone not fully observed in this frame/i)).toBeInTheDocument();

    const viBtn = screen.getByRole('button', { name: /đổi sang tiếng việt/i });
    fireEvent.click(viBtn);
    expect(screen.getByText(/1\. Khung hình VALID \(Có người nhìn thấy\)/i)).toBeInTheDocument();
  });

  it('opens and closes the semantics modal explaining measurement limitations', () => {
    render(<DevStatesPage />);

    const semanticsBtn = screen.getByRole('button', { name: /về phép đo này/i });
    fireEvent.click(semanticsBtn);

    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText(/1\. Định nghĩa số đo/i)).toBeInTheDocument();

    const closeBtn = screen.getByRole('button', { name: /đã hiểu/i });
    fireEvent.click(closeBtn);

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });
});

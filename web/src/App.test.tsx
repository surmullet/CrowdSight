import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import App from './App';

describe('App Navigation and History Back behavior', () => {
  beforeEach(() => {
    // Reset location and history
    window.history.replaceState(null, '', '/');
    vi.restoreAllMocks();
  });

  it('navigates to session review when "Xem kết quả" is clicked and can navigate back', async () => {
    render(<App />);

    // Verify initially on sessions view
    expect(screen.getByText('Thư viện phiên phân tích')).toBeInTheDocument();

    // Find and click on the "Xem kết quả" button of the session
    const viewButtons = screen.getAllByRole('button', { name: /Xem kết quả/i });
    fireEvent.click(viewButtons[0]!);

    // Should now be on Review workspace
    const backBtn = await screen.findByTitle('Quay lại danh sách phiên');
    expect(backBtn).toBeInTheDocument();
    expect(window.history.state?.view).toBe('review');

    // Click the in-app Back button
    fireEvent.click(backBtn);

    // Should return to sessions view
    expect(screen.getByText('Thư viện phiên phân tích')).toBeInTheDocument();
  });

  it('supports browser back button (popstate) to return to sessions from review', async () => {
    render(<App />);

    // Click on session view button
    const viewButtons = screen.getAllByRole('button', { name: /Xem kết quả/i });
    fireEvent.click(viewButtons[0]!);
    expect(await screen.findByTitle('Quay lại danh sách phiên')).toBeInTheDocument();

    // Simulate browser Back button (popstate event)
    window.history.pushState({ view: 'sessions', sessionId: null }, '', '/?view=sessions');
    fireEvent(window, new PopStateEvent('popstate', { state: { view: 'sessions', sessionId: null } }));

    // App should handle popstate and display Sessions Library instead of exiting
    expect(await screen.findByText('Thư viện phiên phân tích')).toBeInTheDocument();
  });

  it('supports in-app back from NewSessionWizard on Step 1 to return to sessions', async () => {
    render(<App />);

    // Open Wizard
    const newSessionTab = screen.getByRole('button', { name: /Tạo phiên/i });
    fireEvent.click(newSessionTab);

    // Verify Wizard is open
    expect(screen.getByText('Khởi tạo phiên phân tích mới')).toBeInTheDocument();

    // Click on header back button
    const headerBackBtn = screen.getByTitle('Quay lại danh sách phiên');
    fireEvent.click(headerBackBtn);

    // Should be back on sessions library
    expect(screen.getByText('Thư viện phiên phân tích')).toBeInTheDocument();
  });

  it('supports in-app back from Model Status page to return to sessions', async () => {
    render(<App />);

    // Go to Model page
    const modelTab = screen.getByRole('button', { name: /Mô hình/i });
    fireEvent.click(modelTab);

    expect(screen.getByText(/Mô hình & Tình trạng sử dụng/i)).toBeInTheDocument();

    // Click on Back button
    const backBtn = screen.getByTitle('Quay lại');
    fireEvent.click(backBtn);

    // Should be back on sessions library
    expect(screen.getByText('Thư viện phiên phân tích')).toBeInTheDocument();
  });
});

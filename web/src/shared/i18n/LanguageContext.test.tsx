import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import { LanguageProvider, useLanguage } from './LanguageContext';
import { Banner } from '@/shared/ui/Banner';

const TestConsumer: React.FC = () => {
  const { locale, toggleLocale, t } = useLanguage();
  return (
    <div>
      <span data-testid="locale">{locale}</span>
      <span data-testid="title">{t.nav.sessions}</span>
      <button onClick={toggleLocale}>Toggle</button>
      <Banner />
    </div>
  );
};

describe('LanguageContext', () => {
  it('defaults to Vietnamese and switches to English on toggle', () => {
    render(
      <LanguageProvider>
        <TestConsumer />
      </LanguageProvider>
    );

    expect(screen.getByTestId('locale').textContent).toBe('vi');
    expect(screen.getByTestId('title').textContent).toBe('Thư viện');
    expect(screen.getByText(/Thử nghiệm — chưa được duyệt/i)).toBeInTheDocument();

    // Toggle language
    fireEvent.click(screen.getByText('Toggle'));

    expect(screen.getByTestId('locale').textContent).toBe('en');
    expect(screen.getByTestId('title').textContent).toBe('Library');
    expect(screen.getByText(/Experimental — not approved/i)).toBeInTheDocument();

    // Toggle back
    fireEvent.click(screen.getByText('Toggle'));
    expect(screen.getByTestId('locale').textContent).toBe('vi');
    expect(screen.getByTestId('title').textContent).toBe('Thư viện');
  });
});

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ModelStatusPage } from './ModelStatusPage';

describe('ModelStatusPage', () => {
  it('renders model profile id and hashes', () => {
    render(
      <ModelStatusPage
        modelProfileId="crowd_best_local_v2"
        modelProfileSha256="hash-profile-123"
        checkpointSha256="hash-checkpoint-456"
        applicabilityStatus="EXPERIMENTAL_NO_APPROVAL"
        operationalAlertsAllowed={false}
      />
    );

    expect(screen.getByText('crowd_best_local_v2')).toBeInTheDocument();
    expect(screen.getByText('hash-profile-123')).toBeInTheDocument();
    expect(screen.getByText('hash-checkpoint-456')).toBeInTheDocument();
  });

  it('renders locked operational alerts banner with no enable button', () => {
    render(
      <ModelStatusPage
        modelProfileId="crowd_best_local_v2"
        modelProfileSha256="hash-profile-123"
        checkpointSha256="hash-checkpoint-456"
        applicabilityStatus="EXPERIMENTAL_NO_APPROVAL"
        operationalAlertsAllowed={false}
      />
    );

    expect(screen.getByText(/Cảnh báo vận hành: ĐANG TẮT HOÀN TOÀN/i)).toBeInTheDocument();
    expect(screen.getByText('KHÓA (FAIL-CLOSED)')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Bật cảnh báo/i })).not.toBeInTheDocument();
  });
});

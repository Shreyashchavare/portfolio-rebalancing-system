import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import App from '@/App';

describe('Application Root & Providers', () => {
  it('mounts the application successfully and displays the branding', () => {
    render(<App />);
    const brandElements = screen.getAllByText(/YOTTAFLEX/i);
    expect(brandElements.length).toBeGreaterThan(0);
    expect(brandElements[0]).toBeInTheDocument();
    expect(screen.getByText(/Rebalancing Core/i)).toBeInTheDocument();
    expect(screen.getByText(/Financial Overview/i)).toBeInTheDocument();
  });
});

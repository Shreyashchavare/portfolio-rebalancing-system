import { describe, it, expect } from 'vitest';
import { screen } from '@testing-library/react';
import { renderWithProviders } from './test-utils';
import { WorkflowsPage } from '@/features/workflows/WorkflowsPage';

describe('Workflow Orchestration & Human Review Gate (TDD)', () => {
  it('renders workflow orchestration header and agentic state machine badge', () => {
    renderWithProviders(<WorkflowsPage />);

    expect(screen.getByText('Workflow Orchestration & State Monitoring')).toBeInTheDocument();
    expect(screen.getByText('AGENTIC STATE MACHINE')).toBeInTheDocument();
  });

  it('renders execution state machine pipeline with all 7 progression stages', () => {
    renderWithProviders(<WorkflowsPage />);

    expect(screen.getByText('Execution State Machine Transition Pipeline')).toBeInTheDocument();
    expect(screen.getByText('1. Received')).toBeInTheDocument();
    expect(screen.getByText('2. Validating')).toBeInTheDocument();
    expect(screen.getByText('3. Drift Analysis')).toBeInTheDocument();
    expect(screen.getByText('4. Proposal & Fees')).toBeInTheDocument();
    expect(screen.getByText('5. FastEmbed RAG')).toBeInTheDocument();
    expect(screen.getByText('6. Grounded Summary')).toBeInTheDocument();
    expect(screen.getByText('7. Human Review')).toBeInTheDocument();
  });

  it('renders Recent Workflow Runs table with workflow ID and proposal link', () => {
    renderWithProviders(<WorkflowsPage />);

    expect(screen.getByText('Recent Workflow Runs')).toBeInTheDocument();
    expect(screen.getByText('WF-20260115-A1B2C3D4')).toBeInTheDocument();
    const proposalMatches = screen.getAllByText('RB-2026-000002');
    expect(proposalMatches.length).toBeGreaterThanOrEqual(1);
  });
});

/**
 * @vitest-environment jsdom
 */
/**
 * ReviewMetrics Component Tests
 *
 * Tests the review metrics component functionality including:
 * - Rendering metrics grid
 * - Duration formatting
 * - In-progress state
 * - No data state
 * - i18n translations
 */
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import '../../../../../shared/i18n';
import { ReviewMetrics } from '../ReviewMetrics';
import type { ReviewMetrics as ReviewMetricsType } from '../../../../../shared/types';

describe('ReviewMetrics', () => {
  const mockMetrics: ReviewMetricsType = {
    cycleTime: 86400000, // 1 day in milliseconds
    iterationCount: 3,
    timeToApproval: 3600000, // 1 hour in milliseconds
    reviewerResponseTime: 1800000, // 30 minutes in milliseconds
    reviewStartedAt: '2024-01-01T00:00:00Z',
    approvedAt: '2024-01-02T00:00:00Z',
  };

  const mockInProgressMetrics: ReviewMetricsType = {
    cycleTime: 0,
    iterationCount: 2,
    timeToApproval: 0,
    reviewerResponseTime: 0,
    reviewStartedAt: '2024-01-01T00:00:00Z',
    approvedAt: undefined,
  };

  it('should render metrics grid with all metrics', () => {
    render(<ReviewMetrics metrics={mockMetrics} />);

    // Check for metric labels using flexible matching
    expect(screen.getByText(/cycle.*time/i)).toBeInTheDocument();
    expect(screen.getByText(/iteration/i)).toBeInTheDocument();
    expect(screen.getByText(/time.*approval/i)).toBeInTheDocument();
    expect(screen.getByText(/response.*time/i)).toBeInTheDocument();
  });

  it('should format duration correctly - days', () => {
    const metricsWithDays: ReviewMetricsType = {
      ...mockMetrics,
      cycleTime: 172800000, // 2 days
    };

    render(<ReviewMetrics metrics={metricsWithDays} />);

    // Should show "2 days" or similar
    expect(screen.getByText(/2.*day/i)).toBeInTheDocument();
  });

  it('should format duration correctly - hours', () => {
    const metricsWithHours: ReviewMetricsType = {
      ...mockMetrics,
      cycleTime: 7200000, // 2 hours
    };

    render(<ReviewMetrics metrics={metricsWithHours} />);

    // Should show "2 hours" or similar
    expect(screen.getByText(/2.*hour/i)).toBeInTheDocument();
  });

  it('should format duration correctly - minutes', () => {
    const metricsWithMinutes: ReviewMetricsType = {
      ...mockMetrics,
      cycleTime: 300000, // 5 minutes
    };

    render(<ReviewMetrics metrics={metricsWithMinutes} />);

    // Should show "5 minutes" or similar
    expect(screen.getByText(/5.*minute/i)).toBeInTheDocument();
  });

  it('should show "In progress" for active reviews without approval', () => {
    render(<ReviewMetrics metrics={mockInProgressMetrics} />);

    expect(screen.getByText(/in progress/i)).toBeInTheDocument();
  });

  it('should show "No data" state when metrics is null', () => {
    const { container } = render(<ReviewMetrics metrics={undefined} />);

    expect(container).toBeEmptyDOMElement();
  });

  it('should show "No data" message when no metrics available', () => {
    const emptyMetrics: ReviewMetricsType = {
      cycleTime: 0,
      iterationCount: 0,
      timeToApproval: 0,
      reviewerResponseTime: 0,
      reviewStartedAt: undefined,
      approvedAt: undefined,
    };

    render(<ReviewMetrics metrics={emptyMetrics} />);

    expect(screen.getByText(/no metrics available/i)).toBeInTheDocument();
  });

  it('should display all four metric types', () => {
    render(<ReviewMetrics metrics={mockMetrics} />);

    // Should have cycle time, iterations, time to approval, and response time
    const metricItems = screen.getAllByRole('generic').filter(
      (el) => el.className.includes('rounded-lg') && el.className.includes('border')
    );

    // Should have at least 4 metric items
    expect(metricItems.length).toBeGreaterThanOrEqual(4);
  });

  it('should use i18n translations', () => {
    render(<ReviewMetrics metrics={mockMetrics} />);

    // Component should render without errors
    expect(screen.getByText(/cycle.*time/i)).toBeInTheDocument();
  });

  it('should display iteration count as a number', () => {
    render(<ReviewMetrics metrics={mockMetrics} />);

    // Should show "3" for iteration count
    expect(screen.getByText('3')).toBeInTheDocument();
  });
});

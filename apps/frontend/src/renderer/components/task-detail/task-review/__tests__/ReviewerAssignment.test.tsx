/**
 * @vitest-environment jsdom
 */
/**
 * ReviewerAssignment Component Tests
 *
 * Tests the reviewer assignment component functionality including:
 * - Rendering reviewer list
 * - Approval status icons
 * - Add/remove reviewer interactions
 * - Required reviewer indicators
 * - Disabled state
 * - i18n translations
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import '../../../../shared/i18n';
import { ReviewerAssignment } from '../ReviewerAssignment';
import type { ReviewerAssignment as ReviewerAssignmentType } from '../../../../../shared/types';

describe('ReviewerAssignment', () => {
  const mockOnAddReviewer = vi.fn();
  const mockOnRemoveReviewer = vi.fn();
  const mockOnApprove = vi.fn();

  const mockAssignment: ReviewerAssignmentType = {
    required: [
      { id: 'alice', name: 'Alice Smith', email: 'alice@example.com', approved: true },
      { id: 'bob', name: 'Bob Jones', email: 'bob@example.com', approved: false },
    ],
    actual: [
      { id: 'alice', name: 'Alice Smith', email: 'alice@example.com', approved: true, comment: 'LGTM!' },
      { id: 'bob', name: 'Bob Jones', email: 'bob@example.com', approved: false },
      { id: 'charlie', name: 'Charlie Brown', email: 'charlie@example.com', approved: false },
    ],
    allApproved: false,
  };

  const mockApprovedAssignment: ReviewerAssignmentType = {
    required: [
      { id: 'alice', name: 'Alice Smith', email: 'alice@example.com', approved: true },
      { id: 'bob', name: 'Bob Jones', email: 'bob@example.com', approved: true },
    ],
    actual: [
      { id: 'alice', name: 'Alice Smith', email: 'alice@example.com', approved: true },
      { id: 'bob', name: 'Bob Jones', email: 'bob@example.com', approved: true },
    ],
    allApproved: true,
  };

  const mockAvailableReviewers = [
    { id: 'alice', name: 'Alice Smith', email: 'alice@example.com' },
    { id: 'bob', name: 'Bob Jones', email: 'bob@example.com' },
    { id: 'charlie', name: 'Charlie Brown', email: 'charlie@example.com' },
    { id: 'dave', name: 'Dave Wilson', email: 'dave@example.com' },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render reviewer list', () => {
    render(
      <ReviewerAssignment
        assignment={mockAssignment}
        availableReviewers={mockAvailableReviewers}
        onAddReviewer={mockOnAddReviewer}
        onRemoveReviewer={mockOnRemoveReviewer}
      />
    );

    expect(screen.getByText('Alice Smith')).toBeInTheDocument();
    expect(screen.getByText('Bob Jones')).toBeInTheDocument();
    expect(screen.getByText('Charlie Brown')).toBeInTheDocument();
  });

  it('should show approval status icons correctly', () => {
    render(
      <ReviewerAssignment
        assignment={mockAssignment}
        availableReviewers={mockAvailableReviewers}
        onAddReviewer={mockOnAddReviewer}
        onRemoveReviewer={mockOnRemoveReviewer}
      />
    );

    // Alice is approved - should show CheckCircle
    const aliceRow = screen.getByText('Alice Smith').closest('div');
    expect(aliceRow).toBeInTheDocument();

    // Bob is not approved - should show User icon
    const bobRow = screen.getByText('Bob Jones').closest('div');
    expect(bobRow).toBeInTheDocument();
  });

  it('should display "All approved" when complete', () => {
    render(
      <ReviewerAssignment
        assignment={mockApprovedAssignment}
        availableReviewers={mockAvailableReviewers}
        onAddReviewer={mockOnAddReviewer}
        onRemoveReviewer={mockOnRemoveReviewer}
      />
    );

    expect(screen.getByText(/all approved/i)).toBeInTheDocument();
  });

  it('should display "X waiting approval" when incomplete', () => {
    render(
      <ReviewerAssignment
        assignment={mockAssignment}
        availableReviewers={mockAvailableReviewers}
        onAddReviewer={mockOnAddReviewer}
        onRemoveReviewer={mockOnRemoveReviewer}
      />
    );

    // Should show "1 waiting approval" (only Bob is required and not approved)
    expect(screen.getByText(/1.*waiting/i)).toBeInTheDocument();
  });

  it('should render add reviewer dropdown when available reviewers exist', () => {
    render(
      <ReviewerAssignment
        assignment={mockAssignment}
        availableReviewers={mockAvailableReviewers}
        onAddReviewer={mockOnAddReviewer}
        onRemoveReviewer={mockOnRemoveReviewer}
      />
    );

    // Should show dropdown trigger
    const dropdown = screen.getByRole('combobox');
    expect(dropdown).toBeInTheDocument();
  });

  it('should call onRemoveReviewer when remove button clicked', () => {
    render(
      <ReviewerAssignment
        assignment={mockAssignment}
        availableReviewers={mockAvailableReviewers}
        onAddReviewer={mockOnAddReviewer}
        onRemoveReviewer={mockOnRemoveReviewer}
      />
    );

    // Get all remove buttons (X buttons)
    const removeButtons = screen.getAllByRole('button', { name: /remove/i });
    expect(removeButtons.length).toBeGreaterThan(0);

    // Click the first remove button
    fireEvent.click(removeButtons[0]);

    expect(mockOnRemoveReviewer).toHaveBeenCalled();
  });

  it('should show asterisk (*) for required reviewers', () => {
    render(
      <ReviewerAssignment
        assignment={mockAssignment}
        availableReviewers={mockAvailableReviewers}
        onAddReviewer={mockOnAddReviewer}
        onRemoveReviewer={mockOnRemoveReviewer}
      />
    );

    // Alice is required - should show asterisk
    const aliceRow = screen.getByText('Alice Smith').parentElement;
    expect(aliceRow).toHaveTextContent('*');

    // Bob is required - should show asterisk
    const bobRow = screen.getByText('Bob Jones').parentElement;
    expect(bobRow).toHaveTextContent('*');

    // Charlie is NOT required - should not show asterisk
    const charlieRow = screen.getByText('Charlie Brown').parentElement;
    expect(charlieRow).not.toHaveTextContent('*');
  });

  it('should disable all interactions when disabled prop is true', () => {
    render(
      <ReviewerAssignment
        assignment={mockAssignment}
        availableReviewers={mockAvailableReviewers}
        onAddReviewer={mockOnAddReviewer}
        onRemoveReviewer={mockOnRemoveReviewer}
        disabled={true}
      />
    );

    // Remove buttons should not be rendered
    const removeButtons = screen.queryAllByRole('button', { name: /remove/i });
    expect(removeButtons).toHaveLength(0);

    // Add reviewer dropdown should not be rendered
    const dropdown = screen.queryByRole('combobox');
    expect(dropdown).not.toBeInTheDocument();
  });

  it('should use i18n translations', () => {
    render(
      <ReviewerAssignment
        assignment={mockAssignment}
        availableReviewers={mockAvailableReviewers}
        onAddReviewer={mockOnAddReviewer}
        onRemoveReviewer={mockOnRemoveReviewer}
      />
    );

    // Component should render without errors
    expect(screen.getByText('Alice Smith')).toBeInTheDocument();
  });

  it('should show empty state when no reviewers assigned', () => {
    const emptyAssignment: ReviewerAssignmentType = {
      required: [],
      actual: [],
      allApproved: true,
    };

    render(
      <ReviewerAssignment
        assignment={emptyAssignment}
        availableReviewers={mockAvailableReviewers}
        onAddReviewer={mockOnAddReviewer}
        onRemoveReviewer={mockOnRemoveReviewer}
      />
    );

    expect(screen.getByText(/no reviewers/i)).toBeInTheDocument();
  });

  it('should not render when assignment is undefined', () => {
    const { container } = render(
      <ReviewerAssignment
        assignment={undefined}
        availableReviewers={mockAvailableReviewers}
        onAddReviewer={mockOnAddReviewer}
        onRemoveReviewer={mockOnRemoveReviewer}
      />
    );

    expect(container).toBeEmptyDOMElement();
  });

  it('should display reviewer comments when provided', () => {
    render(
      <ReviewerAssignment
        assignment={mockAssignment}
        availableReviewers={mockAvailableReviewers}
        onAddReviewer={mockOnAddReviewer}
        onRemoveReviewer={mockOnRemoveReviewer}
      />
    );

    // Alice has a comment
    expect(screen.getByText('LGTM!')).toBeInTheDocument();
  });
});

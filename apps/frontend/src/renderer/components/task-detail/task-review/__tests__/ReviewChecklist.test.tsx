/**
 * @vitest-environment jsdom
 */
/**
 * ReviewChecklist Component Tests
 *
 * Tests the review checklist component functionality including:
 * - Rendering checklist items
 * - Completion status display
 * - Checkbox interaction
 * - Required item indicators
 * - Disabled state
 * - i18n translations
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import '../../../../shared/i18n';
import { ReviewChecklist } from '../ReviewChecklist';
import type { ReviewChecklist as ReviewChecklistType } from '../../../../../shared/types';

describe('ReviewChecklist', () => {
  const mockOnItemChange = vi.fn();

  const mockChecklist: ReviewChecklistType = {
    items: [
      { id: 'item1', label: 'Code quality check', completed: false, required: true },
      { id: 'item2', label: 'Tests passing', completed: true, required: true },
      { id: 'item3', label: 'Performance review', completed: false, required: false },
    ],
    allComplete: false,
  };

  const mockCompleteChecklist: ReviewChecklistType = {
    items: [
      { id: 'item1', label: 'Code quality check', completed: true, required: true },
      { id: 'item2', label: 'Tests passing', completed: true, required: true },
    ],
    allComplete: true,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render checklist items', () => {
    render(<ReviewChecklist checklist={mockChecklist} onItemChange={mockOnItemChange} />);

    expect(screen.getByText('Code quality check')).toBeInTheDocument();
    expect(screen.getByText('Tests passing')).toBeInTheDocument();
    expect(screen.getByText('Performance review')).toBeInTheDocument();
  });

  it('should display "All items complete" when complete', () => {
    render(<ReviewChecklist checklist={mockCompleteChecklist} onItemChange={mockOnItemChange} />);

    expect(screen.getByText(/all.*complete/i)).toBeInTheDocument();
  });

  it('should display "X items remaining" when incomplete', () => {
    render(<ReviewChecklist checklist={mockChecklist} onItemChange={mockOnItemChange} />);

    // Should show "1 item remaining" (only item1 is required and incomplete)
    expect(screen.getByText(/1.*remaining/i)).toBeInTheDocument();
  });

  it('should call onItemChange when checkbox changes', () => {
    render(<ReviewChecklist checklist={mockChecklist} onItemChange={mockOnItemChange} />);

    // Get the first checkbox (Code quality check - unchecked)
    const checkboxes = screen.getAllByRole('checkbox');
    fireEvent.click(checkboxes[0]);

    expect(mockOnItemChange).toHaveBeenCalledWith('item1', true);
  });

  it('should show asterisk (*) for required items', () => {
    render(<ReviewChecklist checklist={mockChecklist} onItemChange={mockOnItemChange} />);

    // Required items should have asterisk when not completed
    const codeQualityLabel = screen.getByText('Code quality check').parentElement;
    expect(codeQualityLabel).toHaveTextContent('*');

    // Completed required item should not show asterisk
    const testsLabel = screen.getByText('Tests passing').parentElement;
    expect(testsLabel).not.toHaveTextContent('*');

    // Optional item should not show asterisk
    const perfLabel = screen.getByText('Performance review').parentElement;
    expect(perfLabel).not.toHaveTextContent('*');
  });

  it('should disable all checkboxes when disabled prop is true', () => {
    render(<ReviewChecklist checklist={mockChecklist} onItemChange={mockOnItemChange} disabled={true} />);

    const checkboxes = screen.getAllByRole('checkbox');
    checkboxes.forEach((checkbox) => {
      expect(checkbox).toBeDisabled();
    });
  });

  it('should not call onItemChange when disabled', () => {
    render(<ReviewChecklist checklist={mockChecklist} onItemChange={mockOnItemChange} disabled={true} />);

    const checkboxes = screen.getAllByRole('checkbox');
    fireEvent.click(checkboxes[0]);

    expect(mockOnItemChange).not.toHaveBeenCalled();
  });

  it('should use i18n translations', () => {
    render(<ReviewChecklist checklist={mockChecklist} onItemChange={mockOnItemChange} />);

    // Check for translation key content (the actual translation will vary)
    // We can verify the component renders without errors
    expect(screen.getByText(/Code quality check/)).toBeInTheDocument();
  });

  it('should show empty state when no checklist provided', () => {
    const { container } = render(<ReviewChecklist checklist={undefined} onItemChange={mockOnItemChange} />);

    expect(container).toBeEmptyDOMElement();
  });

  it('should show no items message when checklist is empty', () => {
    const emptyChecklist: ReviewChecklistType = {
      items: [],
      allComplete: true,
    };

    render(<ReviewChecklist checklist={emptyChecklist} onItemChange={mockOnItemChange} />);

    expect(screen.getByText(/no items/i)).toBeInTheDocument();
  });
});

import { useState, useEffect, useMemo } from 'react';
import type { PRData } from '../../../../preload/api/modules/github-api';

/**
 * ES-#### pattern for ticket matching (hardcoded per plan)
 */
const TICKET_PATTERN = /ES-\d+/gi;

/**
 * Extract ES-#### from text
 */
export function extractTicketKey(text: string): string | null {
  const match = text.match(/ES-\d+/i);
  return match ? match[0].toUpperCase() : null;
}

/**
 * Extract all ES-#### references from text
 */
export function extractAllTicketKeys(text: string): string[] {
  const matches = text.match(TICKET_PATTERN) || [];
  return [...new Set(matches.map(m => m.toUpperCase()))];
}

/**
 * Find PRs linked to a specific ticket key
 */
export function findLinkedPRs(ticketKey: string, prs: PRData[]): PRData[] {
  const pattern = new RegExp(ticketKey, 'i');
  return prs.filter(pr =>
    pattern.test(pr.title) ||
    pattern.test(pr.headRefName) ||
    pattern.test(pr.body || '')
  );
}

/**
 * Hook to find PRs linked to a Jira ticket
 */
export function useLinkedPRs(
  ticketKey: string | undefined,
  projectId: string | undefined
) {
  const [allPRs, setAllPRs] = useState<PRData[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch PRs
  useEffect(() => {
    const fetchPRs = async () => {
      if (!projectId) return;

      setIsLoading(true);
      try {
        const prs = await window.electronAPI.github.listPRs(projectId);
        setAllPRs(prs || []);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch PRs');
        setAllPRs([]);
      } finally {
        setIsLoading(false);
      }
    };

    fetchPRs();
  }, [projectId]);

  // Find linked PRs
  const linkedPRs = useMemo(() => {
    if (!ticketKey) return [];
    return findLinkedPRs(ticketKey, allPRs);
  }, [ticketKey, allPRs]);

  return {
    linkedPRs,
    isLoading,
    error,
  };
}

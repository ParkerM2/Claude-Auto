import { useState, useEffect, useCallback } from 'react';
import type { JiraIssue, JiraSyncStatus } from '../../../../shared/types';

interface UseJiraTicketsOptions {
  isActive?: boolean;
}

interface UseJiraTicketsReturn {
  tickets: JiraIssue[];
  isLoading: boolean;
  error: string | null;
  selectedTicket: JiraIssue | null;
  isConnected: boolean;
  connectionStatus: JiraSyncStatus | null;
  selectTicket: (ticket: JiraIssue | null) => void;
  refresh: () => Promise<void>;
}

export function useJiraTickets(
  projectId: string | undefined,
  options: UseJiraTicketsOptions = {}
): UseJiraTicketsReturn {
  const { isActive = true } = options;

  const [tickets, setTickets] = useState<JiraIssue[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedTicket, setSelectedTicket] = useState<JiraIssue | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<JiraSyncStatus | null>(null);

  const isConnected = connectionStatus?.connected ?? false;

  const checkConnection = useCallback(async () => {
    if (!projectId) return;

    try {
      const result = await window.electronAPI.jira.checkConnection(projectId);
      if (result.success && result.data) {
        setConnectionStatus(result.data);
        setError(result.data.connected ? null : result.data.error || null);
      } else {
        setConnectionStatus({ connected: false, error: result.error });
        setError(result.error || 'Failed to check connection');
      }
    } catch (err) {
      setConnectionStatus({ connected: false, error: 'Failed to check connection' });
      setError(err instanceof Error ? err.message : 'Failed to check connection');
    }
  }, [projectId]);

  const fetchTickets = useCallback(async () => {
    if (!projectId || !isConnected) return;

    setIsLoading(true);
    try {
      const result = await window.electronAPI.jira.getMyIssues(projectId);
      if (result.success && result.data) {
        setTickets(result.data);
        setError(null);
      } else {
        setError(result.error || 'Failed to fetch tickets');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch tickets');
    } finally {
      setIsLoading(false);
    }
  }, [projectId, isConnected]);

  const refresh = useCallback(async () => {
    await checkConnection();
    await fetchTickets();
  }, [checkConnection, fetchTickets]);

  const selectTicket = useCallback((ticket: JiraIssue | null) => {
    setSelectedTicket(ticket);
  }, []);

  // Initial load
  useEffect(() => {
    if (isActive && projectId) {
      checkConnection();
    }
  }, [isActive, projectId, checkConnection]);

  // Fetch tickets when connected
  useEffect(() => {
    if (isActive && isConnected) {
      fetchTickets();
    }
  }, [isActive, isConnected, fetchTickets]);

  return {
    tickets,
    isLoading,
    error,
    selectedTicket,
    isConnected,
    connectionStatus,
    selectTicket,
    refresh,
  };
}

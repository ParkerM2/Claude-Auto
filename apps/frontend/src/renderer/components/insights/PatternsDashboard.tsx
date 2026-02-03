import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { TrendingUp, AlertTriangle, Lightbulb, RefreshCw } from 'lucide-react';
import { Button } from '../ui/button';
import { ScrollArea } from '../ui/scroll-area';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { PatternCard } from './PatternCard';
import { GotchaCard } from './GotchaCard';

interface PatternItem {
  id: string;
  content: string;
  frequency: number;
  lastSeen: string;
}

interface SuggestionItem {
  id: string;
  content: string;
  frequency: number;
  lastSeen: string;
}

interface PatternInsightsData {
  top_patterns: PatternItem[];
  common_gotchas: PatternItem[];
  improvement_suggestions: SuggestionItem[];
  last_updated?: string;
}

interface PatternsDashboardProps {
  projectId: string;
}

/**
 * PatternsDashboard component displays AI-generated insights from memory.
 *
 * Shows three main sections:
 * - Top Patterns: Recurring code patterns learned from sessions
 * - Common Gotchas: Pitfalls and problems to avoid
 * - Improvement Suggestions: Recommendations based on past failures
 *
 * @example
 * ```tsx
 * <PatternsDashboard projectId="my-project" />
 * ```
 */
export function PatternsDashboard({ projectId }: PatternsDashboardProps) {
  const { t } = useTranslation(['insights', 'common']);
  const [isLoading, setIsLoading] = useState(true);
  const [data, setData] = useState<PatternInsightsData | null>(null);
  const [dismissedPatterns, setDismissedPatterns] = useState<Set<string>>(new Set());
  const [dismissedGotchas, setDismissedGotchas] = useState<Set<string>>(new Set());
  const [dismissedSuggestions, setDismissedSuggestions] = useState<Set<string>>(new Set());
  const [actionPending, setActionPending] = useState<string | null>(null);

  // Load dismissed items from localStorage
  useEffect(() => {
    try {
      const storageKey = `patterns-dashboard-dismissed-${projectId}`;
      const stored = localStorage.getItem(storageKey);
      if (stored) {
        const parsed = JSON.parse(stored);
        setDismissedPatterns(new Set(parsed.patterns || []));
        setDismissedGotchas(new Set(parsed.gotchas || []));
        setDismissedSuggestions(new Set(parsed.suggestions || []));
      }
    } catch (error) {
      // Ignore errors loading dismissed items
    }
  }, [projectId]);

  // Save dismissed items to localStorage
  const saveDismissed = (
    patterns: Set<string>,
    gotchas: Set<string>,
    suggestions: Set<string>
  ) => {
    try {
      const storageKey = `patterns-dashboard-dismissed-${projectId}`;
      localStorage.setItem(
        storageKey,
        JSON.stringify({
          patterns: Array.from(patterns),
          gotchas: Array.from(gotchas),
          suggestions: Array.from(suggestions)
        })
      );
    } catch (error) {
      // Ignore errors saving dismissed items
    }
  };

  // Load pattern insights data
  const loadData = async () => {
    setIsLoading(true);
    try {
      const result = await window.electronAPI.getPatternInsights(projectId);
      if (result.success && result.data) {
        // Transform backend data to include IDs (using content hash or index)
        const transformedData = {
          top_patterns: result.data.top_patterns.map((item: { content: string; frequency: number; last_seen: string }, idx: number) => ({
            id: `pattern-${idx}-${item.content.slice(0, 20).replace(/\s/g, '-')}`,
            content: item.content,
            frequency: item.frequency,
            lastSeen: item.last_seen
          })),
          common_gotchas: result.data.common_gotchas.map((item: { content: string; frequency: number; last_seen: string }, idx: number) => ({
            id: `gotcha-${idx}-${item.content.slice(0, 20).replace(/\s/g, '-')}`,
            content: item.content,
            frequency: item.frequency,
            lastSeen: item.last_seen
          })),
          improvement_suggestions: result.data.improvement_suggestions.map((item: { content: string; frequency: number; last_seen: string }, idx: number) => ({
            id: `suggestion-${idx}-${item.content.slice(0, 20).replace(/\s/g, '-')}`,
            content: item.content,
            frequency: item.frequency,
            lastSeen: item.last_seen
          })),
          last_updated: result.data.last_updated
        };
        setData(transformedData);
      } else {
        // Set empty data if API call failed
        setData({
          top_patterns: [],
          common_gotchas: [],
          improvement_suggestions: [],
          last_updated: new Date().toISOString()
        });
      }
    } catch (error) {
      // Handle error by setting empty data
      setData({
        top_patterns: [],
        common_gotchas: [],
        improvement_suggestions: [],
        last_updated: new Date().toISOString()
      });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [projectId]);

  const handleDismissPattern = (id: string) => {
    setActionPending(id);
    const newDismissed = new Set(dismissedPatterns);
    newDismissed.add(id);
    setDismissedPatterns(newDismissed);
    saveDismissed(newDismissed, dismissedGotchas, dismissedSuggestions);
    setActionPending(null);
  };

  const handleConfirmPattern = (id: string) => {
    setActionPending(id);
    // Remove from dismissed if it was dismissed
    const newDismissed = new Set(dismissedPatterns);
    newDismissed.delete(id);
    setDismissedPatterns(newDismissed);
    saveDismissed(newDismissed, dismissedGotchas, dismissedSuggestions);
    setActionPending(null);
  };

  const handleDismissGotcha = (id: string) => {
    setActionPending(id);
    const newDismissed = new Set(dismissedGotchas);
    newDismissed.add(id);
    setDismissedGotchas(newDismissed);
    saveDismissed(dismissedPatterns, newDismissed, dismissedSuggestions);
    setActionPending(null);
  };

  const handleConfirmGotcha = (id: string) => {
    setActionPending(id);
    const newDismissed = new Set(dismissedGotchas);
    newDismissed.delete(id);
    setDismissedGotchas(newDismissed);
    saveDismissed(dismissedPatterns, newDismissed, dismissedSuggestions);
    setActionPending(null);
  };

  const handleDismissSuggestion = (id: string) => {
    setActionPending(id);
    const newDismissed = new Set(dismissedSuggestions);
    newDismissed.add(id);
    setDismissedSuggestions(newDismissed);
    saveDismissed(dismissedPatterns, dismissedGotchas, newDismissed);
    setActionPending(null);
  };

  const handleConfirmSuggestion = (id: string) => {
    setActionPending(id);
    const newDismissed = new Set(dismissedSuggestions);
    newDismissed.delete(id);
    setDismissedSuggestions(newDismissed);
    saveDismissed(dismissedPatterns, dismissedGotchas, newDismissed);
    setActionPending(null);
  };

  const handleRefresh = () => {
    loadData();
  };

  // Filter out dismissed items
  const visiblePatterns = data?.top_patterns.filter((p) => !dismissedPatterns.has(p.id)) || [];
  const visibleGotchas = data?.common_gotchas.filter((g) => !dismissedGotchas.has(g.id)) || [];
  const visibleSuggestions = data?.improvement_suggestions.filter((s) => !dismissedSuggestions.has(s.id)) || [];

  if (isLoading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">
            {t('insights:patterns.loading')}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="shrink-0 border-b border-border p-4 bg-card/50">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold">{t('insights:patterns.title')}</h2>
            <p className="text-sm text-muted-foreground">
              {t('insights:patterns.subtitle')}
            </p>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleRefresh}
            disabled={isLoading}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
            {t('common:actions.refresh')}
          </Button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-4 space-y-6">
        {/* Top Patterns Section */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <TrendingUp className="h-5 w-5 text-primary" />
              {t('insights:patterns.topPatterns')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {visiblePatterns.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-8">
                {t('insights:patterns.noPatterns')}
              </p>
            ) : (
              <ScrollArea className="h-[300px]">
                <div className="space-y-3 pr-4">
                  {visiblePatterns.map((pattern) => (
                    <PatternCard
                      key={pattern.id}
                      content={pattern.content}
                      frequency={pattern.frequency}
                      lastSeen={pattern.lastSeen}
                      onConfirm={() => handleConfirmPattern(pattern.id)}
                      onDismiss={() => handleDismissPattern(pattern.id)}
                      isActionPending={actionPending === pattern.id}
                    />
                  ))}
                </div>
              </ScrollArea>
            )}
          </CardContent>
        </Card>

        {/* Common Gotchas Section */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <AlertTriangle className="h-5 w-5 text-orange-600 dark:text-orange-400" />
              {t('insights:patterns.commonGotchas')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {visibleGotchas.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-8">
                {t('insights:patterns.noGotchas')}
              </p>
            ) : (
              <ScrollArea className="h-[300px]">
                <div className="space-y-3 pr-4">
                  {visibleGotchas.map((gotcha) => (
                    <GotchaCard
                      key={gotcha.id}
                      content={gotcha.content}
                      frequency={gotcha.frequency}
                      lastSeen={gotcha.lastSeen}
                      onConfirm={() => handleConfirmGotcha(gotcha.id)}
                      onDismiss={() => handleDismissGotcha(gotcha.id)}
                      isActionPending={actionPending === gotcha.id}
                    />
                  ))}
                </div>
              </ScrollArea>
            )}
          </CardContent>
        </Card>

        {/* Improvement Suggestions Section */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Lightbulb className="h-5 w-5 text-amber-600 dark:text-amber-400" />
              {t('insights:patterns.improvements')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {visibleSuggestions.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-8">
                {t('insights:patterns.noSuggestions')}
              </p>
            ) : (
              <ScrollArea className="h-[300px]">
                <div className="space-y-3 pr-4">
                  {visibleSuggestions.map((suggestion) => (
                    <PatternCard
                      key={suggestion.id}
                      content={suggestion.content}
                      frequency={suggestion.frequency}
                      lastSeen={suggestion.lastSeen}
                      onConfirm={() => handleConfirmSuggestion(suggestion.id)}
                      onDismiss={() => handleDismissSuggestion(suggestion.id)}
                      isActionPending={actionPending === suggestion.id}
                    />
                  ))}
                </div>
              </ScrollArea>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

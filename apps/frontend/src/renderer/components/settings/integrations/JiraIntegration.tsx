import { useState, useEffect } from 'react';
import { Eye, EyeOff, Loader2, CheckCircle2, AlertCircle, ExternalLink } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../ui/button';
import { Input } from '../../ui/input';
import { Label } from '../../ui/label';
import { Switch } from '../../ui/switch';
import type { ProjectEnvConfig, JiraSyncStatus } from '../../../../shared/types';

interface JiraIntegrationProps {
  envConfig: ProjectEnvConfig | null;
  updateEnvConfig: (updates: Partial<ProjectEnvConfig>) => void;
  projectId: string | undefined;
}

export function JiraIntegration({
  envConfig,
  updateEnvConfig,
  projectId,
}: JiraIntegrationProps) {
  const { t } = useTranslation(['settings', 'common']);
  const [showApiToken, setShowApiToken] = useState(false);
  const [isCheckingConnection, setIsCheckingConnection] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<JiraSyncStatus | null>(null);

  // Check connection when API token is set
  useEffect(() => {
    const checkConnection = async () => {
      if (!projectId || !envConfig?.jiraApiToken || !envConfig?.jiraBaseUrl || !envConfig?.jiraEmail) {
        setConnectionStatus(null);
        return;
      }

      setIsCheckingConnection(true);
      try {
        const result = await window.electronAPI.jira.checkConnection(projectId);
        if (result.success && result.data) {
          setConnectionStatus(result.data);
        } else {
          setConnectionStatus({
            connected: false,
            error: result.error || 'Failed to check connection',
          });
        }
      } catch (err) {
        setConnectionStatus({
          connected: false,
          error: err instanceof Error ? err.message : 'Failed to check connection',
        });
      } finally {
        setIsCheckingConnection(false);
      }
    };

    // Debounce the check
    const timeout = setTimeout(checkConnection, 500);
    return () => clearTimeout(timeout);
  }, [projectId, envConfig?.jiraApiToken, envConfig?.jiraBaseUrl, envConfig?.jiraEmail]);

  if (!envConfig) return null;

  return (
    <div className="space-y-4">
      {/* Enable Toggle */}
      <div className="flex items-center justify-between">
        <div className="space-y-0.5">
          <Label className="font-normal text-foreground">
            {t('settings:jira.enable')}
          </Label>
          <p className="text-xs text-muted-foreground">
            {t('settings:jira.enableDescription')}
          </p>
        </div>
        <Switch
          checked={envConfig.jiraEnabled}
          onCheckedChange={(checked) => updateEnvConfig({ jiraEnabled: checked })}
        />
      </div>

      {envConfig.jiraEnabled && (
        <>
          {/* Base URL */}
          <div className="space-y-2">
            <Label className="text-sm font-medium text-foreground">
              {t('settings:jira.baseUrl')}
            </Label>
            <p className="text-xs text-muted-foreground">
              {t('settings:jira.baseUrlDescription')}
            </p>
            <Input
              type="text"
              placeholder="https://company.atlassian.net"
              value={envConfig.jiraBaseUrl || ''}
              onChange={(e) => updateEnvConfig({ jiraBaseUrl: e.target.value })}
            />
          </div>

          {/* Email */}
          <div className="space-y-2">
            <Label className="text-sm font-medium text-foreground">
              {t('settings:jira.email')}
            </Label>
            <p className="text-xs text-muted-foreground">
              {t('settings:jira.emailDescription')}
            </p>
            <Input
              type="email"
              placeholder="user@company.com"
              value={envConfig.jiraEmail || ''}
              onChange={(e) => updateEnvConfig({ jiraEmail: e.target.value })}
            />
          </div>

          {/* API Token */}
          <div className="space-y-2">
            <Label className="text-sm font-medium text-foreground">
              {t('settings:jira.apiToken')}
            </Label>
            <p className="text-xs text-muted-foreground">
              {t('settings:jira.apiTokenDescription')}{' '}
              <a
                href="https://id.atlassian.com/manage-profile/security/api-tokens"
                target="_blank"
                rel="noopener noreferrer"
                className="text-info hover:underline inline-flex items-center gap-1"
              >
                {t('settings:jira.createToken')}
                <ExternalLink className="h-3 w-3" />
              </a>
            </p>
            <div className="relative">
              <Input
                type={showApiToken ? 'text' : 'password'}
                placeholder="ATATT3xFfGF0..."
                value={envConfig.jiraApiToken || ''}
                onChange={(e) => updateEnvConfig({ jiraApiToken: e.target.value })}
                className="pr-10"
              />
              <button
                type="button"
                onClick={() => setShowApiToken(!showApiToken)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              >
                {showApiToken ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
              </button>
            </div>
          </div>

          {/* Project Key */}
          <div className="space-y-2">
            <Label className="text-sm font-medium text-foreground">
              {t('settings:jira.projectKey')}
            </Label>
            <p className="text-xs text-muted-foreground">
              {t('settings:jira.projectKeyDescription')}
            </p>
            <Input
              type="text"
              placeholder="ES"
              value={envConfig.jiraProjectKey || ''}
              onChange={(e) => updateEnvConfig({ jiraProjectKey: e.target.value.toUpperCase() })}
              className="uppercase"
            />
          </div>

          {/* Connection Status */}
          {(envConfig.jiraApiToken && envConfig.jiraBaseUrl && envConfig.jiraEmail) && (
            <ConnectionStatus
              isChecking={isCheckingConnection}
              connectionStatus={connectionStatus}
            />
          )}
        </>
      )}
    </div>
  );
}

interface ConnectionStatusProps {
  isChecking: boolean;
  connectionStatus: JiraSyncStatus | null;
}

function ConnectionStatus({ isChecking, connectionStatus }: ConnectionStatusProps) {
  const { t } = useTranslation(['settings', 'common']);

  return (
    <div className="rounded-lg border border-border bg-muted/30 p-3">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-foreground">
            {t('settings:jira.connectionStatus')}
          </p>
          <p className="text-xs text-muted-foreground">
            {isChecking
              ? t('common:labels.loading')
              : connectionStatus?.connected
              ? t('settings:jira.connectedAs', { user: connectionStatus.currentUser })
              : connectionStatus?.error || t('settings:jira.notConnected')}
          </p>
        </div>
        {isChecking ? (
          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
        ) : connectionStatus?.connected ? (
          <CheckCircle2 className="h-4 w-4 text-success" />
        ) : (
          <AlertCircle className="h-4 w-4 text-warning" />
        )}
      </div>
    </div>
  );
}

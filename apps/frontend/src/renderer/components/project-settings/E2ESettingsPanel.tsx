import { useTranslation } from 'react-i18next';
import { Globe, Lock, Link, Code2 } from 'lucide-react';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Switch } from '../ui/switch';
import { Separator } from '../ui/separator';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '../ui/select';
import { PasswordInput } from './PasswordInput';
import type { E2ETestingConfig, E2EBrowserMode } from '../../../shared/types';

interface E2ESettingsPanelProps {
  config: E2ETestingConfig;
  onConfigChange: (config: E2ETestingConfig) => void;
  onPasswordChange?: (password: string) => void;
  storedPassword?: string;
}

export function E2ESettingsPanel({
  config,
  onConfigChange,
  onPasswordChange,
  storedPassword = ''
}: E2ESettingsPanelProps) {
  const { t } = useTranslation(['settings']);

  const updateConfig = (updates: Partial<E2ETestingConfig>) => {
    onConfigChange({ ...config, ...updates });
  };

  return (
    <div className="space-y-6">
      {/* Enable E2E Testing */}
      <div className="flex items-center justify-between">
        <div className="space-y-0.5">
          <Label className="font-normal text-foreground">
            {t('e2e.enable')}
          </Label>
          <p className="text-xs text-muted-foreground">
            {t('e2e.enableDescription')}
          </p>
        </div>
        <Switch
          checked={config.enabled}
          onCheckedChange={(checked) => updateConfig({ enabled: checked })}
        />
      </div>

      {config.enabled && (
        <>
          <Separator />

          {/* Browser Mode Selection */}
          <section className="space-y-4">
            <div className="flex items-center gap-2">
              <Globe className="h-4 w-4 text-info" />
              <h4 className="text-sm font-medium text-foreground">
                {t('e2e.browserMode.label')}
              </h4>
            </div>
            <p className="text-xs text-muted-foreground">
              {t('e2e.browserMode.description')}
            </p>
            <Select
              value={config.browserMode}
              onValueChange={(value: E2EBrowserMode) => updateConfig({ browserMode: value })}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="auto">
                  {t('e2e.browserMode.options.auto')}
                </SelectItem>
                <SelectItem value="chrome-devtools">
                  {t('e2e.browserMode.options.chromeDevtools')}
                </SelectItem>
                <SelectItem value="puppeteer">
                  {t('e2e.browserMode.options.puppeteer')}
                </SelectItem>
              </SelectContent>
            </Select>
          </section>

          <Separator />

          {/* Authentication Section */}
          <section className="space-y-4">
            <div className="flex items-center gap-2">
              <Lock className="h-4 w-4 text-info" />
              <h4 className="text-sm font-medium text-foreground">
                {t('e2e.authentication.title')}
              </h4>
            </div>
            <p className="text-xs text-muted-foreground">
              {t('e2e.authentication.description')}
            </p>

            {/* Login URL */}
            <div className="space-y-2">
              <Label className="text-sm font-medium text-foreground">
                {t('e2e.authentication.loginUrl.label')}
              </Label>
              <Input
                type="url"
                placeholder={t('e2e.authentication.loginUrl.placeholder')}
                value={config.loginUrl || ''}
                onChange={(e) => updateConfig({ loginUrl: e.target.value })}
              />
              <p className="text-xs text-muted-foreground">
                {t('e2e.authentication.loginUrl.description')}
              </p>
            </div>

            {/* Username */}
            <div className="space-y-2">
              <Label className="text-sm font-medium text-foreground">
                {t('e2e.authentication.username.label')}
              </Label>
              <Input
                type="text"
                placeholder={t('e2e.authentication.username.placeholder')}
                value={config.loginUsername || ''}
                onChange={(e) => updateConfig({ loginUsername: e.target.value })}
              />
              <p className="text-xs text-muted-foreground">
                {t('e2e.authentication.username.description')}
              </p>
            </div>

            {/* Password */}
            <div className="space-y-2">
              <Label className="text-sm font-medium text-foreground">
                {t('e2e.authentication.password.label')}
              </Label>
              <PasswordInput
                value={storedPassword}
                onChange={(value) => onPasswordChange?.(value)}
                placeholder={t('e2e.authentication.password.placeholder')}
              />
              <p className="text-xs text-muted-foreground">
                {t('e2e.authentication.password.description')}
              </p>
            </div>
          </section>

          <Separator />

          {/* Navigation Section */}
          <section className="space-y-4">
            <div className="flex items-center gap-2">
              <Link className="h-4 w-4 text-info" />
              <h4 className="text-sm font-medium text-foreground">
                {t('e2e.navigation.title')}
              </h4>
            </div>
            <p className="text-xs text-muted-foreground">
              {t('e2e.navigation.description')}
            </p>

            {/* Base URL */}
            <div className="space-y-2">
              <Label className="text-sm font-medium text-foreground">
                {t('e2e.navigation.baseUrl.label')}
              </Label>
              <Input
                type="url"
                placeholder={t('e2e.navigation.baseUrl.placeholder')}
                value={config.baseUrl || ''}
                onChange={(e) => updateConfig({ baseUrl: e.target.value })}
              />
              <p className="text-xs text-muted-foreground">
                {t('e2e.navigation.baseUrl.description')}
              </p>
            </div>

            {/* Post-Login URL */}
            <div className="space-y-2">
              <Label className="text-sm font-medium text-foreground">
                {t('e2e.navigation.postLoginUrl.label')}
              </Label>
              <Input
                type="text"
                placeholder={t('e2e.navigation.postLoginUrl.placeholder')}
                value={config.postLoginUrl || ''}
                onChange={(e) => updateConfig({ postLoginUrl: e.target.value })}
              />
              <p className="text-xs text-muted-foreground">
                {t('e2e.navigation.postLoginUrl.description')}
              </p>
            </div>
          </section>

          <Separator />

          {/* Selectors Section */}
          <section className="space-y-4">
            <div className="flex items-center gap-2">
              <Code2 className="h-4 w-4 text-info" />
              <h4 className="text-sm font-medium text-foreground">
                {t('e2e.selectors.title')}
              </h4>
            </div>
            <p className="text-xs text-muted-foreground">
              {t('e2e.selectors.description')}
            </p>

            {/* Username Selector */}
            <div className="space-y-2">
              <Label className="text-sm font-medium text-foreground">
                {t('e2e.selectors.usernameSelector.label')}
              </Label>
              <Input
                type="text"
                placeholder={t('e2e.selectors.usernameSelector.placeholder')}
                value={config.usernameSelector || ''}
                onChange={(e) => updateConfig({ usernameSelector: e.target.value })}
                className="font-mono text-sm"
              />
              <p className="text-xs text-muted-foreground">
                {t('e2e.selectors.usernameSelector.description')}
              </p>
            </div>

            {/* Password Selector */}
            <div className="space-y-2">
              <Label className="text-sm font-medium text-foreground">
                {t('e2e.selectors.passwordSelector.label')}
              </Label>
              <Input
                type="text"
                placeholder={t('e2e.selectors.passwordSelector.placeholder')}
                value={config.passwordSelector || ''}
                onChange={(e) => updateConfig({ passwordSelector: e.target.value })}
                className="font-mono text-sm"
              />
              <p className="text-xs text-muted-foreground">
                {t('e2e.selectors.passwordSelector.description')}
              </p>
            </div>

            {/* Submit Selector */}
            <div className="space-y-2">
              <Label className="text-sm font-medium text-foreground">
                {t('e2e.selectors.submitSelector.label')}
              </Label>
              <Input
                type="text"
                placeholder={t('e2e.selectors.submitSelector.placeholder')}
                value={config.submitSelector || ''}
                onChange={(e) => updateConfig({ submitSelector: e.target.value })}
                className="font-mono text-sm"
              />
              <p className="text-xs text-muted-foreground">
                {t('e2e.selectors.submitSelector.description')}
              </p>
            </div>
          </section>

          {/* Hints */}
          <div className="rounded-lg border border-info/30 bg-info/5 p-3 mt-4">
            <p className="text-xs text-muted-foreground">
              {t('e2e.hints.qaAgentsOnly')}
            </p>
          </div>
        </>
      )}
    </div>
  );
}

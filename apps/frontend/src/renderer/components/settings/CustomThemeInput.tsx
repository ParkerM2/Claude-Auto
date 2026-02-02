import { Info, AlertCircle, CheckCircle2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { cn } from '../../lib/utils';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';

interface CustomThemeInputProps {
  themeName: string;
  themeCss: string;
  error: string | null;
  onNameChange: (name: string) => void;
  onCssChange: (css: string) => void;
}

/**
 * Custom theme input component for creating themes with CSS from tweakcn.com
 * This is a controlled component used inside the theme creation dialog.
 */
export function CustomThemeInput({
  themeName,
  themeCss,
  error,
  onNameChange,
  onCssChange,
}: CustomThemeInputProps) {
  const { t } = useTranslation(['settings']);

  return (
    <div className="space-y-4">
      {/* Instructions */}
      <div className="rounded-lg border border-border bg-muted/30 p-4">
        <div className="flex items-start gap-2">
          <Info className="h-4 w-4 text-muted-foreground mt-0.5 flex-shrink-0" />
          <div className="space-y-2 text-sm text-muted-foreground">
            <p className="font-medium text-foreground">{t('settings:theme.customTheme.expectedFormat')}</p>
            <ul className="list-disc list-inside space-y-1 text-xs">
              <li>{t('settings:theme.customTheme.formatRequirement1')} <code className="px-1 py-0.5 rounded bg-muted">{t('settings:theme.customTheme.formatRequirement1Code')}</code> {t('settings:theme.customTheme.formatRequirement1Suffix')}</li>
              <li>{t('settings:theme.customTheme.formatRequirement2')} <code className="px-1 py-0.5 rounded bg-muted">{t('settings:theme.customTheme.formatRequirement2Code')}</code> {t('settings:theme.customTheme.formatRequirement2Suffix')}</li>
              <li>{t('settings:theme.customTheme.formatRequirement3')} <code className="px-1 py-0.5 rounded bg-muted">{t('settings:theme.customTheme.formatRequirement3Variables')}</code>{t('settings:theme.customTheme.formatRequirement3Suffix')}</li>
              <li>{t('settings:theme.customTheme.formatRequirement4')}</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Theme Name Input */}
      <div className="space-y-2">
        <Label htmlFor="theme-name" className="text-sm font-medium text-foreground">
          {t('settings:theme.customTheme.themeNameLabel')}
        </Label>
        <input
          id="theme-name"
          type="text"
          value={themeName}
          onChange={(e) => onNameChange(e.target.value)}
          placeholder={t('settings:theme.customTheme.themeNamePlaceholder')}
          className={cn(
            'flex h-10 w-full rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground',
            'placeholder:text-muted-foreground',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:border-primary',
            'disabled:cursor-not-allowed disabled:opacity-50',
            'transition-colors duration-200'
          )}
        />
      </div>

      {/* CSS Input */}
      <div className="space-y-2">
        <Label htmlFor="theme-css" className="text-sm font-medium text-foreground">
          {t('settings:theme.customTheme.themeCssLabel')}
        </Label>
        <Textarea
          id="theme-css"
          value={themeCss}
          onChange={(e) => onCssChange(e.target.value)}
          placeholder={t('settings:theme.customTheme.themeCssPlaceholder')}
          className={cn(
            'min-h-[250px] font-mono text-xs resize-y',
            error && 'border-destructive focus-visible:ring-destructive',
            !error && themeCss.trim() && 'border-green-500/50 focus-visible:ring-green-500/50'
          )}
        />
        {error && (
          <div className="flex items-center gap-2 text-sm text-destructive">
            <AlertCircle className="h-4 w-4" />
            <span>{error}</span>
          </div>
        )}
        {!error && themeCss.trim() && (
          <div className="flex items-center gap-2 text-sm text-green-600 dark:text-green-500">
            <CheckCircle2 className="h-4 w-4" />
            <span>{t('settings:theme.customTheme.successMessage')}</span>
          </div>
        )}
      </div>
    </div>
  );
}

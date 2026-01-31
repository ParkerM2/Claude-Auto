import { useState } from 'react';
import { Palette, AlertCircle, Info, CheckCircle2 } from 'lucide-react';
import { cn } from '../../lib/utils';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { Button } from '../ui/button';
import { useSettingsStore } from '../../stores/settings-store';
import type { AppSettings } from '../../../shared/types';

interface CustomThemeInputProps {
  settings: AppSettings;
  onSettingsChange: (settings: AppSettings) => void;
}

/**
 * Custom theme input component for pasting CSS from tweakcn.com
 * Allows users to define custom color themes by pasting CSS variables
 *
 * Theme changes are applied immediately for live preview, while other settings
 * require saving to take effect.
 */
export function CustomThemeInput({ settings, onSettingsChange }: CustomThemeInputProps) {
  const updateStoreSettings = useSettingsStore((state) => state.updateSettings);
  const [themeName, setThemeName] = useState(settings.customThemeName || '');
  const [themeCss, setThemeCss] = useState(settings.customThemeCss || '');
  const [error, setError] = useState<string | null>(null);

  const handleNameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const name = e.target.value;
    setThemeName(name);
    // Update settings immediately
    const updatedSettings = { ...settings, customThemeName: name };
    onSettingsChange(updatedSettings);
    updateStoreSettings({ customThemeName: name });
  };

  const validateCss = (css: string): string | null => {
    if (!css.trim()) {
      return null; // Empty CSS is valid (allows clearing)
    }

    // Check for :root section
    if (!css.includes(':root')) {
      return 'CSS must include :root section with CSS variables';
    }

    // Check for CSS variables (--variable-name format)
    const hasVariables = /--[\w-]+\s*:/.test(css);
    if (!hasVariables) {
      return 'CSS must contain at least one CSS variable (e.g., --background: #fff)';
    }

    // Check for balanced braces
    const openBraces = (css.match(/{/g) || []).length;
    const closeBraces = (css.match(/}/g) || []).length;
    if (openBraces !== closeBraces) {
      return 'CSS has unmatched braces - check your syntax';
    }

    // Check for basic :root structure
    const rootMatch = css.match(/:root\s*{([^}]+)}/);
    if (!rootMatch) {
      return ':root section appears to be empty or malformed';
    }

    // Warn if .dark section is missing (optional but recommended)
    if (!css.includes('.dark')) {
      // This is just a warning, not an error - don't return it
      // Could add a warning state in the future
    }

    return null; // Valid CSS
  };

  const handleCssChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const css = e.target.value;
    setThemeCss(css);

    // Validate CSS
    const validationError = validateCss(css);
    setError(validationError);

    // Only update settings if validation passes or CSS is empty
    if (!validationError) {
      const updatedSettings = { ...settings, customThemeCss: css };
      onSettingsChange(updatedSettings);
      updateStoreSettings({ customThemeCss: css });
    }
  };

  const handleClear = () => {
    setThemeName('');
    setThemeCss('');
    setError(null);
    const updatedSettings = { ...settings, customThemeName: '', customThemeCss: '' };
    onSettingsChange(updatedSettings);
    updateStoreSettings({ customThemeName: '', customThemeCss: '' });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start gap-3">
        <div className="p-2 rounded-lg bg-primary/10 text-primary">
          <Palette className="h-5 w-5" />
        </div>
        <div className="flex-1 space-y-1">
          <h3 className="text-base font-semibold text-foreground">Custom Theme</h3>
          <p className="text-sm text-muted-foreground">
            Paste CSS variables from{' '}
            <a
              href="https://tweakcn.com/editor/theme?tab=typography&p=dashboard"
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary hover:underline"
            >
              tweakcn.com/editor
            </a>
            {' '}to create your own theme
          </p>
        </div>
      </div>

      {/* Instructions */}
      <div className="rounded-lg border border-border bg-muted/30 p-4">
        <div className="flex items-start gap-2">
          <Info className="h-4 w-4 text-muted-foreground mt-0.5 flex-shrink-0" />
          <div className="space-y-2 text-sm text-muted-foreground">
            <p className="font-medium text-foreground">Expected format:</p>
            <ul className="list-disc list-inside space-y-1 text-xs">
              <li>Must include <code className="px-1 py-0.5 rounded bg-muted">:root</code> section with CSS variables</li>
              <li>Should include <code className="px-1 py-0.5 rounded bg-muted">.dark</code> section for dark mode support</li>
              <li>Variables like <code className="px-1 py-0.5 rounded bg-muted">--background</code>, <code className="px-1 py-0.5 rounded bg-muted">--foreground</code>, <code className="px-1 py-0.5 rounded bg-muted">--primary</code>, etc.</li>
              <li>Supports hex, HSL, RGB color formats</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Theme Name Input */}
      <div className="space-y-2">
        <Label htmlFor="theme-name" className="text-sm font-medium text-foreground">
          Theme Name
        </Label>
        <input
          id="theme-name"
          type="text"
          value={themeName}
          onChange={handleNameChange}
          placeholder="e.g., My Custom Theme"
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
          Theme CSS
        </Label>
        <Textarea
          id="theme-css"
          value={themeCss}
          onChange={handleCssChange}
          placeholder={`:root {
  --background: #ffffff;
  --foreground: #000000;
  --primary: #3b82f6;
  /* ... more variables */
}

.dark {
  --background: #000000;
  --foreground: #ffffff;
  /* ... more variables */
}`}
          className={cn(
            'min-h-[300px] font-mono text-xs resize-y',
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
            <span>Valid CSS - theme will be applied immediately</span>
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="flex justify-end gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={handleClear}
          disabled={!themeName && !themeCss}
        >
          Clear
        </Button>
      </div>
    </div>
  );
}

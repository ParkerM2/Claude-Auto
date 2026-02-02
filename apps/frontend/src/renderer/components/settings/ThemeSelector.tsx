import { useState } from 'react';
import { Check, Sun, Moon, Monitor, Palette, Plus, Trash2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { cn } from '../../lib/utils';
import { Label } from '../ui/label';
import { Button } from '../ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog';
import { COLOR_THEMES } from '../../../shared/constants';
import { useSettingsStore } from '../../stores/settings-store';
import type { ColorTheme, AppSettings, CustomThemeEntry } from '../../../shared/types';
import { CustomThemeInput } from './CustomThemeInput';

interface ThemeSelectorProps {
  settings: AppSettings;
  onSettingsChange: (settings: AppSettings) => void;
}

/**
 * Theme selector component displaying a grid of theme cards with preview swatches
 * and a 3-option mode toggle (Light/Dark/System)
 *
 * Supports multiple custom themes that users can create, save, and delete.
 */
export function ThemeSelector({ settings, onSettingsChange }: ThemeSelectorProps) {
  const { t } = useTranslation(['settings', 'common']);
  const updateStoreSettings = useSettingsStore((state) => state.updateSettings);

  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [newThemeName, setNewThemeName] = useState('');
  const [newThemeCss, setNewThemeCss] = useState('');
  const [cssError, setCssError] = useState<string | null>(null);

  const currentColorTheme = settings.colorTheme || 'default';
  const currentMode = settings.theme;
  const isDark = currentMode === 'dark' ||
    (currentMode === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches);

  const customThemes = settings.customThemes || [];

  const handleColorThemeChange = (themeId: ColorTheme) => {
    // Update local draft state
    onSettingsChange({ ...settings, colorTheme: themeId });
    // Apply immediately to store for live preview (triggers App.tsx useEffect)
    updateStoreSettings({ colorTheme: themeId });
  };

  const handleModeChange = (mode: 'light' | 'dark' | 'system') => {
    // Update local draft state
    onSettingsChange({ ...settings, theme: mode });
    // Apply immediately to store for live preview (triggers App.tsx useEffect)
    updateStoreSettings({ theme: mode });
  };

  const validateCss = (css: string): string | null => {
    if (!css.trim()) {
      return t('settings:theme.customTheme.validationErrors.emptyCss');
    }
    if (!css.includes(':root')) {
      return t('settings:theme.customTheme.validationErrors.missingRoot');
    }
    const hasVariables = /--[\w-]+\s*:/.test(css);
    if (!hasVariables) {
      return t('settings:theme.customTheme.validationErrors.missingVariables');
    }
    const openBraces = (css.match(/{/g) || []).length;
    const closeBraces = (css.match(/}/g) || []).length;
    if (openBraces !== closeBraces) {
      return t('settings:theme.customTheme.validationErrors.unmatchedBraces');
    }
    return null;
  };

  const handleCreateTheme = () => {
    // Validate
    if (!newThemeName.trim()) {
      setCssError(t('settings:theme.customTheme.validationErrors.emptyName'));
      return;
    }
    const validationError = validateCss(newThemeCss);
    if (validationError) {
      setCssError(validationError);
      return;
    }

    // Create new theme entry
    const newTheme: CustomThemeEntry = {
      id: crypto.randomUUID(),
      name: newThemeName.trim(),
      css: newThemeCss,
      createdAt: Date.now(),
    };

    const updatedThemes = [...customThemes, newTheme];
    const themeId: ColorTheme = `custom-${newTheme.id}`;

    // Update settings with new theme and select it
    const updatedSettings = {
      ...settings,
      customThemes: updatedThemes,
      colorTheme: themeId,
    };
    onSettingsChange(updatedSettings);
    updateStoreSettings({ customThemes: updatedThemes, colorTheme: themeId });

    // Reset dialog state
    setNewThemeName('');
    setNewThemeCss('');
    setCssError(null);
    setIsCreateDialogOpen(false);
  };

  const handleDeleteTheme = (themeId: string, e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent selecting the theme when clicking delete

    const updatedThemes = customThemes.filter(t => t.id !== themeId);

    // If we're deleting the currently selected theme, switch to default
    let newColorTheme = settings.colorTheme;
    if (settings.colorTheme === `custom-${themeId}`) {
      newColorTheme = 'default';
    }

    const updatedSettings = {
      ...settings,
      customThemes: updatedThemes,
      colorTheme: newColorTheme,
    };
    onSettingsChange(updatedSettings);
    updateStoreSettings({ customThemes: updatedThemes, colorTheme: newColorTheme });
  };

  const getModeIcon = (mode: string) => {
    switch (mode) {
      case 'light':
        return <Sun className="h-4 w-4" />;
      case 'dark':
        return <Moon className="h-4 w-4" />;
      default:
        return <Monitor className="h-4 w-4" />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Mode Toggle */}
      <div className="space-y-3">
        <Label className="text-sm font-medium text-foreground">
          {t('settings:theme.appearanceMode')}
        </Label>
        <p className="text-sm text-muted-foreground">
          {t('settings:theme.appearanceModeDescription')}
        </p>
        <div className="grid grid-cols-3 gap-3 max-w-md pt-1">
          {(['system', 'light', 'dark'] as const).map((mode) => (
            <button
              key={mode}
              onClick={() => handleModeChange(mode)}
              className={cn(
                'flex flex-col items-center gap-2 p-4 rounded-lg border-2 transition-all',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
                currentMode === mode
                  ? 'border-primary bg-primary/5'
                  : 'border-border hover:border-primary/50 hover:bg-accent/50'
              )}
            >
              {getModeIcon(mode)}
              <span className="text-sm font-medium capitalize">{mode}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Color Theme Grid */}
      <div className="space-y-3">
        <Label className="text-sm font-medium text-foreground">
          {t('settings:theme.colorTheme')}
        </Label>
        <p className="text-sm text-muted-foreground">
          {t('settings:theme.colorThemeDescription')}
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 pt-1">
          {/* Built-in themes */}
          {COLOR_THEMES.map((theme) => {
            const isSelected = currentColorTheme === theme.id;
            const bgColor = isDark ? theme.previewColors.darkBg : theme.previewColors.bg;
            const accentColor = isDark
              ? (theme.previewColors.darkAccent || theme.previewColors.accent)
              : theme.previewColors.accent;

            return (
              <button
                key={theme.id}
                onClick={() => handleColorThemeChange(theme.id as ColorTheme)}
                className={cn(
                  'relative flex flex-col p-4 rounded-lg border-2 text-left transition-all',
                  'hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
                  isSelected
                    ? 'border-primary bg-primary/5 shadow-sm'
                    : 'border-border hover:border-primary/50 hover:bg-accent/30'
                )}
              >
                {isSelected && (
                  <div className="absolute top-2 right-2 w-5 h-5 rounded-full bg-primary flex items-center justify-center">
                    <Check className="w-3 h-3 text-primary-foreground" />
                  </div>
                )}
                <div className="flex items-center gap-2 mb-3">
                  <div className="flex -space-x-1.5">
                    <div
                      className="w-6 h-6 rounded-full border-2 border-background shadow-sm"
                      style={{ backgroundColor: bgColor }}
                      title="Background color"
                    />
                    <div
                      className="w-6 h-6 rounded-full border-2 border-background shadow-sm"
                      style={{ backgroundColor: accentColor }}
                      title="Accent color"
                    />
                  </div>
                </div>
                <div className="space-y-1">
                  <p className="font-medium text-sm text-foreground">{theme.name}</p>
                  <p className="text-xs text-muted-foreground line-clamp-2">{theme.description}</p>
                </div>
              </button>
            );
          })}

          {/* User's custom themes */}
          {customThemes.map((theme) => {
            const themeId: ColorTheme = `custom-${theme.id}`;
            const isSelected = currentColorTheme === themeId;

            return (
              <button
                key={theme.id}
                onClick={() => handleColorThemeChange(themeId)}
                className={cn(
                  'relative flex flex-col p-4 rounded-lg border-2 text-left transition-all group',
                  'hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
                  isSelected
                    ? 'border-primary bg-primary/5 shadow-sm'
                    : 'border-border hover:border-primary/50 hover:bg-accent/30'
                )}
              >
                {isSelected && (
                  <div className="absolute top-2 right-2 w-5 h-5 rounded-full bg-primary flex items-center justify-center">
                    <Check className="w-3 h-3 text-primary-foreground" />
                  </div>
                )}
                {/* Delete button - shown on hover */}
                <button
                  onClick={(e) => handleDeleteTheme(theme.id, e)}
                  className={cn(
                    'absolute top-2 right-2 w-6 h-6 rounded-full bg-destructive/10 hover:bg-destructive/20 flex items-center justify-center',
                    'opacity-0 group-hover:opacity-100 transition-opacity',
                    isSelected && 'right-9'
                  )}
                  title={t('common:buttons.delete')}
                >
                  <Trash2 className="w-3 h-3 text-destructive" />
                </button>
                <div className="flex items-center gap-2 mb-3">
                  <div className="p-2 rounded-lg bg-gradient-to-br from-primary/20 to-accent/20">
                    <Palette className="h-4 w-4 text-primary" />
                  </div>
                </div>
                <div className="space-y-1">
                  <p className="font-medium text-sm text-foreground">{theme.name}</p>
                  <p className="text-xs text-muted-foreground line-clamp-2">
                    {t('settings:theme.customTheme.customDescription')}
                  </p>
                </div>
              </button>
            );
          })}

          {/* Create New Custom Theme Card */}
          <button
            onClick={() => setIsCreateDialogOpen(true)}
            className={cn(
              'relative flex flex-col p-4 rounded-lg border-2 border-dashed text-left transition-all',
              'hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
              'border-border hover:border-primary/50 hover:bg-accent/30'
            )}
          >
            <div className="flex items-center gap-2 mb-3">
              <div className="p-2 rounded-lg bg-muted">
                <Plus className="h-4 w-4 text-muted-foreground" />
              </div>
            </div>
            <div className="space-y-1">
              <p className="font-medium text-sm text-foreground">
                {t('settings:theme.customTheme.createNew')}
              </p>
              <p className="text-xs text-muted-foreground line-clamp-2">
                {t('settings:theme.customTheme.createNewDescription')}
              </p>
            </div>
          </button>
        </div>
      </div>

      {/* Create Custom Theme Dialog */}
      <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{t('settings:theme.customTheme.title')}</DialogTitle>
            <DialogDescription>
              {t('settings:theme.customTheme.description')}{' '}
              <a
                href="https://tweakcn.com/editor/theme?tab=typography&p=dashboard"
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary hover:underline"
              >
                {t('settings:theme.customTheme.linkText')}
              </a>
              {' '}{t('settings:theme.customTheme.descriptionSuffix')}
            </DialogDescription>
          </DialogHeader>

          <CustomThemeInput
            themeName={newThemeName}
            themeCss={newThemeCss}
            error={cssError}
            onNameChange={(name) => {
              setNewThemeName(name);
              setCssError(null);
            }}
            onCssChange={(css) => {
              setNewThemeCss(css);
              const error = css.trim() ? validateCss(css) : null;
              setCssError(error);
            }}
          />

          <DialogFooter>
            <Button variant="outline" onClick={() => setIsCreateDialogOpen(false)}>
              {t('common:buttons.cancel')}
            </Button>
            <Button onClick={handleCreateTheme}>
              {t('settings:theme.customTheme.saveButton')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

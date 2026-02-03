import { RotateCcw } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { cn } from '../../../lib/utils';
import { Label } from '../../ui/label';
import { Slider } from '../../ui/slider';
import { SettingsSection } from '../SettingsSection';
import {
  LETTER_SPACING_MIN,
  LETTER_SPACING_MAX,
  LETTER_SPACING_DEFAULT,
  LETTER_SPACING_STEP,
} from '../../../../shared/constants';
import type { FontSettings } from '../../../../shared/types';

interface LetterSpacingCardProps {
  fontSettings: FontSettings;
  onLetterSpacingChange: (value: number) => void;
}

export function LetterSpacingCard({ fontSettings, onLetterSpacingChange }: LetterSpacingCardProps) {
  const { t } = useTranslation('settings');

  const currentValue = fontSettings.letterSpacing ?? LETTER_SPACING_DEFAULT;

  const handleReset = () => {
    onLetterSpacingChange(LETTER_SPACING_DEFAULT);
  };

  const handleSliderChange = (values: number[]) => {
    if (values.length > 0) {
      onLetterSpacingChange(values[0]);
    }
  };

  // Format value for display (show as percentage-like value)
  const formatValue = (value: number) => {
    if (value === 0) return '0';
    return value > 0 ? `+${(value * 100).toFixed(1)}%` : `${(value * 100).toFixed(1)}%`;
  };

  return (
    <SettingsSection
      title={t('sections.letterSpacing.title', 'Letter Spacing')}
      description={t('sections.letterSpacing.description', 'Adjust the spacing between letters')}
    >
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <Label className="text-sm font-medium">
            {t('sections.letterSpacing.tracking', 'Tracking')}
          </Label>
          <div className="flex items-center gap-2">
            <span className="text-sm font-mono text-muted-foreground min-w-[60px] text-right">
              {formatValue(currentValue)}
            </span>
            {currentValue !== LETTER_SPACING_DEFAULT && (
              <button
                type="button"
                onClick={handleReset}
                className={cn(
                  'p-1.5 rounded-md transition-colors',
                  'hover:bg-accent text-muted-foreground hover:text-foreground',
                  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
                )}
                title={t('sections.letterSpacing.reset', 'Reset to default')}
              >
                <RotateCcw className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
        </div>

        <p className="text-sm text-muted-foreground">
          {t('sections.letterSpacing.trackingDescription', 'Negative values tighten text, positive values loosen it')}
        </p>

        <div className="pt-2">
          <Slider
            value={[currentValue]}
            onValueChange={handleSliderChange}
            min={LETTER_SPACING_MIN}
            max={LETTER_SPACING_MAX}
            step={LETTER_SPACING_STEP}
            className="w-full"
          />
        </div>

        {/* Scale markers */}
        <div className="flex justify-between text-xs text-muted-foreground">
          <span>{t('sections.letterSpacing.tight', 'Tight')}</span>
          <span>{t('sections.letterSpacing.normal', 'Normal')}</span>
          <span>{t('sections.letterSpacing.loose', 'Loose')}</span>
        </div>

        {/* Preview */}
        <div className="space-y-3 pt-2">
          <Label className="text-xs text-muted-foreground">
            {t('sections.letterSpacing.preview', 'Preview')}
          </Label>
          <div
            className="p-4 rounded-md border border-border bg-muted/30 space-y-2"
            style={{ letterSpacing: `${currentValue}em` }}
          >
            <p className="text-lg font-semibold">The Quick Brown Fox</p>
            <p className="text-sm">
              Jumps over the lazy dog. Pack my box with five dozen liquor jugs.
            </p>
            <p className="text-xs text-muted-foreground font-mono">
              const example = &quot;Hello, World!&quot;;
            </p>
          </div>
        </div>
      </div>
    </SettingsSection>
  );
}

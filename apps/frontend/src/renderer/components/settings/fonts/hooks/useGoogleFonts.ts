import { useState, useEffect, useCallback, useMemo } from 'react';
import type { GoogleFont, FontCategory, FontOption } from '../types';

// Popular fonts by category (curated list for quick access)
const POPULAR_FONTS: Record<FontCategory, string[]> = {
  'sans-serif': [
    'Inter',
    'Roboto',
    'Open Sans',
    'Lato',
    'Poppins',
    'Montserrat',
    'Source Sans 3',
    'Nunito',
    'Raleway',
    'Work Sans',
    'DM Sans',
    'Plus Jakarta Sans',
    'Outfit',
    'Manrope',
    'Space Grotesk',
  ],
  'serif': [
    'Merriweather',
    'Playfair Display',
    'Lora',
    'PT Serif',
    'Source Serif 4',
    'Libre Baskerville',
    'Crimson Text',
    'EB Garamond',
    'Cormorant',
    'Spectral',
    'Bitter',
    'DM Serif Display',
    'Bodoni Moda',
    'Fraunces',
    'Newsreader',
  ],
  'monospace': [
    'JetBrains Mono',
    'Fira Code',
    'Source Code Pro',
    'Roboto Mono',
    'IBM Plex Mono',
    'Space Mono',
    'Ubuntu Mono',
    'Inconsolata',
    'Red Hat Mono',
    'Overpass Mono',
    'DM Mono',
    'Martian Mono',
    'Azeret Mono',
    'Spline Sans Mono',
    'Syne Mono',
  ],
};

// System font fallbacks
const SYSTEM_FONTS: Record<FontCategory, FontOption> = {
  'sans-serif': { value: 'system-ui', label: 'System Default' },
  'serif': { value: 'Georgia', label: 'System Serif (Georgia)' },
  'monospace': { value: 'ui-monospace', label: 'System Mono' },
};

interface UseGoogleFontsOptions {
  category: FontCategory;
}

interface UseGoogleFontsReturn {
  fonts: FontOption[];
  isLoading: boolean;
  error: string | null;
  loadFont: (fontFamily: string) => void;
  searchFonts: (query: string) => FontOption[];
}

// Cache for all Google Fonts
let fontsCache: GoogleFont[] | null = null;
let fontsCachePromise: Promise<GoogleFont[]> | null = null;

// Set of currently loaded fonts
const loadedFonts = new Set<string>();

/**
 * Hook to fetch and manage Google Fonts
 */
export function useGoogleFonts({ category }: UseGoogleFontsOptions): UseGoogleFontsReturn {
  const [allFonts, setAllFonts] = useState<GoogleFont[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch all fonts (cached)
  useEffect(() => {
    const fetchFonts = async () => {
      // Use cache if available
      if (fontsCache) {
        setAllFonts(fontsCache);
        setIsLoading(false);
        return;
      }

      // Use existing promise if already fetching
      if (fontsCachePromise) {
        try {
          const fonts = await fontsCachePromise;
          setAllFonts(fonts);
          setIsLoading(false);
        } catch {
          setError('Failed to load fonts');
          setIsLoading(false);
        }
        return;
      }

      // Fetch from API
      setIsLoading(true);
      setError(null);

      fontsCachePromise = fetch(
        'https://www.googleapis.com/webfonts/v1/webfonts?key=AIzaSyBwIX97bVWr3-6AIUvGkcNnmFgirefZ6Sw&sort=popularity'
      )
        .then((res) => {
          if (!res.ok) throw new Error('Failed to fetch fonts');
          return res.json();
        })
        .then((data) => {
          const items: GoogleFont[] = data.items || [];
          fontsCache = items;
          return items;
        })
        .catch(() => {
          return [] as GoogleFont[];
        });

      try {
        const fonts = await fontsCachePromise;
        setAllFonts(fonts || []);
      } catch {
        setError('Failed to load Google Fonts. Using popular fonts only.');
      } finally {
        setIsLoading(false);
      }
    };

    fetchFonts();
  }, []);

  // Filter fonts by category
  const categoryFonts = useMemo(() => {
    const categoryMap: Record<FontCategory, string> = {
      'sans-serif': 'sans-serif',
      'serif': 'serif',
      'monospace': 'monospace',
    };

    return allFonts.filter((font) => font.category === categoryMap[category]);
  }, [allFonts, category]);

  // Build font options list
  const fonts = useMemo((): FontOption[] => {
    const options: FontOption[] = [];

    // Add system default first
    options.push(SYSTEM_FONTS[category]);

    // Add popular fonts section
    const popularList = POPULAR_FONTS[category];
    const popularFonts = popularList.map((name) => ({
      value: name,
      label: name,
      isLoaded: loadedFonts.has(name),
    }));

    options.push(...popularFonts);

    // Add separator and remaining fonts from API (if loaded)
    if (categoryFonts.length > 0) {
      const popularSet = new Set(popularList);
      const additionalFonts = categoryFonts
        .filter((font) => !popularSet.has(font.family))
        .slice(0, 100) // Limit to avoid overwhelming the dropdown
        .map((font) => ({
          value: font.family,
          label: font.family,
          isLoaded: loadedFonts.has(font.family),
        }));

      options.push(...additionalFonts);
    }

    return options;
  }, [category, categoryFonts]);

  // Load a font dynamically
  const loadFont = useCallback((fontFamily: string) => {
    if (loadedFonts.has(fontFamily) || fontFamily === 'system-ui' || fontFamily === 'ui-monospace' || fontFamily === 'Georgia') {
      return;
    }

    // Create link element to load the font
    const link = document.createElement('link');
    link.href = `https://fonts.googleapis.com/css2?family=${encodeURIComponent(fontFamily).replace(/%20/g, '+')}:wght@400;500;600;700&display=swap`;
    link.rel = 'stylesheet';
    document.head.appendChild(link);

    loadedFonts.add(fontFamily);
  }, []);

  // Search fonts
  const searchFonts = useCallback(
    (query: string): FontOption[] => {
      if (!query.trim()) {
        return fonts;
      }

      const lowerQuery = query.toLowerCase();
      return fonts.filter((font) => font.label.toLowerCase().includes(lowerQuery));
    },
    [fonts]
  );

  return {
    fonts,
    isLoading,
    error,
    loadFont,
    searchFonts,
  };
}

/**
 * Preload fonts that are currently in use
 */
export function preloadFonts(fontSettings: { sansSerif?: string; serif?: string; mono?: string }) {
  const { sansSerif, serif, mono } = fontSettings;

  [sansSerif, serif, mono].forEach((font) => {
    if (font && !loadedFonts.has(font) && font !== 'system-ui' && font !== 'ui-monospace' && font !== 'Georgia') {
      const link = document.createElement('link');
      link.href = `https://fonts.googleapis.com/css2?family=${encodeURIComponent(font).replace(/%20/g, '+')}:wght@400;500;600;700&display=swap`;
      link.rel = 'stylesheet';
      document.head.appendChild(link);
      loadedFonts.add(font);
    }
  });
}

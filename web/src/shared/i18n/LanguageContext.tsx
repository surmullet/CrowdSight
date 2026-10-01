import React, { createContext, useContext, useState, useMemo } from 'react';
import { Locale, translations, TranslationDictionary } from './translations';

export interface LanguageContextType {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  toggleLocale: () => void;
  t: TranslationDictionary;
}

const STORAGE_KEY = 'crowdsight_locale';

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

export const LanguageProvider: React.FC<{ children: React.ReactNode; defaultLocale?: Locale }> = ({
  children,
  defaultLocale,
}) => {
  const [locale, setLocaleState] = useState<Locale>(() => {
    if (defaultLocale) return defaultLocale;
    try {
      const isTestEnv = typeof process !== 'undefined' && Boolean(process.env && process.env.NODE_ENV === 'test');
      if (typeof window !== 'undefined' && window.localStorage && !isTestEnv) {
        const saved = localStorage.getItem(STORAGE_KEY);
        if (saved === 'vi' || saved === 'en') return saved;
      }
    } catch {
      // LocalStorage might be inaccessible in some environments
    }
    return 'vi';
  });

  const setLocale = (newLocale: Locale) => {
    setLocaleState(newLocale);
    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        localStorage.setItem(STORAGE_KEY, newLocale);
      }
    } catch {
      // ignore
    }
  };

  const toggleLocale = () => {
    setLocale(locale === 'vi' ? 'en' : 'vi');
  };

  const t = useMemo(() => translations[locale], [locale]);

  return (
    <LanguageContext.Provider value={{ locale, setLocale, toggleLocale, t }}>
      {children}
    </LanguageContext.Provider>
  );
};

export const LanguageWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const context = useContext(LanguageContext);
  if (context) {
    return <>{children}</>;
  }
  return <LanguageProvider>{children}</LanguageProvider>;
};

export const useLanguage = (): LanguageContextType => {
  const context = useContext(LanguageContext);
  if (!context) {
    // Graceful fallback for components rendered outside of LanguageProvider (e.g. isolated unit tests)
    return {
      locale: 'vi',
      setLocale: () => {},
      toggleLocale: () => {},
      t: translations.vi,
    };
  }
  return context;
};

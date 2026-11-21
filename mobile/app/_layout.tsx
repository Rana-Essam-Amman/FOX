import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { useEffect, useRef, useState } from 'react';
import { I18nManager, View, Text, TouchableOpacity, StyleSheet, Platform } from 'react-native';
import { setupI18n, i18n, isRTL, detectLocale, initializeLocale, saveLocale } from '../src/i18n';
import { colors, spacing } from '../src/design/tokens';

export default function RootLayout() {
  const [locale, setLocale] = useState<'en' | 'ar'>(() => {
    const initial = detectLocale();
    setupI18n(initial);
    return initial;
  });
  const [ready, setReady] = useState(false);
  // Guards against a late initialization result overwriting a user selection
  // that occurred after the user was allowed to interact (i.e., after ready).
  const userSelectedRef = useRef(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const resolved = await initializeLocale();
      if (cancelled || userSelectedRef.current) {
        // Even if cancelled or user already chose, mark ready so UI can appear
        // if we haven't unmounted. User choice takes precedence.
        if (!cancelled) setReady(true);
        return;
      }
      setupI18n(resolved);
      setLocale(resolved);
      setReady(true);
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!ready) return;
    const rtl = isRTL(locale);
    // forceRTL only takes full effect after a native app reload.
    // We call it only when the desired direction differs from the current native setting,
    // and only once per change, not on every render.
    if (Platform.OS !== 'web' && I18nManager.isRTL !== rtl) {
      I18nManager.forceRTL(rtl);
      // Full native layout flip requires restarting the app.
      // Web direction is applied immediately via the container style below.
    }
  }, [locale, ready]);

  const toggleLanguage = async () => {
    if (!ready) return;
    userSelectedRef.current = true;
    const next: 'en' | 'ar' = locale === 'en' ? 'ar' : 'en';
    setupI18n(next);
    setLocale(next);
    await saveLocale(next);
    // On native, I18nManager.forceRTL does not flip the layout until the next app launch.
  };

  const rtl = isRTL(locale);

  if (!ready) {
    return (
      <View style={styles.container} testID="locale-loading">
        <StatusBar style="light" />
      </View>
    );
  }

  return (
    <View style={[styles.container, { direction: rtl ? 'rtl' : 'ltr' }]}>
      <StatusBar style="light" />
      <View style={styles.langBar}>
        <TouchableOpacity
          onPress={toggleLanguage}
          style={styles.langButton}
          accessibilityRole="button"
          accessibilityLabel={locale === 'en' ? i18n.t('common.switchToArabic') : i18n.t('common.switchToEnglish')}
          testID="lang-toggle"
        >
          <Text style={styles.langText}>
            {locale === 'en' ? 'العربية' : 'English'}
          </Text>
        </TouchableOpacity>
      </View>
      <Stack
        screenOptions={{
          headerStyle: { backgroundColor: colors.surface },
          headerTintColor: colors.primary,
          headerTitleStyle: { fontWeight: '600', color: colors.text },
          contentStyle: { backgroundColor: colors.background },
        }}
      >
        <Stack.Screen name="index" options={{ title: i18n.t('home.title'), headerShown: false }} />
        <Stack.Screen name="create" options={{ title: i18n.t('create.title') }} />
        <Stack.Screen name="review" options={{ title: i18n.t('create.review.title') }} />
      </Stack>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  langBar: {
    paddingHorizontal: spacing.md,
    paddingTop: spacing.sm,
    alignItems: 'flex-end',
  },
  langButton: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    backgroundColor: colors.elevated,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: colors.border,
    minHeight: 44,
    minWidth: 44,
    justifyContent: 'center',
    alignItems: 'center',
  },
  langText: {
    color: colors.text,
    fontWeight: '600',
    fontSize: 14,
  },
});

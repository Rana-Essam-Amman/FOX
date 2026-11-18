import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { useEffect, useState } from 'react';
import { I18nManager, View, Text, TouchableOpacity, StyleSheet, Platform } from 'react-native';
import { setupI18n, i18n, isRTL, detectLocale } from '../src/i18n';
import { colors, spacing } from '../src/design/tokens';

export default function RootLayout() {
  const [locale, setLocale] = useState<'en' | 'ar'>(() => {
    const initial = detectLocale();
    setupI18n(initial);
    return initial;
  });

  useEffect(() => {
    const rtl = isRTL(locale);
    if (I18nManager.isRTL !== rtl) {
      I18nManager.forceRTL(rtl);
      // Native platforms may require a full app reload for complete RTL layout flip.
      // Web applies direction immediately via the container style.
    }
  }, [locale]);

  const toggleLanguage = () => {
    const next: 'en' | 'ar' = locale === 'en' ? 'ar' : 'en';
    setupI18n(next);
    setLocale(next);
    if (Platform.OS !== 'web') {
      // On native, forceRTL takes effect after reload for full layout flip.
      // The state update is still applied so strings change immediately.
    }
  };

  const rtl = isRTL(locale);

  return (
    <View style={[styles.container, { direction: rtl ? 'rtl' : 'ltr' }]}>
      <StatusBar style="dark" />
      <View style={styles.langBar}>
        <TouchableOpacity
          onPress={toggleLanguage}
          style={styles.langButton}
          accessibilityRole="button"
          accessibilityLabel={locale === 'en' ? 'Switch to Arabic' : 'Switch to English'}
        >
          <Text style={styles.langText}>
            {locale === 'en' ? 'العربية' : 'English'}
          </Text>
        </TouchableOpacity>
      </View>
      <Stack
        screenOptions={{
          headerStyle: { backgroundColor: colors.background },
          headerTintColor: colors.primary,
          headerTitleStyle: { fontWeight: '600' },
          contentStyle: { backgroundColor: colors.background },
        }}
      >
        <Stack.Screen name="index" options={{ title: i18n.t('home.title'), headerShown: false }} />
        <Stack.Screen name="create" options={{ title: i18n.t('create.title') }} />
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
    backgroundColor: colors.surface,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: colors.border,
    minHeight: 44,
    minWidth: 44,
    justifyContent: 'center',
    alignItems: 'center',
  },
  langText: {
    color: colors.primary,
    fontWeight: '600',
    fontSize: 14,
  },
});
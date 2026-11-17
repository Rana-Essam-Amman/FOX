import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { useEffect, useState } from 'react';
import { I18nManager, View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { setupI18n, i18n, isRTL } from '../src/i18n';
import { colors, spacing } from '../src/design/tokens';

export default function RootLayout() {
  const [locale, setLocale] = useState(i18n.locale);

  useEffect(() => {
    setupI18n();
    const rtl = isRTL();
    if (I18nManager.isRTL !== rtl) {
      I18nManager.forceRTL(rtl);
      // Note: In production, app reload is typically needed for full RTL flip on native.
      // For web preview, direction is handled via styles.
    }
  }, []);

  const toggleLanguage = () => {
    const next = locale === 'en' ? 'ar' : 'en';
    i18n.locale = next;
    setLocale(next);
    const rtl = next === 'ar';
    I18nManager.forceRTL(rtl);
  };

  return (
    <View style={[styles.container, { direction: isRTL() ? 'rtl' : 'ltr' }]}>
      <StatusBar style="dark" />
      <View style={styles.langBar}>
        <TouchableOpacity onPress={toggleLanguage} style={styles.langButton}>
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
  },
  langText: {
    color: colors.primary,
    fontWeight: '600',
    fontSize: 14,
  },
});
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, useWindowDimensions } from 'react-native';
import { Link } from 'expo-router';
import { colors, spacing, typography, radii } from '../src/design/tokens';
import { i18n, isRTL } from '../src/i18n';

export default function HomeScreen() {
  const { width } = useWindowDimensions();
  const isDesktop = width >= 768;

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={[styles.content, isDesktop && styles.desktopContent]}
    >
      <View style={styles.hero}>
        <Text style={[typography.heading, styles.title, isRTL() && styles.rtlText]}>
          {i18n.t('home.title')}
        </Text>
        <Text style={[typography.body, styles.subtitle, isRTL() && styles.rtlText]}>
          {i18n.t('home.subtitle')}
        </Text>
        <Link href="/create" asChild>
          <TouchableOpacity style={styles.primaryButton} accessibilityRole="button" accessibilityLabel={i18n.t('home.createAction')}>
            <Text style={styles.primaryButtonText}>{i18n.t('home.createAction')}</Text>
          </TouchableOpacity>
        </Link>
      </View>

      <View style={styles.section}>
        <Text style={[typography.subheading, styles.sectionTitle, isRTL() && styles.rtlText]}>
          {i18n.t('home.recentProjects')}
        </Text>
        <View style={styles.emptyState}>
          <Text style={[typography.body, styles.emptyText, isRTL() && styles.rtlText]}>
            {i18n.t('home.emptyProjects')}
          </Text>
        </View>
      </View>

      <View style={styles.section}>
        <Text style={[typography.subheading, styles.sectionTitle, isRTL() && styles.rtlText]}>
          {i18n.t('home.examples')}
        </Text>
        <View style={[styles.examplesGrid, isDesktop && styles.examplesGridDesktop]}>
          <View style={styles.exampleCard}>
            <View style={styles.examplePlaceholder} />
            <Text style={[typography.caption, styles.exampleTitle, isRTL() && styles.rtlText]}>
              {i18n.t('home.example1')}
            </Text>
          </View>
          <View style={styles.exampleCard}>
            <View style={styles.examplePlaceholder} />
            <Text style={[typography.caption, styles.exampleTitle, isRTL() && styles.rtlText]}>
              {i18n.t('home.example2')}
            </Text>
          </View>
        </View>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  content: {
    padding: spacing.lg,
    paddingBottom: spacing.xxl,
  },
  desktopContent: {
    maxWidth: 900,
    alignSelf: 'center',
    width: '100%',
  },
  hero: {
    alignItems: 'center',
    marginBottom: spacing.xl,
    paddingVertical: spacing.xl,
  },
  title: {
    color: colors.primary,
    marginBottom: spacing.sm,
    textAlign: 'center',
  },
  subtitle: {
    color: colors.textSecondary,
    textAlign: 'center',
    marginBottom: spacing.lg,
    maxWidth: 400,
  },
  primaryButton: {
    backgroundColor: colors.primary,
    paddingHorizontal: spacing.xl,
    paddingVertical: spacing.md,
    borderRadius: radii.full,
    minHeight: 48,
    justifyContent: 'center',
    alignItems: 'center',
  },
  primaryButtonText: {
    color: '#FFFFFF',
    fontSize: 18,
    fontWeight: '600',
  },
  section: {
    marginBottom: spacing.xl,
  },
  sectionTitle: {
    color: colors.text,
    marginBottom: spacing.md,
  },
  emptyState: {
    backgroundColor: colors.surface,
    borderRadius: radii.md,
    padding: spacing.lg,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: colors.border,
    borderStyle: 'dashed',
  },
  emptyText: {
    color: colors.textSecondary,
    textAlign: 'center',
  },
  examplesGrid: {
    gap: spacing.md,
  },
  examplesGridDesktop: {
    flexDirection: 'row',
  },
  exampleCard: {
    flex: 1,
    backgroundColor: colors.surface,
    borderRadius: radii.md,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: colors.border,
  },
  examplePlaceholder: {
    height: 120,
    backgroundColor: colors.secondary,
    opacity: 0.3,
  },
  exampleTitle: {
    padding: spacing.md,
    color: colors.text,
    textAlign: 'center',
  },
  rtlText: {
    textAlign: 'right',
  },
});
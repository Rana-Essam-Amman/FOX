import { View, Text, StyleSheet, ScrollView, TouchableOpacity, useWindowDimensions } from 'react-native';
import { Link, useRouter } from 'expo-router';
import { colors, spacing, typography, radii } from '../src/design/tokens';
import { i18n, isRTL } from '../src/i18n';

export default function HomeScreen() {
  const { width } = useWindowDimensions();
  const isDesktop = width >= 768;
  const router = useRouter();
  const rtl = isRTL();

  const goToCreate = (mode?: string, concept?: string) => {
    const params: Record<string, string> = {};
    if (mode) params.mode = mode;
    if (concept) params.concept = concept;
    router.push({ pathname: '/create', params });
  };

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={[styles.content, isDesktop && styles.desktopContent]}
    >
      {/* Compact studio header */}
      <View style={[styles.header, rtl && styles.headerRtl]}>
        <Text style={[typography.heading, styles.wordmark]} accessibilityRole="header">
          {i18n.t('home.title')}
        </Text>
        <View style={styles.headerSpacer} />
      </View>

      {/* Main creative hero */}
      <View style={styles.hero}>
        <Text style={[typography.heading, styles.heroTitle, rtl && styles.rtlText]}>
          {i18n.t('home.subtitle')}
        </Text>
        <Text style={[typography.body, styles.heroSupporting, rtl && styles.rtlText]}>
          {i18n.t('home.supporting')}
        </Text>
        <Link href="/create" asChild>
          <TouchableOpacity
            style={styles.primaryCta}
            accessibilityRole="button"
            accessibilityLabel={i18n.t('home.createAction')}
          >
            <Text style={styles.primaryCtaText}>{i18n.t('home.createAction')}</Text>
          </TouchableOpacity>
        </Link>
      </View>

      {/* Quick creation entry points */}
      <View style={styles.section}>
        <Text style={[typography.subheading, styles.sectionTitle, rtl && styles.rtlText]}>
          {i18n.t('home.quickStart')}
        </Text>
        <View style={[styles.quickGrid, isDesktop && styles.quickGridDesktop]}>
          <TouchableOpacity
            style={styles.quickCard}
            onPress={() => goToCreate('text')}
            accessibilityRole="button"
            accessibilityLabel={i18n.t('a11y.quickEntry', { label: i18n.t('home.textIdea') })}
          >
            <Text style={[typography.body, styles.quickCardTitle, rtl && styles.rtlText]}>
              {i18n.t('home.textIdea')}
            </Text>
            <Text style={[typography.caption, styles.quickCardHint, rtl && styles.rtlText]}>
              {rtl ? 'اكتب فكرتك' : 'Write your idea'}
            </Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={styles.quickCard}
            onPress={() => goToCreate('image')}
            accessibilityRole="button"
            accessibilityLabel={i18n.t('a11y.quickEntry', { label: i18n.t('home.imageStart') })}
          >
            <Text style={[typography.body, styles.quickCardTitle, rtl && styles.rtlText]}>
              {i18n.t('home.imageStart')}
            </Text>
            <Text style={[typography.caption, styles.quickCardHint, rtl && styles.rtlText]}>
              {rtl ? 'ارفع صورة' : 'Upload a photo'}
            </Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={styles.quickCard}
            onPress={() => goToCreate('concept')}
            accessibilityRole="button"
            accessibilityLabel={i18n.t('a11y.quickEntry', { label: i18n.t('home.conceptStart') })}
          >
            <Text style={[typography.body, styles.quickCardTitle, rtl && styles.rtlText]}>
              {i18n.t('home.conceptStart')}
            </Text>
            <Text style={[typography.caption, styles.quickCardHint, rtl && styles.rtlText]}>
              {rtl ? 'اختر مفهوماً' : 'Pick a concept'}
            </Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* Recent projects */}
      <View style={styles.section}>
        <Text style={[typography.subheading, styles.sectionTitle, rtl && styles.rtlText]}>
          {i18n.t('home.recentProjects')}
        </Text>
        <View style={styles.emptyState}>
          <Text style={[typography.body, styles.emptyTitle, rtl && styles.rtlText]}>
            {i18n.t('home.emptyProjects')}
          </Text>
          <Text style={[typography.caption, styles.emptyHint, rtl && styles.rtlText]}>
            {i18n.t('home.emptyProjectsHint')}
          </Text>
        </View>
      </View>

      {/* Inspiration / templates */}
      <View style={styles.section}>
        <Text style={[typography.subheading, styles.sectionTitle, rtl && styles.rtlText]}>
          {i18n.t('home.inspiration')}
        </Text>
        <View style={[styles.templateGrid, isDesktop && styles.templateGridDesktop]}>
          <TouchableOpacity
            style={styles.templateCard}
            onPress={() => goToCreate(undefined, 'product')}
            accessibilityRole="button"
            accessibilityLabel={i18n.t('home.templateProduct')}
          >
            <View style={styles.templateAccent} />
            <Text style={[typography.body, styles.templateTitle, rtl && styles.rtlText]}>
              {i18n.t('home.templateProduct')}
            </Text>
            <Text style={[typography.caption, styles.templateHint, rtl && styles.rtlText]}>
              {rtl ? 'أبرز منتجك' : 'Showcase your product'}
            </Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={styles.templateCard}
            onPress={() => goToCreate(undefined, 'social')}
            accessibilityRole="button"
            accessibilityLabel={i18n.t('home.templateSocial')}
          >
            <View style={[styles.templateAccent, { backgroundColor: colors.primary }]} />
            <Text style={[typography.body, styles.templateTitle, rtl && styles.rtlText]}>
              {i18n.t('home.templateSocial')}
            </Text>
            <Text style={[typography.caption, styles.templateHint, rtl && styles.rtlText]}>
              {rtl ? 'محتوى قصير' : 'Short-form content'}
            </Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={styles.templateCard}
            onPress={() => goToCreate(undefined, 'story')}
            accessibilityRole="button"
            accessibilityLabel={i18n.t('home.templateStory')}
          >
            <View style={[styles.templateAccent, { backgroundColor: '#4A5568' }]} />
            <Text style={[typography.body, styles.templateTitle, rtl && styles.rtlText]}>
              {i18n.t('home.templateStory')}
            </Text>
            <Text style={[typography.caption, styles.templateHint, rtl && styles.rtlText]}>
              {rtl ? 'لحظة مميزة' : 'A memorable moment'}
            </Text>
          </TouchableOpacity>
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
    paddingHorizontal: spacing.md,
    paddingTop: spacing.md,
    paddingBottom: spacing.xxl,
  },
  desktopContent: {
    maxWidth: 900,
    alignSelf: 'center',
    width: '100%',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: spacing.lg,
    minHeight: 48,
  },
  headerRtl: {
    flexDirection: 'row-reverse',
  },
  wordmark: {
    color: colors.text,
    fontSize: 28,
  },
  headerSpacer: {
    flex: 1,
  },
  hero: {
    marginBottom: spacing.xl,
  },
  heroTitle: {
    color: colors.text,
    marginBottom: spacing.sm,
  },
  heroSupporting: {
    color: colors.textSecondary,
    marginBottom: spacing.lg,
    lineHeight: 24,
  },
  primaryCta: {
    backgroundColor: colors.primary,
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.xl,
    borderRadius: radii.full,
    alignSelf: 'flex-start',
    minHeight: 48,
    justifyContent: 'center',
    alignItems: 'center',
  },
  primaryCtaText: {
    color: '#FFFFFF',
    fontSize: 17,
    fontWeight: '600',
  },
  section: {
    marginBottom: spacing.xl,
  },
  sectionTitle: {
    color: colors.text,
    marginBottom: spacing.md,
  },
  quickGrid: {
    gap: spacing.sm,
  },
  quickGridDesktop: {
    flexDirection: 'row',
  },
  quickCard: {
    flex: 1,
    backgroundColor: colors.surface,
    borderRadius: radii.lg,
    padding: spacing.md,
    borderWidth: 1,
    borderColor: colors.border,
    minHeight: 88,
    justifyContent: 'center',
  },
  quickCardTitle: {
    color: colors.text,
    marginBottom: spacing.xs,
  },
  quickCardHint: {
    color: colors.textSecondary,
  },
  emptyState: {
    backgroundColor: colors.surface,
    borderRadius: radii.lg,
    padding: spacing.lg,
    borderWidth: 1,
    borderColor: colors.border,
  },
  emptyTitle: {
    color: colors.text,
    marginBottom: spacing.sm,
  },
  emptyHint: {
    color: colors.textSecondary,
  },
  templateGrid: {
    gap: spacing.md,
  },
  templateGridDesktop: {
    flexDirection: 'row',
  },
  templateCard: {
    flex: 1,
    backgroundColor: colors.elevated,
    borderRadius: radii.lg,
    padding: spacing.md,
    borderWidth: 1,
    borderColor: colors.border,
    minHeight: 120,
    justifyContent: 'flex-end',
  },
  templateAccent: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    height: 4,
    backgroundColor: colors.primary,
    borderTopLeftRadius: radii.lg,
    borderTopRightRadius: radii.lg,
  },
  templateTitle: {
    color: colors.text,
    marginBottom: spacing.xs,
  },
  templateHint: {
    color: colors.textSecondary,
  },
  rtlText: {
    textAlign: 'right',
  },
});

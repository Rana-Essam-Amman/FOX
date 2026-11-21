import { StyleSheet } from 'react-native';
import { colors, spacing, radii } from '../design/tokens';

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

export { styles };

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
    maxWidth: 700,
    alignSelf: 'center',
    width: '100%',
  },
  emptyContainer: {
    flex: 1,
    backgroundColor: colors.background,
    justifyContent: 'center',
    alignItems: 'center',
    padding: spacing.lg,
  },
  emptyText: {
    color: colors.textSecondary,
    textAlign: 'center',
    marginBottom: spacing.lg,
  },
  title: {
    color: colors.text,
    marginBottom: spacing.md,
  },
  localBadge: {
    backgroundColor: colors.elevated,
    borderRadius: radii.md,
    borderWidth: 1,
    borderColor: colors.primary,
    padding: spacing.sm,
    marginBottom: spacing.lg,
  },
  localBadgeText: {
    color: colors.primary,
    textAlign: 'center',
    fontWeight: '600',
  },
  section: {
    marginBottom: spacing.lg,
  },
  label: {
    color: colors.textSecondary,
    marginBottom: spacing.sm,
  },
  card: {
    backgroundColor: colors.surface,
    borderRadius: radii.md,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.md,
  },
  cardText: {
    color: colors.text,
  },
  image: {
    width: '100%',
    height: 200,
    borderRadius: radii.md,
    backgroundColor: colors.surface,
  },
  noImage: {
    backgroundColor: colors.surface,
    borderRadius: radii.md,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.lg,
    alignItems: 'center',
  },
  noImageText: {
    color: colors.textSecondary,
  },
  settingsCard: {
    backgroundColor: colors.surface,
    borderRadius: radii.md,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.md,
  },
  settingRow: {
    color: colors.text,
    marginBottom: spacing.xs,
  },
  disclaimer: {
    color: colors.textSecondary,
    textAlign: 'center',
    marginBottom: spacing.lg,
  },
  backButton: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    paddingVertical: spacing.md,
    borderRadius: radii.full,
    alignItems: 'center',
    minHeight: 48,
    justifyContent: 'center',
  },
  backButtonText: {
    color: colors.text,
    fontSize: 16,
    fontWeight: '600',
  },
  rtlText: {
    textAlign: 'right',
  },
});

export { styles };

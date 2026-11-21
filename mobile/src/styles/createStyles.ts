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
  title: {
    color: colors.text,
    marginBottom: spacing.lg,
  },
  section: {
    marginBottom: spacing.lg,
  },
  sectionLabel: {
    color: colors.text,
    marginBottom: spacing.sm,
  },
  optionLabel: {
    color: colors.textSecondary,
    marginTop: spacing.md,
    marginBottom: spacing.sm,
  },
  input: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radii.md,
    padding: spacing.md,
    minHeight: 100,
    textAlignVertical: 'top',
    backgroundColor: colors.surface,
    color: colors.text,
    fontSize: 16,
  },
  rtlInput: {
    textAlign: 'right',
  },
  uploadButton: {
    backgroundColor: colors.surface,
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.lg,
    borderRadius: radii.md,
    alignSelf: 'flex-start',
    minHeight: 44,
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: colors.border,
  },
  uploadButtonEmphasized: {
    borderColor: colors.primary,
    borderWidth: 2,
  },
  conceptBanner: {
    backgroundColor: colors.elevated,
    borderRadius: radii.md,
    borderWidth: 1,
    borderColor: colors.primary,
    padding: spacing.sm,
    marginBottom: spacing.md,
  },
  conceptBannerText: {
    color: colors.primary,
    textAlign: 'center',
  },
  chipRowRtl: {
    flexDirection: 'row-reverse',
  },
  uploadButtonText: {
    color: colors.text,
    fontWeight: '600',
  },
  previewImage: {
    width: 100,
    height: 100,
    borderRadius: radii.md,
    marginTop: spacing.md,
  },
  chipRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
  },
  chip: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderRadius: radii.full,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surface,
    minHeight: 40,
    justifyContent: 'center',
  },
  chipActive: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  chipText: {
    color: colors.text,
    fontSize: 14,
  },
  chipTextActive: {
    color: '#FFFFFF',
    fontWeight: '600',
  },
  previewBox: {
    backgroundColor: colors.surface,
    borderRadius: radii.lg,
    borderWidth: 1,
    borderColor: colors.border,
    minHeight: 160,
    overflow: 'hidden',
    justifyContent: 'center',
    alignItems: 'center',
  },
  previewFull: {
    width: '100%',
    height: 160,
  },
  previewEmpty: {
    color: colors.textSecondary,
    textAlign: 'center',
    padding: spacing.md,
  },
  previewMeta: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    backgroundColor: 'rgba(13,16,20,0.75)',
    padding: spacing.sm,
  },
  previewMetaText: {
    color: colors.text,
  },
  previewMetaSub: {
    color: colors.textSecondary,
    marginTop: 2,
  },
  errorText: {
    color: colors.error,
    marginBottom: spacing.md,
    textAlign: 'center',
  },
  continueButton: {
    backgroundColor: colors.primary,
    paddingVertical: spacing.md,
    borderRadius: radii.full,
    alignItems: 'center',
    minHeight: 48,
    justifyContent: 'center',
    marginBottom: spacing.md,
  },
  continueButtonText: {
    color: '#FFFFFF',
    fontSize: 17,
    fontWeight: '600',
  },
  disclaimer: {
    color: colors.textSecondary,
    textAlign: 'center',
  },
  rtlText: {
    textAlign: 'right',
  },
});

export { styles };

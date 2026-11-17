export const colors = {
  background: '#FFFFFF',
  surface: '#F8F9FA',
  primary: '#FF6B35',
  primaryDark: '#E55A2B',
  secondary: '#4ECDC4',
  text: '#1A1A2E',
  textSecondary: '#6B7280',
  border: '#E5E7EB',
  error: '#EF4444',
  success: '#10B981',
  disabled: '#9CA3AF',
};

export const spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
  xxl: 48,
};

export const typography = {
  heading: {
    fontSize: 32,
    fontWeight: '700' as const,
    lineHeight: 40,
  },
  subheading: {
    fontSize: 20,
    fontWeight: '600' as const,
    lineHeight: 28,
  },
  body: {
    fontSize: 16,
    fontWeight: '400' as const,
    lineHeight: 24,
  },
  caption: {
    fontSize: 14,
    fontWeight: '400' as const,
    lineHeight: 20,
  },
};

export const radii = {
  sm: 8,
  md: 12,
  lg: 16,
  full: 9999,
};
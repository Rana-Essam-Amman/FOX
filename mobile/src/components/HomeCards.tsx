import { View, Text, TouchableOpacity } from 'react-native';
import { typography } from '../design/tokens';
import { styles } from '../styles/homeStyles';
import { i18n } from '../i18n';

interface QuickCardProps {
  titleKey: string;
  hintKey: string;
  onPress: () => void;
  rtl: boolean;
}

export function QuickCard({ titleKey, hintKey, onPress, rtl }: QuickCardProps) {
  return (
    <TouchableOpacity
      style={styles.quickCard}
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={i18n.t('a11y.quickEntry', { label: i18n.t(titleKey) })}
    >
      <Text style={[typography.body, styles.quickCardTitle, rtl && styles.rtlText]}>
        {i18n.t(titleKey)}
      </Text>
      <Text style={[typography.caption, styles.quickCardHint, rtl && styles.rtlText]}>
        {i18n.t(hintKey)}
      </Text>
    </TouchableOpacity>
  );
}

interface TemplateCardProps {
  titleKey: string;
  hintKey: string;
  accentColor?: string;
  onPress: () => void;
  rtl: boolean;
}

export function TemplateCard({ titleKey, hintKey, accentColor, onPress, rtl }: TemplateCardProps) {
  return (
    <TouchableOpacity
      style={styles.templateCard}
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={i18n.t(titleKey)}
    >
      <View style={[styles.templateAccent, accentColor ? { backgroundColor: accentColor } : null]} />
      <Text style={[typography.body, styles.templateTitle, rtl && styles.rtlText]}>
        {i18n.t(titleKey)}
      </Text>
      <Text style={[typography.caption, styles.templateHint, rtl && styles.rtlText]}>
        {i18n.t(hintKey)}
      </Text>
    </TouchableOpacity>
  );
}

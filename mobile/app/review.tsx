import { View, Text, ScrollView, Image, TouchableOpacity, useWindowDimensions } from 'react-native';
import { useRouter } from 'expo-router';
import { styles } from '../src/styles/reviewStyles';
import { typography } from '../src/design/tokens';
import { i18n, isRTL } from '../src/i18n';
import { useLocalDraft } from '../src/hooks/useLocalDraft';

export default function ReviewScreen() {
  const { width } = useWindowDimensions();
  const isDesktop = width >= 768;
  const router = useRouter();
  const rtl = isRTL();
  const { draft, loaded } = useLocalDraft();

  if (!loaded) {
    return (
      <View style={styles.emptyContainer}>
        <Text style={[typography.body, styles.emptyText]}>Loading…</Text>
      </View>
    );
  }

  if (!draft) {
    return (
      <View style={styles.emptyContainer}>
        <Text style={[typography.body, styles.emptyText, rtl && styles.rtlText]}>
          {i18n.t('create.review.disclaimer')}
        </Text>
        <TouchableOpacity
          style={styles.backButton}
          onPress={() => router.back()}
          accessibilityRole="button"
          accessibilityLabel={i18n.t('common.back')}
        >
          <Text style={styles.backButtonText}>{i18n.t('common.back')}</Text>
        </TouchableOpacity>
      </View>
    );
  }

  const styleLabel = i18n.t(`create.styles.${draft.style}`);

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={[styles.content, isDesktop && styles.desktopContent]}
    >
      <Text style={[typography.subheading, styles.title, rtl && styles.rtlText]}>
        {i18n.t('create.review.title')}
      </Text>

      <View style={styles.localBadge}>
        <Text style={[typography.caption, styles.localBadgeText, rtl && styles.rtlText]}>
          {i18n.t('create.review.localLabel')}
        </Text>
      </View>

      <View style={styles.section}>
        <Text style={[typography.caption, styles.label, rtl && styles.rtlText]}>
          {i18n.t('create.review.prompt')}
        </Text>
        <View style={styles.card}>
          <Text style={[typography.body, styles.cardText, rtl && styles.rtlText]}>
            {draft.prompt.trim() || i18n.t('create.referenceImageFallback')}
          </Text>
        </View>
      </View>

      <View style={styles.section}>
        <Text style={[typography.caption, styles.label, rtl && styles.rtlText]}>
          {i18n.t('create.review.image')}
        </Text>
        {draft.imageUri ? (
          <Image
            source={{ uri: draft.imageUri }}
            style={styles.image}
            resizeMode="cover"
            accessibilityLabel={i18n.t('a11y.selectedImage')}
          />
        ) : (
          <View style={styles.noImage}>
            <Text style={[typography.body, styles.noImageText, rtl && styles.rtlText]}>
              {i18n.t('create.review.noImage')}
            </Text>
          </View>
        )}
      </View>

      <View style={styles.section}>
        <Text style={[typography.caption, styles.label, rtl && styles.rtlText]}>
          {i18n.t('create.review.settings')}
        </Text>
        <View style={styles.settingsCard}>
          <Text style={[typography.body, styles.settingRow, rtl && styles.rtlText]}>
            {i18n.t('create.review.aspect')}: {draft.aspect}
          </Text>
          <Text style={[typography.body, styles.settingRow, rtl && styles.rtlText]}>
            {i18n.t('create.review.duration')}: {draft.duration}
          </Text>
          <Text style={[typography.body, styles.settingRow, rtl && styles.rtlText]}>
            {i18n.t('create.review.style')}: {styleLabel}
          </Text>
        </View>
      </View>

      <Text style={[typography.caption, styles.disclaimer, rtl && styles.rtlText]}>
        {i18n.t('create.review.disclaimer')}
      </Text>

      <TouchableOpacity
        style={styles.backButton}
        onPress={() => router.back()}
        accessibilityRole="button"
        accessibilityLabel={i18n.t('create.review.backToEdit')}
      >
        <Text style={styles.backButtonText}>{i18n.t('create.review.backToEdit')}</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}


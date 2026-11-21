import { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TextInput,
  TouchableOpacity,
  Image,
  Alert,
  useWindowDimensions,
} from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import * as ImagePicker from 'expo-image-picker';
import { colors, spacing, typography, radii } from '../src/design/tokens';
import { i18n, isRTL } from '../src/i18n';
import { validateImageUpload } from '../src/utils/upload';
import type { UploadErrorCode } from '../src/models';
import { setLocalDraft, getLocalDraft, type Duration, type VisualStyle, type Aspect } from '../src/draft';

export default function CreateScreen() {
  const { width } = useWindowDimensions();
  const isDesktop = width >= 768;
  const params = useLocalSearchParams<{ mode?: string; concept?: string }>();
  const router = useRouter();
  const rtl = isRTL();
  const promptRef = useRef<TextInput>(null);
  const imageModeTriggered = useRef(false);

  const existingDraft = getLocalDraft();

  const initialPrompt = (() => {
    if (existingDraft?.prompt) return existingDraft.prompt;
    if (!params.concept) return '';
    const key = `create.concepts.${params.concept}`;
    const translated = i18n.t(key);
    return translated === key ? '' : translated;
  })();

  const [prompt, setPrompt] = useState(initialPrompt);
  const [imageUri, setImageUri] = useState<string | null>(existingDraft?.imageUri ?? null);
  const [duration, setDuration] = useState<Duration>(existingDraft?.duration ?? '30s');
  const [style, setStyle] = useState<VisualStyle>(existingDraft?.style ?? 'cinematic');
  const [aspect, setAspect] = useState<Aspect>(existingDraft?.aspect ?? '9:16');
  const [errorCode, setErrorCode] = useState<UploadErrorCode | 'validation' | null>(null);
  const [selectedConcept, setSelectedConcept] = useState<string | null>(params.concept ?? null);

  const mode = params.mode;

  const pickImage = async () => {
    const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) {
      Alert.alert(i18n.t('create.permissionTitle'), i18n.t('create.permissionMessage'));
      return;
    }

    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsEditing: true,
      quality: 0.8,
    });

    if (!result.canceled && result.assets[0]) {
      const asset = result.assets[0];
      const validation = validateImageUpload(asset.uri, asset.mimeType, asset.fileSize);
      if (!validation.valid) {
        setErrorCode(validation.errorCode ?? 'missing_uri');
        setImageUri(null);
        return;
      }
      setImageUri(asset.uri);
      setErrorCode(null);
    }
  };

  useEffect(() => {
    if (mode === 'text') {
      const timer = setTimeout(() => {
        promptRef.current?.focus();
      }, 300);
      return () => clearTimeout(timer);
    }
  }, [mode]);

  useEffect(() => {
    if (mode === 'image' && !imageModeTriggered.current && !imageUri) {
      imageModeTriggered.current = true;
      void pickImage();
    }
  }, [mode, imageUri]);

  const getErrorMessage = (code: UploadErrorCode | 'validation' | null): string | null => {
    if (!code) return null;
    if (code === 'validation') return i18n.t('create.validationError');
    const key = `create.errors.${code}`;
    const msg = i18n.t(key);
    return msg === key ? i18n.t('create.errors.unknown') : msg;
  };

  const applyConcept = (key: string) => {
    const translated = i18n.t(`create.concepts.${key}`);
    setSelectedConcept(key);
    setPrompt(translated);
  };

  const handleContinue = () => {
    if (!prompt.trim() && !imageUri) {
      setErrorCode('validation');
      return;
    }
    setErrorCode(null);
    setLocalDraft({
      prompt: prompt.trim(),
      imageUri,
      duration,
      style,
      aspect,
    });
    router.push('/review');
  };

  const showConceptChooser = mode === 'concept' && !selectedConcept;

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={[styles.content, isDesktop && styles.desktopContent]}
    >
      <Text style={[typography.subheading, styles.title, rtl && styles.rtlText]}>
        {i18n.t('create.title')}
      </Text>

      {mode === 'text' && (
        <View style={styles.conceptBanner}>
          <Text style={[typography.caption, styles.conceptBannerText, rtl && styles.rtlText]}>
            {i18n.t('create.modeText')}
          </Text>
        </View>
      )}

      {mode === 'image' && (
        <View style={styles.conceptBanner}>
          <Text style={[typography.caption, styles.conceptBannerText, rtl && styles.rtlText]}>
            {i18n.t('create.modeImage')}
          </Text>
        </View>
      )}

      {selectedConcept && (
        <View style={styles.conceptBanner}>
          <Text style={[typography.caption, styles.conceptBannerText, rtl && styles.rtlText]}>
            {i18n.t('create.conceptBanner')}
          </Text>
        </View>
      )}

      {showConceptChooser && (
        <View style={styles.section}>
          <Text style={[typography.caption, styles.sectionLabel, rtl && styles.rtlText]}>
            {i18n.t('create.conceptChoose')}
          </Text>
          <View style={[styles.chipRow, rtl && styles.chipRowRtl]}>
            {(['product', 'social', 'story'] as const).map((key) => (
              <TouchableOpacity
                key={key}
                style={styles.chip}
                onPress={() => applyConcept(key)}
                accessibilityRole="button"
                accessibilityLabel={i18n.t(`home.template${key.charAt(0).toUpperCase() + key.slice(1)}`)}
              >
                <Text style={styles.chipText}>
                  {i18n.t(`home.template${key.charAt(0).toUpperCase() + key.slice(1)}`)}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>
      )}

      {/* Idea / prompt */}
      <View style={styles.section}>
        <Text style={[typography.caption, styles.sectionLabel, rtl && styles.rtlText]}>
          {i18n.t('create.promptLabel')}
        </Text>
        <TextInput
          ref={promptRef}
          style={[styles.input, rtl && styles.rtlInput]}
          placeholder={i18n.t('create.promptPlaceholder')}
          placeholderTextColor={colors.textSecondary}
          value={prompt}
          onChangeText={setPrompt}
          multiline
          numberOfLines={4}
          accessibilityLabel={i18n.t('create.promptLabel')}
          autoFocus={mode === 'text'}
        />
      </View>

      {/* Optional reference image */}
      <View style={styles.section}>
        <Text style={[typography.caption, styles.sectionLabel, rtl && styles.rtlText]}>
          {i18n.t('create.uploadLabel')}
        </Text>
        <TouchableOpacity
          style={[styles.uploadButton, mode === 'image' && styles.uploadButtonEmphasized]}
          onPress={pickImage}
          accessibilityRole="button"
          accessibilityLabel={i18n.t('a11y.uploadButton')}
        >
          <Text style={styles.uploadButtonText}>{i18n.t('create.uploadButton')}</Text>
        </TouchableOpacity>
        {imageUri && (
          <Image
            source={{ uri: imageUri }}
            style={styles.previewImage}
            accessibilityLabel={i18n.t('a11y.selectedImage')}
          />
        )}
      </View>

      {/* Format & Style */}
      <View style={styles.section}>
        <Text style={[typography.subheading, styles.sectionLabel, rtl && styles.rtlText]}>
          {i18n.t('create.settingsTitle')}
        </Text>

        <Text style={[typography.caption, styles.optionLabel, rtl && styles.rtlText]}>
          {i18n.t('create.aspectLabel')}
        </Text>
        <View style={[styles.chipRow, rtl && styles.chipRowRtl]}>
          {(['9:16', '16:9', '1:1'] as Aspect[]).map((a) => (
            <TouchableOpacity
              key={a}
              style={[styles.chip, aspect === a && styles.chipActive]}
              onPress={() => setAspect(a)}
              accessibilityRole="button"
              accessibilityLabel={i18n.t('a11y.aspectChip', { value: a })}
              accessibilityState={{ selected: aspect === a }}
            >
              <Text style={[styles.chipText, aspect === a && styles.chipTextActive]}>{a}</Text>
            </TouchableOpacity>
          ))}
        </View>

        <Text style={[typography.caption, styles.optionLabel, rtl && styles.rtlText]}>
          {i18n.t('create.durationLabel')}
        </Text>
        <View style={[styles.chipRow, rtl && styles.chipRowRtl]}>
          {(['15s', '30s', '60s'] as Duration[]).map((d) => (
            <TouchableOpacity
              key={d}
              style={[styles.chip, duration === d && styles.chipActive]}
              onPress={() => setDuration(d)}
              accessibilityRole="button"
              accessibilityLabel={i18n.t('a11y.durationChip', { value: d })}
              accessibilityState={{ selected: duration === d }}
            >
              <Text style={[styles.chipText, duration === d && styles.chipTextActive]}>{d}</Text>
            </TouchableOpacity>
          ))}
        </View>

        <Text style={[typography.caption, styles.optionLabel, rtl && styles.rtlText]}>
          {i18n.t('create.styleLabel')}
        </Text>
        <View style={[styles.chipRow, rtl && styles.chipRowRtl]}>
          {(['cinematic', 'dynamic', 'minimal'] as VisualStyle[]).map((s) => (
            <TouchableOpacity
              key={s}
              style={[styles.chip, style === s && styles.chipActive]}
              onPress={() => setStyle(s)}
              accessibilityRole="button"
              accessibilityLabel={i18n.t('a11y.styleChip', { value: s })}
              accessibilityState={{ selected: style === s }}
            >
              <Text style={[styles.chipText, style === s && styles.chipTextActive]}>
                {i18n.t(`create.styles.${s}`)}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      </View>

      {/* Local preview */}
      <View style={styles.section}>
        <Text style={[typography.subheading, styles.sectionLabel, rtl && styles.rtlText]}>
          {i18n.t('create.previewTitle')}
        </Text>
        <View style={styles.previewBox}>
          {imageUri ? (
            <Image source={{ uri: imageUri }} style={styles.previewFull} resizeMode="cover" />
          ) : (
            <Text style={[typography.body, styles.previewEmpty, rtl && styles.rtlText]}>
              {i18n.t('create.previewEmpty')}
            </Text>
          )}
          {(prompt || imageUri) && (
            <View style={styles.previewMeta}>
              <Text style={[typography.caption, styles.previewMetaText, rtl && styles.rtlText]} numberOfLines={2}>
                {prompt || i18n.t('create.referenceImageFallback')}
              </Text>
              <Text style={[typography.small, styles.previewMetaSub, rtl && styles.rtlText]}>
                {aspect} · {duration} · {i18n.t(`create.styles.${style}`)}
              </Text>
            </View>
          )}
        </View>
      </View>

      {errorCode && (
        <Text style={styles.errorText} accessibilityRole="alert">
          {getErrorMessage(errorCode)}
        </Text>
      )}

      <TouchableOpacity
        style={styles.continueButton}
        onPress={handleContinue}
        accessibilityRole="button"
        accessibilityLabel={i18n.t('create.generateButton')}
      >
        <Text style={styles.continueButtonText}>{i18n.t('create.generateButton')}</Text>
      </TouchableOpacity>

      <Text style={[typography.caption, styles.disclaimer, rtl && styles.rtlText]}>
        {i18n.t('create.notConnected')}
      </Text>
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

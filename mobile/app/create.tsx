import { useState } from 'react';
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
import * as ImagePicker from 'expo-image-picker';
import { colors, spacing, typography, radii } from '../src/design/tokens';
import { i18n, isRTL } from '../src/i18n';
import { validateImageUpload } from '../src/utils/upload';

export default function CreateScreen() {
  const { width } = useWindowDimensions();
  const isDesktop = width >= 768;

  const [prompt, setPrompt] = useState('');
  const [imageUri, setImageUri] = useState<string | null>(null);
  const [duration, setDuration] = useState<'15s' | '30s' | '60s'>('30s');
  const [style, setStyle] = useState<'cinematic' | 'dynamic' | 'minimal'>('cinematic');
  const [error, setError] = useState<string | null>(null);

  const pickImage = async () => {
    const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) {
      Alert.alert('Permission required', 'Please allow access to your photo library.');
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
        setError(validation.error ?? i18n.t('create.invalidImage'));
        setImageUri(null);
        return;
      }
      setImageUri(asset.uri);
      setError(null);
    }
  };

  const handleGenerate = () => {
    if (!prompt.trim() && !imageUri) {
      setError(i18n.t('create.validationError'));
      return;
    }
    setError(null);
    // Honest: generation is not connected
    Alert.alert(
      i18n.t('create.generateButton'),
      i18n.t('create.notConnected')
    );
  };

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={[styles.content, isDesktop && styles.desktopContent]}
    >
      <Text style={[typography.subheading, styles.title, isRTL() && styles.rtlText]}>
        {i18n.t('create.title')}
      </Text>

      <View style={styles.field}>
        <Text style={[typography.caption, styles.label, isRTL() && styles.rtlText]}>
          {i18n.t('create.promptLabel')}
        </Text>
        <TextInput
          style={[styles.input, isRTL() && styles.rtlInput]}
          placeholder={i18n.t('create.promptPlaceholder')}
          placeholderTextColor={colors.textSecondary}
          value={prompt}
          onChangeText={setPrompt}
          multiline
          numberOfLines={4}
          accessibilityLabel={i18n.t('create.promptLabel')}
        />
      </View>

      <View style={styles.field}>
        <Text style={[typography.caption, styles.label, isRTL() && styles.rtlText]}>
          {i18n.t('create.uploadLabel')}
        </Text>
        <TouchableOpacity style={styles.uploadButton} onPress={pickImage} accessibilityRole="button">
          <Text style={styles.uploadButtonText}>{i18n.t('create.uploadButton')}</Text>
        </TouchableOpacity>
        {imageUri && (
          <Image source={{ uri: imageUri }} style={styles.previewImage} accessibilityLabel="Selected image" />
        )}
      </View>

      <View style={styles.field}>
        <Text style={[typography.subheading, styles.label, isRTL() && styles.rtlText]}>
          {i18n.t('create.settingsTitle')}
        </Text>
        <View style={styles.settingsRow}>
          <Text style={[typography.caption, isRTL() && styles.rtlText]}>{i18n.t('create.durationLabel')}:</Text>
          {(['15s', '30s', '60s'] as const).map((d) => (
            <TouchableOpacity
              key={d}
              style={[styles.chip, duration === d && styles.chipActive]}
              onPress={() => setDuration(d)}
            >
              <Text style={[styles.chipText, duration === d && styles.chipTextActive]}>{d}</Text>
            </TouchableOpacity>
          ))}
        </View>
        <View style={styles.settingsRow}>
          <Text style={[typography.caption, isRTL() && styles.rtlText]}>{i18n.t('create.styleLabel')}:</Text>
          {(['cinematic', 'dynamic', 'minimal'] as const).map((s) => (
            <TouchableOpacity
              key={s}
              style={[styles.chip, style === s && styles.chipActive]}
              onPress={() => setStyle(s)}
            >
              <Text style={[styles.chipText, style === s && styles.chipTextActive]}>{s}</Text>
            </TouchableOpacity>
          ))}
        </View>
      </View>

      <View style={styles.previewArea}>
        <Text style={[typography.subheading, styles.label, isRTL() && styles.rtlText]}>
          {i18n.t('create.previewTitle')}
        </Text>
        <View style={styles.previewPlaceholder}>
          <Text style={[typography.body, styles.previewText, isRTL() && styles.rtlText]}>
            {i18n.t('create.previewEmpty')}
          </Text>
        </View>
      </View>

      {error && (
        <Text style={styles.errorText} accessibilityRole="alert">
          {error}
        </Text>
      )}

      <TouchableOpacity
        style={styles.generateButton}
        onPress={handleGenerate}
        accessibilityRole="button"
        accessibilityLabel={i18n.t('create.generateButton')}
      >
        <Text style={styles.generateButtonText}>{i18n.t('create.generateButton')}</Text>
      </TouchableOpacity>

      <Text style={[typography.caption, styles.disclaimer, isRTL() && styles.rtlText]}>
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
    padding: spacing.lg,
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
  field: {
    marginBottom: spacing.lg,
  },
  label: {
    color: colors.text,
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
    backgroundColor: colors.secondary,
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.lg,
    borderRadius: radii.md,
    alignSelf: 'flex-start',
    minHeight: 44,
    justifyContent: 'center',
  },
  uploadButtonText: {
    color: colors.text,
    fontWeight: '600',
  },
  previewImage: {
    width: 120,
    height: 120,
    borderRadius: radii.md,
    marginTop: spacing.md,
  },
  settingsRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    alignItems: 'center',
    gap: spacing.sm,
    marginBottom: spacing.sm,
  },
  chip: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderRadius: radii.full,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surface,
    minHeight: 44,
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
  previewArea: {
    marginBottom: spacing.lg,
  },
  previewPlaceholder: {
    height: 180,
    backgroundColor: colors.surface,
    borderRadius: radii.md,
    borderWidth: 1,
    borderColor: colors.border,
    borderStyle: 'dashed',
    justifyContent: 'center',
    alignItems: 'center',
    padding: spacing.md,
  },
  previewText: {
    color: colors.textSecondary,
    textAlign: 'center',
  },
  errorText: {
    color: colors.error,
    marginBottom: spacing.md,
    textAlign: 'center',
  },
  generateButton: {
    backgroundColor: colors.primary,
    paddingVertical: spacing.md,
    borderRadius: radii.full,
    alignItems: 'center',
    minHeight: 48,
    justifyContent: 'center',
    marginBottom: spacing.md,
  },
  generateButtonText: {
    color: '#FFFFFF',
    fontSize: 18,
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
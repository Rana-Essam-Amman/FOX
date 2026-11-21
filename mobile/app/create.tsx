import { useState, useEffect, useRef } from 'react';
import { View, Text, ScrollView, TextInput, TouchableOpacity, Alert, useWindowDimensions } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import * as ImagePicker from 'expo-image-picker';
import { styles } from '../src/styles/createStyles';
import { typography } from '../src/design/tokens';
import { i18n, isRTL } from '../src/i18n';
import { validateImageUpload } from '../src/utils/upload';
import type { UploadErrorCode } from '../src/models';
import { setLocalDraft, type Duration, type VisualStyle, type Aspect } from '../src/draft';
import { useLocalDraft } from '../src/hooks/useLocalDraft';
import { CreateForm } from '../src/components/CreateForm';

export default function CreateScreen() {
  const { width } = useWindowDimensions();
  const isDesktop = width >= 768;
  const params = useLocalSearchParams<{ mode?: string; concept?: string }>();
  const router = useRouter();
  const rtl = isRTL();
  const promptRef = useRef<TextInput>(null);
  const imageModeTriggered = useRef(false);
  const { draft: existingDraft, loaded } = useLocalDraft();
  const appliedRef = useRef(false);

  const [prompt, setPrompt] = useState('');
  const [imageUri, setImageUri] = useState<string | null>(null);
  const [duration, setDuration] = useState<Duration>('30s');
  const [style, setStyle] = useState<VisualStyle>('cinematic');
  const [aspect, setAspect] = useState<Aspect>('9:16');
  const [errorCode, setErrorCode] = useState<UploadErrorCode | 'validation' | null>(null);
  const [selectedConcept, setSelectedConcept] = useState<string | null>(params.concept ?? null);

  useEffect(() => {
    if (!loaded || appliedRef.current) return;
    appliedRef.current = true;
    if (existingDraft) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- hydrate once from async storage
      setPrompt(existingDraft.prompt);
      setImageUri(existingDraft.imageUri);
      setDuration(existingDraft.duration);
      setStyle(existingDraft.style);
      setAspect(existingDraft.aspect);
    } else if (params.concept) {
      const key = `create.concepts.${params.concept}`;
      const translated = i18n.t(key);
      if (translated !== key) setPrompt(translated);
    }
  }, [loaded, existingDraft, params.concept]);

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
      const timer = setTimeout(() => promptRef.current?.focus(), 300);
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
    setSelectedConcept(key);
    setPrompt(i18n.t(`create.concepts.${key}`));
  };

  const handleContinue = async () => {
    if (!prompt.trim() && !imageUri) {
      setErrorCode('validation');
      return;
    }
    setErrorCode(null);
    await setLocalDraft({ prompt: prompt.trim(), imageUri, duration, style, aspect });
    router.push('/review');
  };

  const showConceptChooser = mode === 'concept' && !selectedConcept;

  return (
    <ScrollView style={styles.container} contentContainerStyle={[styles.content, isDesktop && styles.desktopContent]}>
      <Text style={[typography.subheading, styles.title, rtl && styles.rtlText]}>{i18n.t('create.title')}</Text>
      {mode === 'text' && <View style={styles.conceptBanner}><Text style={[typography.caption, styles.conceptBannerText, rtl && styles.rtlText]}>{i18n.t('create.modeText')}</Text></View>}
      {mode === 'image' && <View style={styles.conceptBanner}><Text style={[typography.caption, styles.conceptBannerText, rtl && styles.rtlText]}>{i18n.t('create.modeImage')}</Text></View>}
      {selectedConcept && <View style={styles.conceptBanner}><Text style={[typography.caption, styles.conceptBannerText, rtl && styles.rtlText]}>{i18n.t('create.conceptBanner')}</Text></View>}
      {showConceptChooser && (
        <View style={styles.section}>
          <Text style={[typography.caption, styles.sectionLabel, rtl && styles.rtlText]}>{i18n.t('create.conceptChoose')}</Text>
          <View style={[styles.chipRow, rtl && styles.chipRowRtl]}>
            {(['product', 'social', 'story'] as const).map((key) => (
              <TouchableOpacity key={key} style={styles.chip} onPress={() => applyConcept(key)} accessibilityRole="button">
                <Text style={styles.chipText}>{i18n.t(`home.template${key.charAt(0).toUpperCase() + key.slice(1)}`)}</Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>
      )}
      <CreateForm
        prompt={prompt} setPrompt={setPrompt} imageUri={imageUri} onPickImage={() => void pickImage()}
        duration={duration} setDuration={setDuration} style={style} setStyle={setStyle} aspect={aspect} setAspect={setAspect}
        mode={mode} rtl={rtl} promptRef={promptRef}
      />
      {errorCode ? <Text style={styles.errorText} accessibilityRole="alert">{getErrorMessage(errorCode)}</Text> : null}
      <TouchableOpacity style={styles.continueButton} onPress={() => void handleContinue()} accessibilityRole="button">
        <Text style={styles.continueButtonText}>{i18n.t('create.generateButton')}</Text>
      </TouchableOpacity>
      <Text style={[typography.caption, styles.disclaimer, rtl && styles.rtlText]}>{i18n.t('create.notConnected')}</Text>
    </ScrollView>
  );
}

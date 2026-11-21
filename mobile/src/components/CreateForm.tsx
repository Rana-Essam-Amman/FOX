import { View, Text, TextInput, TouchableOpacity, Image } from 'react-native';
import { styles } from '../styles/createStyles';
import { typography, colors } from '../design/tokens';
import { i18n } from '../i18n';
import type { Duration, VisualStyle, Aspect } from '../draft';
import { ChipRow } from './ChipRow';

interface CreateFormProps {
  prompt: string;
  setPrompt: (v: string) => void;
  imageUri: string | null;
  onPickImage: () => void;
  duration: Duration;
  setDuration: (v: Duration) => void;
  style: VisualStyle;
  setStyle: (v: VisualStyle) => void;
  aspect: Aspect;
  setAspect: (v: Aspect) => void;
  mode?: string;
  rtl: boolean;
  promptRef: React.RefObject<TextInput | null>;
}

export function CreateForm({
  prompt, setPrompt, imageUri, onPickImage, duration, setDuration, style, setStyle, aspect, setAspect, mode, rtl, promptRef,
}: CreateFormProps) {
  return (
    <>
      <View style={styles.section}>
        <Text style={[typography.caption, styles.sectionLabel, rtl && styles.rtlText]}>{i18n.t('create.promptLabel')}</Text>
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
      <View style={styles.section}>
        <Text style={[typography.caption, styles.sectionLabel, rtl && styles.rtlText]}>{i18n.t('create.uploadLabel')}</Text>
        <TouchableOpacity style={[styles.uploadButton, mode === 'image' && styles.uploadButtonEmphasized]} onPress={onPickImage} accessibilityRole="button">
          <Text style={styles.uploadButtonText}>{i18n.t('create.uploadButton')}</Text>
        </TouchableOpacity>
        {imageUri ? <Image source={{ uri: imageUri }} style={styles.previewImage} accessibilityLabel={i18n.t('a11y.selectedImage')} /> : null}
      </View>
      <View style={styles.section}>
        <Text style={[typography.subheading, styles.sectionLabel, rtl && styles.rtlText]}>{i18n.t('create.settingsTitle')}</Text>
        <Text style={[typography.caption, styles.optionLabel, rtl && styles.rtlText]}>{i18n.t('create.aspectLabel')}</Text>
        <ChipRow values={['9:16', '16:9', '1:1'] as const} selected={aspect} onSelect={setAspect} labelFor={(v) => v} a11yFor={(v) => i18n.t('a11y.aspectChip', { value: v })} rtl={rtl} />
        <Text style={[typography.caption, styles.optionLabel, rtl && styles.rtlText]}>{i18n.t('create.durationLabel')}</Text>
        <ChipRow values={['15s', '30s', '60s'] as const} selected={duration} onSelect={setDuration} labelFor={(v) => v} a11yFor={(v) => i18n.t('a11y.durationChip', { value: v })} rtl={rtl} />
        <Text style={[typography.caption, styles.optionLabel, rtl && styles.rtlText]}>{i18n.t('create.styleLabel')}</Text>
        <ChipRow values={['cinematic', 'dynamic', 'minimal'] as const} selected={style} onSelect={setStyle} labelFor={(v) => i18n.t(`create.styles.${v}`)} a11yFor={(v) => i18n.t('a11y.styleChip', { value: v })} rtl={rtl} />
      </View>
      <View style={styles.section}>
        <Text style={[typography.subheading, styles.sectionLabel, rtl && styles.rtlText]}>{i18n.t('create.previewTitle')}</Text>
        <View style={styles.previewBox}>
          {imageUri ? <Image source={{ uri: imageUri }} style={styles.previewFull} resizeMode="cover" /> : (
            <Text style={[typography.body, styles.previewEmpty, rtl && styles.rtlText]}>{i18n.t('create.previewEmpty')}</Text>
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
    </>
  );
}

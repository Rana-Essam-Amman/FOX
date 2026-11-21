import { I18n } from 'i18n-js';
import { getLocales } from 'expo-localization';
import AsyncStorage from '@react-native-async-storage/async-storage';

const LOCALE_KEY = '@fox_locale';

const translations = {
  en: {
    home: {
      title: 'FOX',
      subtitle: 'Turn your idea into a video',
      supporting: 'Start with a simple idea, and let FOX help you build the scenes.',
      createAction: 'Start a new project',
      recentProjects: 'Recent Projects',
      emptyProjects: 'Your projects will appear here once you create them.',
      emptyProjectsHint: 'Start with an idea above to begin your first creation.',
      inspiration: 'Inspiration',
      quickStart: 'Quick Start',
      textIdea: 'Start with text',
      imageStart: 'Start with image',
      conceptStart: 'Create from concept',
      templates: 'Templates',
      templateProduct: 'Product Showcase',
      templateSocial: 'Social Reel',
      templateStory: 'Story Moment',
      navHome: 'Home',
      navCreate: 'Create',
    },
    create: {
      title: 'Create Video',
      promptLabel: 'Your idea',
      promptPlaceholder: 'Describe the video you want to create...',
      uploadLabel: 'Reference image (optional)',
      uploadButton: 'Add image',
      settingsTitle: 'Format & Style',
      durationLabel: 'Duration',
      styleLabel: 'Visual style',
      aspectLabel: 'Aspect ratio',
      previewTitle: 'Local preview',
      previewEmpty: 'Your draft preview will appear here. Generation is not connected yet.',
      generateButton: 'Continue',
      notConnected: 'Video generation is not yet connected. This is a local draft preview.',
      validationError: 'Please provide a prompt or an image.',
      aspect16x9: '16:9',
      aspect9x16: '9:16',
      aspect1x1: '1:1',
      errors: {
        missing_uri: 'No file selected or URI is empty.',
        missing_mime: 'Image type could not be verified (missing MIME type).',
        unsupported_mime: 'Unsupported image type. Supported: JPEG, PNG, WebP, GIF.',
        missing_size: 'Image size is missing and could not be verified.',
        invalid_size: 'Image size is invalid (must be a positive finite number).',
        too_large: 'Image must be under 10MB.',
        unknown: 'An unknown validation error occurred.',
      },
    },
    common: {
      language: 'Language',
      english: 'English',
      arabic: 'العربية',
      back: 'Back',
      switchToArabic: 'Switch to Arabic',
      switchToEnglish: 'Switch to English',
    },
    a11y: {
      durationChip: 'Duration {{value}}',
      styleChip: 'Style {{value}}',
      aspectChip: 'Aspect ratio {{value}}',
      uploadButton: 'Select reference image',
      selectedImage: 'Selected reference image',
      quickEntry: 'Quick entry {{label}}',
    },
  },
  ar: {
    home: {
      title: 'فوكس',
      subtitle: 'حوّل فكرتك إلى فيديو',
      supporting: 'ابدأ بفكرة بسيطة، ودع FOX يساعدك في بناء المشاهد.',
      createAction: 'ابدأ مشروعاً جديداً',
      recentProjects: 'المشاريع الأخيرة',
      emptyProjects: 'ستظهر مشاريعك هنا بعد إنشائها.',
      emptyProjectsHint: 'ابدأ بفكرة أعلاه لإنشاء أول عمل لك.',
      inspiration: 'إلهام',
      quickStart: 'بداية سريعة',
      textIdea: 'ابدأ بنص',
      imageStart: 'ابدأ بصورة',
      conceptStart: 'أنشئ من مفهوم',
      templates: 'قوالب',
      templateProduct: 'عرض منتج',
      templateSocial: 'ريل اجتماعي',
      templateStory: 'لحظة قصة',
      navHome: 'الرئيسية',
      navCreate: 'إنشاء',
    },
    create: {
      title: 'إنشاء فيديو',
      promptLabel: 'فكرتك',
      promptPlaceholder: 'صف الفيديو الذي تريد إنشاءه...',
      uploadLabel: 'صورة مرجعية (اختياري)',
      uploadButton: 'إضافة صورة',
      settingsTitle: 'التنسيق والأسلوب',
      durationLabel: 'المدة',
      styleLabel: 'الأسلوب البصري',
      aspectLabel: 'نسبة العرض',
      previewTitle: 'معاينة محلية',
      previewEmpty: 'ستظهر معاينة المسودة هنا. التوليد غير متصل بعد.',
      generateButton: 'متابعة',
      notConnected: 'توليد الفيديو غير متصل بعد. هذه معاينة مسودة محلية.',
      validationError: 'يرجى تقديم وصف أو صورة.',
      aspect16x9: '16:9',
      aspect9x16: '9:16',
      aspect1x1: '1:1',
      errors: {
        missing_uri: 'لم يتم اختيار ملف أو أن الرابط فارغ.',
        missing_mime: 'تعذر التحقق من نوع الصورة (نوع MIME مفقود).',
        unsupported_mime: 'نوع الصورة غير مدعوم. المدعوم: JPEG، PNG، WebP، GIF.',
        missing_size: 'حجم الصورة مفقود وتعذر التحقق منه.',
        invalid_size: 'حجم الصورة غير صالح (يجب أن يكون رقماً موجباً محدوداً).',
        too_large: 'يجب أن تكون الصورة أقل من 10 ميجابايت.',
        unknown: 'حدث خطأ تحقق غير معروف.',
      },
    },
    common: {
      language: 'اللغة',
      english: 'English',
      arabic: 'العربية',
      back: 'رجوع',
      switchToArabic: 'التبديل إلى العربية',
      switchToEnglish: 'التبديل إلى الإنجليزية',
    },
    a11y: {
      durationChip: 'المدة {{value}}',
      styleChip: 'الأسلوب {{value}}',
      aspectChip: 'نسبة العرض {{value}}',
      uploadButton: 'اختيار صورة مرجعية',
      selectedImage: 'الصورة المرجعية المختارة',
      quickEntry: 'مدخل سريع {{label}}',
    },
  },
};

export const i18n = new I18n(translations);

export function detectLocale(): 'en' | 'ar' {
  const code = getLocales()[0]?.languageCode ?? 'en';
  return code.startsWith('ar') ? 'ar' : 'en';
}

export function setupI18n(locale: 'en' | 'ar' = detectLocale()): void {
  i18n.locale = locale;
  i18n.enableFallback = true;
  i18n.defaultLocale = 'en';
}

export function t(key: string, options?: Record<string, string>): string {
  return i18n.t(key, options);
}

export function isRTL(locale: string = i18n.locale): boolean {
  return locale === 'ar';
}

export async function loadSavedLocale(): Promise<'en' | 'ar' | null> {
  try {
    const saved = await AsyncStorage.getItem(LOCALE_KEY);
    if (saved === 'en' || saved === 'ar') return saved;
    return null;
  } catch {
    return null;
  }
}

export async function saveLocale(locale: 'en' | 'ar'): Promise<void> {
  try {
    await AsyncStorage.setItem(LOCALE_KEY, locale);
  } catch {
    // Storage failure is non-fatal; locale still works for the session
  }
}

export async function initializeLocale(): Promise<'en' | 'ar'> {
  const saved = await loadSavedLocale();
  const locale = saved ?? detectLocale();
  setupI18n(locale);
  return locale;
}

// Initialize once at module load so first render is consistent
setupI18n();

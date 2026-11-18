import { I18n } from 'i18n-js';
import { getLocales } from 'expo-localization';
import AsyncStorage from '@react-native-async-storage/async-storage';

const LOCALE_KEY = '@fox_locale';

const translations = {
  en: {
    home: {
      title: 'FOX',
      subtitle: 'Create stunning videos with AI',
      createAction: 'Create Video',
      recentProjects: 'Recent Projects',
      emptyProjects: 'No projects yet. Create your first video to get started.',
      examples: 'Example Content',
      example1: 'Product Showcase',
      example2: 'Social Media Reel',
      navHome: 'Home',
      navCreate: 'Create',
    },
    create: {
      title: 'Create Video',
      promptLabel: 'Describe your video',
      promptPlaceholder: 'A fox running through a bright meadow at sunrise...',
      uploadLabel: 'Upload reference image (optional)',
      uploadButton: 'Select Image',
      settingsTitle: 'Video Settings',
      durationLabel: 'Duration',
      styleLabel: 'Style',
      previewTitle: 'Preview',
      previewEmpty: 'Your video preview will appear here once generation is connected.',
      generateButton: 'Generate Video',
      notConnected: 'Video generation is not yet connected to the backend. This is a preview of the interface.',
      validationError: 'Please provide a prompt or an image.',
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
      uploadButton: 'Select reference image',
      selectedImage: 'Selected reference image',
    },
  },
  ar: {
    home: {
      title: 'فوكس',
      subtitle: 'أنشئ مقاطع فيديو مذهلة بالذكاء الاصطناعي',
      createAction: 'إنشاء فيديو',
      recentProjects: 'المشاريع الأخيرة',
      emptyProjects: 'لا توجد مشاريع بعد. أنشئ أول فيديو للبدء.',
      examples: 'محتوى أمثلة',
      example1: 'عرض منتج',
      example2: 'ريل وسائل التواصل',
      navHome: 'الرئيسية',
      navCreate: 'إنشاء',
    },
    create: {
      title: 'إنشاء فيديو',
      promptLabel: 'صف الفيديو الخاص بك',
      promptPlaceholder: 'ثعلب يركض في مرج مشرق عند شروق الشمس...',
      uploadLabel: 'رفع صورة مرجعية (اختياري)',
      uploadButton: 'اختيار صورة',
      settingsTitle: 'إعدادات الفيديو',
      durationLabel: 'المدة',
      styleLabel: 'الأسلوب',
      previewTitle: 'معاينة',
      previewEmpty: 'ستظهر معاينة الفيديو هنا بمجرد اتصال التوليد.',
      generateButton: 'توليد الفيديو',
      notConnected: 'توليد الفيديو غير متصل بالخلفية بعد. هذه معاينة للواجهة.',
      validationError: 'يرجى تقديم وصف أو صورة.',
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
      uploadButton: 'اختيار صورة مرجعية',
      selectedImage: 'الصورة المرجعية المختارة',
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

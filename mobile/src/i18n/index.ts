import { I18n } from 'i18n-js';
import { getLocales } from 'expo-localization';

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
      imageTooLarge: 'Image must be under 10MB.',
      invalidImage: 'Please select a valid image file.',
    },
    common: {
      language: 'Language',
      english: 'English',
      arabic: 'العربية',
      back: 'Back',
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
      imageTooLarge: 'يجب أن تكون الصورة أقل من 10 ميجابايت.',
      invalidImage: 'يرجى اختيار ملف صورة صالح.',
    },
    common: {
      language: 'اللغة',
      english: 'English',
      arabic: 'العربية',
      back: 'رجوع',
    },
  },
};

export const i18n = new I18n(translations);

export function setupI18n(locale: string = getLocales()[0]?.languageCode ?? 'en') {
  i18n.locale = locale.startsWith('ar') ? 'ar' : 'en';
  i18n.enableFallback = true;
  i18n.defaultLocale = 'en';
}

export function t(key: string): string {
  return i18n.t(key);
}

export function isRTL(): boolean {
  return i18n.locale === 'ar';
}
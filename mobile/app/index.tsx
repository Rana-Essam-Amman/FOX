import { View, Text, ScrollView, TouchableOpacity, useWindowDimensions } from 'react-native';
import { Link, useRouter } from 'expo-router';
import { styles } from '../src/styles/homeStyles';
import { typography } from '../src/design/tokens';
import { i18n, isRTL } from '../src/i18n';
import { QuickCard, TemplateCard } from '../src/components/HomeCards';

export default function HomeScreen() {
  const { width } = useWindowDimensions();
  const isDesktop = width >= 768;
  const router = useRouter();
  const rtl = isRTL();

  const goToCreate = (mode?: string, concept?: string) => {
    const params: Record<string, string> = {};
    if (mode) params.mode = mode;
    if (concept) params.concept = concept;
    router.push({ pathname: '/create', params });
  };

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={[styles.content, isDesktop && styles.desktopContent]}
    >
      <View style={[styles.header, rtl && styles.headerRtl]}>
        <Text style={[typography.heading, styles.wordmark]} accessibilityRole="header">
          {i18n.t('home.title')}
        </Text>
        <View style={styles.headerSpacer} />
      </View>

      <View style={styles.hero}>
        <Text style={[typography.heading, styles.heroTitle, rtl && styles.rtlText]}>
          {i18n.t('home.subtitle')}
        </Text>
        <Text style={[typography.body, styles.heroSupporting, rtl && styles.rtlText]}>
          {i18n.t('home.supporting')}
        </Text>
        <Link href="/create" asChild>
          <TouchableOpacity
            style={styles.primaryCta}
            accessibilityRole="button"
            accessibilityLabel={i18n.t('home.createAction')}
          >
            <Text style={styles.primaryCtaText}>{i18n.t('home.createAction')}</Text>
          </TouchableOpacity>
        </Link>
      </View>

      <View style={styles.section}>
        <Text style={[typography.subheading, styles.sectionTitle, rtl && styles.rtlText]}>
          {i18n.t('home.quickStart')}
        </Text>
        <View style={[styles.quickGrid, isDesktop && styles.quickGridDesktop]}>
          <QuickCard titleKey="home.textIdea" hintKey="home.textIdeaHint" onPress={() => goToCreate('text')} rtl={rtl} />
          <QuickCard titleKey="home.imageStart" hintKey="home.imageStartHint" onPress={() => goToCreate('image')} rtl={rtl} />
          <QuickCard titleKey="home.conceptStart" hintKey="home.conceptStartHint" onPress={() => goToCreate('concept')} rtl={rtl} />
        </View>
      </View>

      <View style={styles.section}>
        <Text style={[typography.subheading, styles.sectionTitle, rtl && styles.rtlText]}>
          {i18n.t('home.recentProjects')}
        </Text>
        <View style={styles.emptyState}>
          <Text style={[typography.body, styles.emptyTitle, rtl && styles.rtlText]}>
            {i18n.t('home.emptyProjects')}
          </Text>
          <Text style={[typography.caption, styles.emptyHint, rtl && styles.rtlText]}>
            {i18n.t('home.emptyProjectsHint')}
          </Text>
        </View>
      </View>

      <View style={styles.section}>
        <Text style={[typography.subheading, styles.sectionTitle, rtl && styles.rtlText]}>
          {i18n.t('home.inspiration')}
        </Text>
        <View style={[styles.templateGrid, isDesktop && styles.templateGridDesktop]}>
          <TemplateCard titleKey="home.templateProduct" hintKey="home.templateProductHint" onPress={() => goToCreate(undefined, 'product')} rtl={rtl} />
          <TemplateCard titleKey="home.templateSocial" hintKey="home.templateSocialHint" accentColor="#FF873D" onPress={() => goToCreate(undefined, 'social')} rtl={rtl} />
          <TemplateCard titleKey="home.templateStory" hintKey="home.templateStoryHint" accentColor="#4A5568" onPress={() => goToCreate(undefined, 'story')} rtl={rtl} />
        </View>
      </View>
    </ScrollView>
  );
}

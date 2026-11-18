import React from 'react';
import renderer, { act } from 'react-test-renderer';
import { Text, View } from 'react-native';
import RootLayout from '../app/_layout';
import { getLocales } from 'expo-localization';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { i18n } from './i18n';

jest.mock('expo-localization', () => ({
  getLocales: jest.fn(() => [{ languageCode: 'en', languageTag: 'en-US' }]),
}));

jest.mock('@react-native-async-storage/async-storage', () => ({
  getItem: jest.fn(() => Promise.resolve(null)),
  setItem: jest.fn(() => Promise.resolve()),
}));

function MockStack({ children }: { children: React.ReactNode }) {
  return (
    <View testID="stack">
      {React.Children.map(children, (child) => {
        if (
          React.isValidElement<{ name?: string; options?: { title?: string } }>(child) &&
          child.props.options?.title
        ) {
          return (
            <Text testID={`screen-title-${child.props.name}`}>
              {child.props.options.title}
            </Text>
          );
        }
        return null;
      })}
    </View>
  );
}
MockStack.displayName = 'MockStack';
(MockStack as unknown as { Screen: React.FC }).Screen = function Screen() { return null; };

jest.mock('expo-router', () => ({
  Stack: MockStack,
}));

jest.mock('expo-status-bar', () => ({
  StatusBar: () => null,
}));

const mockedGetLocales = getLocales as jest.MockedFunction<typeof getLocales>;
const mockedStorage = AsyncStorage as jest.Mocked<typeof AsyncStorage>;

describe('RootLayout locale initialization', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockedGetLocales.mockReturnValue([{ languageCode: 'en', languageTag: 'en-US' } as never]);
    mockedStorage.getItem.mockResolvedValue(null);
    mockedStorage.setItem.mockResolvedValue(undefined as never);
  });

  it('remains in loading state while locale initialization is pending', async () => {
    let resolveStorage: (value: string | null) => void = () => {};
    const pending = new Promise<string | null>((resolve) => {
      resolveStorage = resolve;
    });
    mockedStorage.getItem.mockReturnValue(pending);

    let tree: renderer.ReactTestRenderer;
    await act(async () => {
      tree = renderer.create(<RootLayout />);
    });

    expect(tree!.root.findByProps({ testID: 'locale-loading' })).toBeTruthy();
    expect(() => tree!.root.findByProps({ testID: 'lang-toggle' })).toThrow();
    expect(() => tree!.root.findByProps({ testID: 'stack' })).toThrow();

    await act(async () => {
      resolveStorage(null);
      await pending;
    });
    await act(async () => {
      tree!.unmount();
    });
  });

  it('displays saved Arabic locale on the first visible screen without English-first flash', async () => {
    let resolveStorage: (value: string | null) => void = () => {};
    const pending = new Promise<string | null>((resolve) => {
      resolveStorage = resolve;
    });
    mockedStorage.getItem.mockReturnValue(pending);
    mockedGetLocales.mockReturnValue([{ languageCode: 'en', languageTag: 'en-US' } as never]);

    let tree: renderer.ReactTestRenderer;
    await act(async () => {
      tree = renderer.create(<RootLayout />);
    });

    // Still loading — no English content visible
    expect(tree!.root.findByProps({ testID: 'locale-loading' })).toBeTruthy();
    const textsWhileLoading = tree!.root.findAllByType(Text);
    expect(textsWhileLoading.length).toBe(0);

    await act(async () => {
      resolveStorage('ar');
      await pending;
    });

    // Now visible with Arabic
    expect(() => tree!.root.findByProps({ testID: 'locale-loading' })).toThrow();
    const toggle = tree!.root.findByProps({ testID: 'lang-toggle' });
    expect(toggle).toBeTruthy();
    // Button text when locale is ar shows "English"
    const buttonText = tree!.root.findByProps({ testID: 'lang-toggle' }).findByType(Text);
    expect(buttonText.props.children).toBe('English');
    const homeTitle = tree!.root.findByProps({ testID: 'screen-title-index' });
    expect(homeTitle.props.children).toBe('فوكس');
    expect(i18n.locale).toBe('ar');

    await act(async () => {
      tree!.unmount();
    });
  });

  it('displays saved English locale on the first visible screen without Arabic-first flash', async () => {
    let resolveStorage: (value: string | null) => void = () => {};
    const pending = new Promise<string | null>((resolve) => {
      resolveStorage = resolve;
    });
    mockedStorage.getItem.mockReturnValue(pending);
    mockedGetLocales.mockReturnValue([{ languageCode: 'ar', languageTag: 'ar-SA' } as never]);

    let tree: renderer.ReactTestRenderer;
    await act(async () => {
      tree = renderer.create(<RootLayout />);
    });

    expect(tree!.root.findByProps({ testID: 'locale-loading' })).toBeTruthy();
    const textsWhileLoading = tree!.root.findAllByType(Text);
    expect(textsWhileLoading.length).toBe(0);

    await act(async () => {
      resolveStorage('en');
      await pending;
    });

    expect(() => tree!.root.findByProps({ testID: 'locale-loading' })).toThrow();
    const buttonText = tree!.root.findByProps({ testID: 'lang-toggle' }).findByType(Text);
    expect(buttonText.props.children).toBe('العربية');
    const homeTitle = tree!.root.findByProps({ testID: 'screen-title-index' });
    expect(homeTitle.props.children).toBe('FOX');
    expect(i18n.locale).toBe('en');

    await act(async () => {
      tree!.unmount();
    });
  });

  it('falls back to device locale when storage fails', async () => {
    mockedStorage.getItem.mockRejectedValue(new Error('storage error'));
    mockedGetLocales.mockReturnValue([{ languageCode: 'ar', languageTag: 'ar-SA' } as never]);

    let tree: renderer.ReactTestRenderer;
    await act(async () => {
      tree = renderer.create(<RootLayout />);
      await Promise.resolve();
    });

    const homeTitle = tree!.root.findByProps({ testID: 'screen-title-index' });
    expect(homeTitle.props.children).toBe('فوكس');
    expect(i18n.locale).toBe('ar');

    await act(async () => {
      tree!.unmount();
    });
  });

  it('prevents language toggle from racing with or being overwritten by initialization', async () => {
    let resolveStorage: (value: string | null) => void = () => {};
    const pending = new Promise<string | null>((resolve) => {
      resolveStorage = resolve;
    });
    mockedStorage.getItem.mockReturnValue(pending);
    mockedGetLocales.mockReturnValue([{ languageCode: 'en' } as never]);

    let tree: renderer.ReactTestRenderer;
    await act(async () => {
      tree = renderer.create(<RootLayout />);
    });

    // Toggle is not usable while pending
    expect(() => tree!.root.findByProps({ testID: 'lang-toggle' })).toThrow();

    // Resolve initialization to Arabic
    await act(async () => {
      resolveStorage('ar');
      await pending;
    });

    expect(i18n.locale).toBe('ar');
    const buttonTextBefore = tree!.root.findByProps({ testID: 'lang-toggle' }).findByType(Text);
    expect(buttonTextBefore.props.children).toBe('English');

    // User toggles to English after ready
    const toggle = tree!.root.findByProps({ testID: 'lang-toggle' });
    await act(async () => {
      await toggle.props.onPress();
    });

    expect(i18n.locale).toBe('en');
    const buttonTextAfter = tree!.root.findByProps({ testID: 'lang-toggle' }).findByType(Text);
    expect(buttonTextAfter.props.children).toBe('العربية');

    // Confirm the selection was persisted and not overwritten
    expect(mockedStorage.setItem).toHaveBeenCalledWith('@fox_locale', 'en');

    await act(async () => {
      tree!.unmount();
    });
  });
});

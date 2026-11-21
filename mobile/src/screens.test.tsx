import React from 'react';
import renderer, { act } from 'react-test-renderer';
import { Text } from 'react-native';
import HomeScreen from '../app/index';
import CreateScreen from '../app/create';
import ReviewScreen from '../app/review';

const mockPush = jest.fn();

jest.mock('expo-router', () => ({
  useRouter: () => ({ push: mockPush, back: jest.fn() }),
  useLocalSearchParams: () => ({}),
  Link: ({ children }: { children: React.ReactNode }) => children,
}));

jest.mock('../src/i18n', () => ({
  i18n: { t: (k: string) => k },
  isRTL: () => false,
}));

const mockStore = new Map<string, string>();
jest.mock('@react-native-async-storage/async-storage', () => ({
  setItem: async (k: string, v: string) => { mockStore.set(k, v); },
  getItem: async (k: string) => mockStore.get(k) ?? null,
  removeItem: async (k: string) => { mockStore.delete(k); },
}));

jest.mock('expo-file-system/legacy', () => ({
  documentDirectory: 'file:///mock/',
  getInfoAsync: jest.fn(async () => ({ exists: true })),
  makeDirectoryAsync: jest.fn(async () => undefined),
  copyAsync: jest.fn(async () => undefined),
  deleteAsync: jest.fn(async () => undefined),
}));

jest.mock('expo-image-picker', () => ({
  requestMediaLibraryPermissionsAsync: jest.fn(async () => ({ granted: true })),
  launchImageLibraryAsync: jest.fn(async () => ({ canceled: true })),
  MediaTypeOptions: { Images: 'Images' },
}));

function textOf(tree: renderer.ReactTestRenderer) {
  return tree.root.findAllByType(Text).map((n) => n.props.children).flat().filter(Boolean).join(' ');
}

describe('Home screen', () => {
  it('renders primary actions', () => {
    let tree!: renderer.ReactTestRenderer;
    act(() => {
      tree = renderer.create(<HomeScreen />);
    });
    const text = textOf(tree);
    expect(text).toContain('home.title');
    expect(text).toContain('home.createAction');
    expect(text).toContain('home.textIdea');
  });
});

describe('Create screen', () => {
  it('renders the create form', async () => {
    let tree!: renderer.ReactTestRenderer;
    await act(async () => {
      tree = renderer.create(<CreateScreen />);
    });
    const text = textOf(tree);
    expect(text).toContain('create.title');
    expect(text).toContain('create.generateButton');
  });
});

describe('Review screen', () => {
  it('shows empty state when no draft', async () => {
    mockStore.clear();
    let tree!: renderer.ReactTestRenderer;
    await act(async () => {
      tree = renderer.create(<ReviewScreen />);
    });
    const text = textOf(tree);
    expect(text).toContain('create.review.disclaimer');
  });
});

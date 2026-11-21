import { View, Text, TouchableOpacity } from 'react-native';
import { styles } from '../styles/createStyles';

interface ChipRowProps<T extends string> {
  values: readonly T[];
  selected: T;
  onSelect: (value: T) => void;
  labelFor: (value: T) => string;
  a11yFor: (value: T) => string;
  rtl: boolean;
}

export function ChipRow<T extends string>({ values, selected, onSelect, labelFor, a11yFor, rtl }: ChipRowProps<T>) {
  return (
    <View style={[styles.chipRow, rtl && styles.chipRowRtl]}>
      {values.map((value) => (
        <TouchableOpacity
          key={value}
          style={[styles.chip, selected === value && styles.chipActive]}
          onPress={() => onSelect(value)}
          accessibilityRole="button"
          accessibilityLabel={a11yFor(value)}
          accessibilityState={{ selected: selected === value }}
        >
          <Text style={[styles.chipText, selected === value && styles.chipTextActive]}>
            {labelFor(value)}
          </Text>
        </TouchableOpacity>
      ))}
    </View>
  );
}

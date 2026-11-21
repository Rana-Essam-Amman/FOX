import { useEffect, useState } from 'react';
import { getLocalDraft, setMemoryDraft, type LocalDraft } from '../draft';

export function useLocalDraft() {
  const [draft, setDraft] = useState<LocalDraft | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const d = await getLocalDraft();
      if (!cancelled) {
        setDraft(d);
        setMemoryDraft(d);
        setLoaded(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return { draft, loaded, setDraft };
}

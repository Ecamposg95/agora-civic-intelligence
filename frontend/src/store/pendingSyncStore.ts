import { create } from "zustand";

import { countPending } from "@/offline/queue";
import { drainQueue } from "@/offline/sync";

interface PendingSyncState {
  pending: number;
  syncing: boolean;
  refresh: () => Promise<void>;
  triggerSync: () => Promise<void>;
}

export const usePendingSyncStore = create<PendingSyncState>((set, get) => ({
  pending: 0,
  syncing: false,

  refresh: async () => {
    const count = await countPending();
    set({ pending: count });
  },

  triggerSync: async () => {
    set({ syncing: true });
    try {
      await drainQueue();
    } finally {
      set({ syncing: false });
      await get().refresh();
    }
  },
}));

import { openDB } from "idb";
import type { IDBPDatabase } from "idb";
import type { QueuedRegistro } from "./types";

export type AgoraDB = IDBPDatabase<{ registro_queue: QueuedRegistro }>;

let _db: AgoraDB | null = null;

export async function getDb(): Promise<AgoraDB> {
  if (_db) return _db;
  _db = await openDB<{ registro_queue: QueuedRegistro }>("agora-offline", 1, {
    upgrade(db) {
      const store = db.createObjectStore("registro_queue", {
        keyPath: "client_uuid",
      });
      store.createIndex("by_status", "status");
      store.createIndex("by_created_at", "created_at");
    },
  });
  return _db;
}

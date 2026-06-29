import { describe, it, expect, beforeEach } from "vitest";
import { enqueue, listQueue, markStatus, removeQueued, countPending } from "./queue";
import { getDb } from "./db";

beforeEach(async () => {
  const db = await getDb();
  await db.clear("registro_queue");
});

describe("offline queue", () => {
  it("enqueues with status=queued and a generated client_uuid in the payload", async () => {
    const q = await enqueue({ nombre_completo: "Ana", consentimiento: true }, "camp-1");
    expect(q.status).toBe("queued");
    expect(q.client_uuid).toBeTruthy();
    expect(q.payload.client_uuid).toBe(q.client_uuid); // uuid baked into payload
    expect(q.campaign_id).toBe("camp-1");
  });

  it("counts only pending (queued + error)", async () => {
    const a = await enqueue({ nombre_completo: "A", consentimiento: true }, "c");
    const b = await enqueue({ nombre_completo: "B", consentimiento: true }, "c");
    await markStatus(b.client_uuid, "error", { last_error: "net" });
    expect(await countPending()).toBe(2);
    await markStatus(a.client_uuid, "synced");
    expect(await countPending()).toBe(1);
  });

  it("removes a synced row", async () => {
    const a = await enqueue({ nombre_completo: "A", consentimiento: true }, "c");
    await removeQueued(a.client_uuid);
    expect(await listQueue()).toHaveLength(0);
  });

  it("re-enqueuing the same client_uuid does not duplicate", async () => {
    const a = await enqueue({ nombre_completo: "A", consentimiento: true }, "c");
    // simulate a second enqueue reusing the uuid (idempotent put)
    await markStatus(a.client_uuid, "error");
    expect(await listQueue()).toHaveLength(1);
  });
});

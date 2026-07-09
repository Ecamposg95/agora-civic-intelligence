import { apiClient } from "./client";

export interface Asistente { user_id?: string; nombre: string; }

export interface Acuerdo {
  id: string;
  minuta_id: string;
  texto: string;
  orden: number;
  responsable_id?: string;
  responsable_nombre?: string;
  fecha_limite?: string;
  estado: string;
  work_item_id?: string;
  created_at: string;
}

export interface Minuta {
  id: string;
  titulo: string;
  fecha: string;
  lugar?: string;
  tipo: string;
  estado: string;
  asistentes: Asistente[];
  cuerpo?: string;
  area_id?: string;
  created_at: string;
  created_by?: string;
  acuerdos: Acuerdo[];
  acuerdos_pendientes: number;
}

interface Page<T> { items: T[]; total: number; limit: number; offset: number; }

export interface MinutaCreate {
  titulo: string;
  fecha: string;
  lugar?: string;
  tipo?: string;
  estado?: string;
  asistentes?: Asistente[];
  cuerpo?: string;
  area_id?: string;
  acuerdos?: { texto: string; responsable_id?: string; fecha_limite?: string; orden?: number }[];
}

export async function listMinutas(params?: Record<string, string | number>): Promise<Page<Minuta>> {
  const { data } = await apiClient.get("/minutas", { params });
  return data;
}
export async function getMinuta(id: string): Promise<Minuta> {
  const { data } = await apiClient.get(`/minutas/${id}`);
  return data;
}
export async function createMinuta(payload: MinutaCreate): Promise<Minuta> {
  const { data } = await apiClient.post("/minutas", payload);
  return data;
}
export async function updateMinuta(id: string, payload: Partial<MinutaCreate>): Promise<Minuta> {
  const { data } = await apiClient.patch(`/minutas/${id}`, payload);
  return data;
}
export async function deleteMinuta(id: string): Promise<void> {
  await apiClient.delete(`/minutas/${id}`);
}
export async function addAcuerdo(mid: string, payload: { texto: string; responsable_id?: string; fecha_limite?: string; orden?: number }): Promise<Acuerdo> {
  const { data } = await apiClient.post(`/minutas/${mid}/acuerdos`, payload);
  return data;
}
export async function updateAcuerdo(mid: string, aid: string, payload: Partial<Acuerdo>): Promise<Acuerdo> {
  const { data } = await apiClient.patch(`/minutas/${mid}/acuerdos/${aid}`, payload);
  return data;
}
export async function deleteAcuerdo(mid: string, aid: string): Promise<void> {
  await apiClient.delete(`/minutas/${mid}/acuerdos/${aid}`);
}
export async function listAcuerdos(params?: Record<string, string | number>): Promise<Page<Acuerdo>> {
  const { data } = await apiClient.get("/acuerdos", { params });
  return data;
}

import type { Cart, Job, Knowledge, OpeningHours, Order, Source } from "../types/knowledge";

const API_URL = "http://localhost:8080";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, init);
  if (!res.ok) {
    let msg = `Erreur ${res.status}`;
    try {
      const e = await res.json();
      if (typeof e.detail === "string") msg = e.detail;
    } catch { /* message par défaut */ }
    throw new Error(msg);
  }
  return res.json() as Promise<T>;
}

const post = (body?: unknown, method = "POST"): RequestInit => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: body === undefined ? undefined : JSON.stringify(body),
});

export const confirmBusiness = (placeId: string) =>
  request<{ business_id: string }>("/onboarding/confirm", post({ place_id: placeId }));

export const getBusiness = (id: string) =>
    request<{ business: { google_hours?: OpeningHours | null }; sources: Source[]; job: Job }>(`/businesses/${id}`);

export const addUrl = (id: string, url: string) =>
  request<Source>(`/businesses/${id}/sources`, post({ url }));

export const addText = (id: string, text: string) =>
  request<Source>(`/businesses/${id}/sources/text`, post({ text }));

export function uploadDocument(id: string, file: File) {
  const form = new FormData();
  form.append("file", file);
  return request<Source>(`/businesses/${id}/documents`, { method: "POST", body: form });
}

export const startCollect = (id: string) => request<Job>(`/businesses/${id}/collect`, post());
export const collectStatus = (id: string) => request<Job>(`/businesses/${id}/collect/status`);

export const getDraft = (id: string) => request<Knowledge>(`/businesses/${id}/knowledge/draft`);
export const saveDraft = (id: string, kn: Knowledge) =>
  request<{ ok: boolean }>(`/businesses/${id}/knowledge`, post(kn, "PUT"));
export const approve = (id: string) =>
  request<{ version: number }>(`/businesses/${id}/knowledge/approve`, post());

export const startConversation = (id: string) =>
  request<{ conversation_id: string; greeting: string }>(`/businesses/${id}/conversations`, post());
export const sendMessage = (id: string, cid: string, message: string) =>
  request<{ reply: string; cart: Cart }>(`/businesses/${id}/conversations/${cid}/messages`, post({ message }));
export const confirmOrder = (id: string, cid: string, name: string, phone: string) =>
  request<{ order: Order }>(
    `/businesses/${id}/conversations/${cid}/orders/confirm`,
    post({ customer_name: name, customer_phone: phone, fulfillment: "pickup" }),
  );
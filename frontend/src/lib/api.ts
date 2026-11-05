import type { PaginatedResponse, ProductDetail, ProductListItem } from "@/types/catalog";

const API_URL = process.env.INTERNAL_API_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers ?? {}),
    },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API error ${res.status}: ${text}`);
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// Catalog
// ---------------------------------------------------------------------------

export type ProductFilters = {
  species?: string;
  value_tier?: string;
  listing_status?: string;
  search?: string;
  page?: number;
};

export function getProducts(filters: ProductFilters = {}): Promise<PaginatedResponse<ProductListItem>> {
  const params = new URLSearchParams();
  if (filters.species)        params.set("species", filters.species);
  if (filters.value_tier)     params.set("value_tier", filters.value_tier);
  if (filters.listing_status) params.set("listing_status", filters.listing_status);
  if (filters.search)         params.set("search", filters.search);
  if (filters.page)           params.set("page", String(filters.page));
  const qs = params.toString();
  return apiFetch<PaginatedResponse<ProductListItem>>(`/api/v1/products/${qs ? `?${qs}` : ""}`);
}

export function getProduct(slug: string): Promise<ProductDetail> {
  return apiFetch<ProductDetail>(`/api/v1/products/${slug}/`);
}

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

export type LoginPayload   = { email: string; password: string };
export type RegisterPayload = { email: string; password: string; full_name?: string };
export type TokenPair      = { access: string; refresh: string };

export function login(payload: LoginPayload): Promise<TokenPair> {
  return apiFetch<TokenPair>("/api/v1/auth/login/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function register(payload: RegisterPayload): Promise<{ id: number; email: string }> {
  return apiFetch("/api/v1/auth/register/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function refreshToken(refresh: string): Promise<{ access: string }> {
  return apiFetch("/api/v1/auth/token/refresh/", {
    method: "POST",
    body: JSON.stringify({ refresh }),
  });
}

// ---------------------------------------------------------------------------
// Order tracking (public)
// ---------------------------------------------------------------------------

export function getOrderTracking(orderRef: string) {
  return apiFetch(`/api/v1/tracking/${orderRef}/`);
}

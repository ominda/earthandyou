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
  search?: string;
  page?: number;
};

export function getProducts(filters: ProductFilters = {}): Promise<PaginatedResponse<ProductListItem>> {
  const params = new URLSearchParams();
  if (filters.species)    params.set("species", filters.species);
  if (filters.value_tier) params.set("value_tier", filters.value_tier);
  if (filters.search)     params.set("search", filters.search);
  if (filters.page)       params.set("page", String(filters.page));
  const qs = params.toString();
  return apiFetch<PaginatedResponse<ProductListItem>>(`/api/v1/catalog/products/${qs ? `?${qs}` : ""}`);
}

export function getProduct(slug: string): Promise<ProductDetail> {
  return apiFetch<ProductDetail>(`/api/v1/catalog/products/${slug}/`);
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

export type RegisterFullPayload = { email: string; password: string; password_confirm: string; first_name?: string; last_name?: string };

export function registerFull(payload: RegisterFullPayload): Promise<{ id: number; email: string }> {
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
// Cart
// ---------------------------------------------------------------------------

export function getCart(token: string): Promise<import("@/types/commerce").Cart> {
  return apiFetch("/api/v1/cart/", { headers: { Authorization: `Bearer ${token}` }, cache: "no-store" });
}

export function addToCart(token: string, productId: number): Promise<unknown> {
  return apiFetch("/api/v1/cart/items/", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({ product_id: productId }),
  });
}

export function removeFromCart(token: string, productId: number): Promise<unknown> {
  return apiFetch(`/api/v1/cart/items/${productId}/`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
}

// ---------------------------------------------------------------------------
// Reservation
// ---------------------------------------------------------------------------

export function createReservation(token: string, productId: number): Promise<import("@/types/commerce").Reservation> {
  return apiFetch("/api/v1/reservations/", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({ product_id: productId }),
  });
}

// ---------------------------------------------------------------------------
// Checkout
// ---------------------------------------------------------------------------

export function createCheckout(
  token: string,
  reservationId: number,
  shippingAddressId: number,
  billingAddressId?: number
): Promise<import("@/types/commerce").CheckoutSession> {
  return apiFetch("/api/v1/checkout/", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({
      reservation_id: reservationId,
      shipping_address_id: shippingAddressId,
      billing_address_id: billingAddressId,
    }),
  });
}

export function placeOrder(token: string, checkoutSessionId: number): Promise<import("@/types/commerce").Order> {
  return apiFetch("/api/v1/orders/", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({ checkout_session_id: checkoutSessionId }),
  });
}

export function getAddresses(token: string): Promise<import("@/types/commerce").CustomerAddress[]> {
  return apiFetch("/api/v1/auth/me/addresses/", { headers: { Authorization: `Bearer ${token}` }, cache: "no-store" });
}

export function createAddress(token: string, data: Partial<import("@/types/commerce").CustomerAddress>): Promise<import("@/types/commerce").CustomerAddress> {
  return apiFetch("/api/v1/auth/me/addresses/", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify(data),
  });
}

export function updateAddress(token: string, id: number, data: Partial<import("@/types/commerce").CustomerAddress>): Promise<import("@/types/commerce").CustomerAddress> {
  return apiFetch(`/api/v1/auth/me/addresses/${id}/`, {
    method: "PATCH",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify(data),
  });
}

export function deleteAddress(token: string, id: number): Promise<void> {
  return apiFetch(`/api/v1/auth/me/addresses/${id}/`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function getMe(token: string): Promise<{ id: number; email: string; first_name: string; last_name: string; full_name: string; is_email_verified: boolean }> {
  return apiFetch("/api/v1/auth/me/", { headers: { Authorization: `Bearer ${token}` }, cache: "no-store" });
}

export function updateMe(token: string, data: { first_name?: string; last_name?: string }): Promise<unknown> {
  return apiFetch("/api/v1/auth/me/", {
    method: "PATCH",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify(data),
  });
}

// ---------------------------------------------------------------------------
// Orders
// ---------------------------------------------------------------------------

export function getOrders(token: string): Promise<import("@/types/commerce").Order[]> {
  return apiFetch("/api/v1/orders/", { headers: { Authorization: `Bearer ${token}` }, cache: "no-store" });
}

export function getOrder(token: string, id: number): Promise<import("@/types/commerce").Order> {
  return apiFetch(`/api/v1/orders/${id}/`, { headers: { Authorization: `Bearer ${token}` }, cache: "no-store" });
}

// ---------------------------------------------------------------------------
// Order tracking (public)
// ---------------------------------------------------------------------------

export function getOrderTracking(orderRef: string) {
  return apiFetch(`/api/v1/tracking/${orderRef}/`, { cache: "no-store" });
}

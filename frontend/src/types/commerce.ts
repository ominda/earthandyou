export interface CartItem {
  id: number;
  product_id: number;
  gemstone_id: string;
  headline: string;
  price_usd: string;
  slug: string;
  added_at: string;
}

export interface Cart {
  id: number;
  item_count: number;
  total_usd: string;
  items: CartItem[];
  updated_at: string;
}

export interface Reservation {
  id: number;
  gemstone_id: string;
  headline: string;
  price_usd: string;
  status: string;
  is_active: boolean;
  expires_at: string;
  created_at: string;
}

export interface CustomerAddress {
  id: number;
  recipient_name: string;
  phone: string;
  line1: string;
  line2: string;
  city: string;
  state: string;
  postal_code: string;
  country: string;
  is_default: boolean;
}

export interface CheckoutSession {
  id: number;
  gemstone_id: string;
  headline: string;
  shipping_address: Record<string, string>;
  billing_address: Record<string, string>;
  subtotal_usd: string;
  shipping_usd: string;
  total_usd: string;
  status: string;
  is_active: boolean;
  expires_at: string;
  created_at: string;
}

export interface OrderStatusLog {
  from_status: string;
  to_status: string;
  actor: string;
  notes: string;
  created_at: string;
}

export interface Order {
  id: number;
  order_ref: string;
  gemstone_id: string;
  product_headline: string;
  product_slug: string;
  subtotal_usd: string;
  shipping_usd: string;
  total_usd: string;
  shipping_address: Record<string, string>;
  billing_address: Record<string, string>;
  status: string;
  payment_reference: string;
  status_logs: OrderStatusLog[];
  created_at: string;
}

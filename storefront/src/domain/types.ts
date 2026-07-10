export interface StoreSettings {
  store_name: string;
  logo_url: string | null;
  favicon_url: string | null;
  primary_color: string;
  accent_color: string;
  font_choice: string;
  banner_images: string[];
  announcement_bar_text: string | null;
  social_links: Record<string, string>;
  enabled_sections: Record<string, boolean>;
}

export interface Product {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  price: string;
  compare_at_price: string | null;
  images: string[];
  category_id: string | null;
  in_stock: boolean;
}

export interface ProductPage {
  items: Product[];
  total: number;
}

export interface Category {
  id: string;
  name: string;
  slug: string;
  parent_id: string | null;
}

export interface CartLineItem {
  product_id: string;
  quantity: number;
}

export interface Cart {
  id: string;
  line_items: CartLineItem[];
}

export type OrderStatus = "pending" | "paid" | "fulfilled" | "cancelled" | "refunded";

export interface OrderLineItem {
  product_id: string;
  product_name: string;
  unit_price: string;
  quantity: number;
  line_total: string;
}

export interface Order {
  id: string;
  customer_id: string;
  status: OrderStatus;
  payment_status: string;
  line_items: OrderLineItem[];
  subtotal: string;
  tax: string;
  shipping: string;
  total: string;
}

export interface OrderPage {
  items: Order[];
  total: number;
}

export interface ShippingAddress {
  line1: string;
  line2?: string | null;
  city: string;
  state: string;
  postal_code: string;
  country: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

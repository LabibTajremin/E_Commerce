export type ProductStatus = "draft" | "published";

export interface Product {
  id: string;
  tenant_id: string;
  name: string;
  slug: string;
  description: string | null;
  price: string;
  compare_at_price: string | null;
  sku: string | null;
  images: string[];
  stock_qty: number;
  status: ProductStatus;
  category_id: string | null;
}

export interface ProductPage {
  items: Product[];
  total: number;
}

export interface ProductInput {
  name: string;
  price: string;
  slug?: string | null;
  description?: string | null;
  compare_at_price?: string | null;
  sku?: string | null;
  stock_qty?: number;
  category_id?: string | null;
}

export interface Category {
  id: string;
  tenant_id: string;
  name: string;
  slug: string;
  parent_id: string | null;
}

export interface CategoryInput {
  name: string;
  slug?: string | null;
  parent_id?: string | null;
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

export interface Theme {
  id: string;
  name: string;
  layout_type: "grid" | "list" | "minimal";
  sections: Record<string, boolean>;
}

export interface StoreSettings {
  tenant_id: string;
  theme_id: string;
  store_name: string;
  logo_url: string | null;
  favicon_url: string | null;
  primary_color: string;
  accent_color: string;
  font_choice: string;
  banner_images: string[];
  announcement_bar_text: string | null;
  social_links: Record<string, string>;
  seo_meta: Record<string, string>;
  enabled_sections: Record<string, boolean>;
}

export interface BrandingInput {
  store_name?: string | null;
  primary_color?: string | null;
  accent_color?: string | null;
  font_choice?: string | null;
  announcement_bar_text?: string | null;
}

export interface SubscriptionPlan {
  id: string;
  name: string;
  price: string;
  max_products: number;
  max_banners: number;
  custom_domain_allowed: boolean;
}

export interface TenantSubscription {
  plan_id: string;
  status: string;
  current_period_end: string | null;
}

export interface CurrentAdmin {
  user_id: string;
  tenant_id: string;
  role: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

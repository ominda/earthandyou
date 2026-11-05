export type ValueTier = "standard" | "premium" | "luxury" | "ultra_luxury";
export type ListingStatus = "active" | "sold_out" | "unlisted";

export interface PrimaryMedia {
  s3_key: string;
  alt_text: string;
}

export interface ProductMedia {
  id: number;
  media_type: "photo" | "video" | "certificate";
  s3_key: string;
  alt_text: string;
  display_order: number;
  is_primary: boolean;
}

export interface CertificationReport {
  id: number;
  laboratory_name: string;
  laboratory_code: string;
  report_number: string;
  report_type: string;
  issue_date: string;
  natural_status: string;
  treatment_status: string;
  treatment_details: string;
  origin_country: string;
  reported_carat_weight: string;
  reported_dimensions: string;
  verification_status: string;
  verification_url: string;
  is_primary: boolean;
}

export interface Provenance {
  confidence: string;
  origin_country: string;
  source_region: string;
  mine_locality: string;
  customer_description: string;
}

export interface ProductListItem {
  id: number;
  gemstone_id: string;
  slug: string;
  species: string;
  species_code: string;
  variety: string | null;
  headline: string;
  price_usd: string;
  value_tier: ValueTier;
  listing_status: ListingStatus;
  is_available: boolean;
  primary_media: PrimaryMedia | null;
}

export interface ProductDetail extends ProductListItem {
  description: string;
  meta_title: string;
  meta_description: string;
  media: ProductMedia[];
  certification_reports: CertificationReport[];
  provenance: Provenance | null;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface BusinessSearchResult {
    place_id: string;
    name: string | null;
    address: string | null;
    short_address: string | null;
    category: string | null;
    business_status: string | null;
    latitude: number | null;
    longitude: number | null;
  }
  
  export interface OpeningHour {
    day: string;
    opens_at: string | null;
    closes_at: string | null;
    closes_next_day: boolean;
  }
  
  export interface BusinessDetails extends BusinessSearchResult {
    street: string | null;
    street_number: string | null;
    postal_code: string | null;
    city: string | null;
    country: string | null;
    phone: string | null;
    international_phone: string | null;
    phone_normalized: string | null;
    website: string | null;
    google_maps_url: string | null;
    rating: number | null;
    review_count: number | null;
    opening_hours: OpeningHour[];
    is_open_now: boolean | null;
    timezone: string | null;
  }
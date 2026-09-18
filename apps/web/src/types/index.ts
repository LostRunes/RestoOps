export interface User {
  id: string;
  email: string;
  full_name: string;
  role: "OWNER" | "ADMIN" | "AGENT";
  organization_id: string;
  created_at: string;
}

export interface Organization {
  id: string;
  name: string;
  slug: string;
  domain?: string;
  smtp_host?: string;
  smtp_port?: number;
  smtp_username?: string;
  created_at: string;
}

export interface Lead {
  id: string;
  organization_id: string;
  restaurant_id?: string;
  company_name: string;
  contact_name: string;
  email: string;
  phone?: string;
  address?: string;
  city?: string;
  state?: string;
  zip_code?: string;
  status: "NEW" | "VERIFYING" | "VERIFIED" | "SCORE_QUEUED" | "SCORED" | "CAMPAIGN_QUEUED" | "ENGAGED" | "QUOTED" | "WON" | "LOST";
  score: number;
  priority: "HOT" | "HIGH" | "MEDIUM" | "LOW";
  verification_status: "VALID" | "INVALID" | "RISKY" | "UNKNOWN" | "UNVERIFIED";
  verification_details?: Record<string, any>;
  custom_attributes?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface CampaignStep {
  id: string;
  step_number: number;
  type: "EMAIL" | "CALL";
  delay_days: number;
  subject_template?: string;
  body_template: string;
}

export interface Campaign {
  id: string;
  organization_id: string;
  name: string;
  description?: string;
  status: "DRAFT" | "SCHEDULED" | "RUNNING" | "PAUSED" | "COMPLETED" | "CANCELLED";
  target_filter?: Record<string, any>;
  total_leads_targeted: number;
  leads_processed: number;
  steps: CampaignStep[];
  started_at?: string;
  completed_at?: string;
  created_at: string;
}

export interface Message {
  id: string;
  conversation_id: string;
  sender_type: "CUSTOMER" | "AGENT" | "AI";
  sender_name?: string;
  channel: "EMAIL" | "WHATSAPP" | "WEB_CHAT";
  content: string;
  metadata?: Record<string, any>;
  created_at: string;
}

export interface Conversation {
  id: string;
  organization_id: string;
  lead_id: string;
  lead?: Lead;
  channel: "EMAIL" | "WHATSAPP" | "WEB_CHAT";
  status: "OPEN" | "WAITING_ON_CUSTOMER" | "RESOLVED" | "CLOSED";
  last_message_at?: string;
  messages?: Message[];
  created_at: string;
}

export interface QuoteItem {
  id?: string;
  name: string;
  description?: string;
  category?: string;
  quantity: number;
  unit_price: number;
  total: number;
}

export interface Quote {
  id: string;
  organization_id: string;
  lead_id: string;
  lead?: Lead;
  quote_number: string;
  status: "DRAFT" | "SENT" | "VIEWED" | "ACCEPTED" | "REJECTED" | "EXPIRED";
  event_type?: string;
  event_date?: string;
  guest_count?: number;
  items: QuoteItem[];
  subtotal: number;
  tax: number;
  delivery_fee: number;
  discount: number;
  total: number;
  notes?: string;
  terms?: string;
  valid_until?: string;
  sent_at?: string;
  accepted_at?: string;
  created_at: string;
}

export interface Order {
  id: string;
  organization_id: string;
  quote_id: string;
  quote_number?: string;
  lead_id: string;
  lead?: Lead;
  order_number: string;
  status: "CONFIRMED" | "IN_PREPARATION" | "OUT_FOR_DELIVERY" | "DELIVERED" | "CANCELLED";
  total_amount: number;
  event_date?: string;
  delivery_address?: string;
  created_at: string;
}

export interface Call {
  id: string;
  organization_id: string;
  lead_id: string;
  lead?: Lead;
  provider: "EXOTEL" | "WEBRTC";
  direction: "OUTBOUND" | "INBOUND";
  status: "INITIATED" | "RINGING" | "IN_PROGRESS" | "COMPLETED" | "FAILED" | "BUSY" | "NO_ANSWER";
  duration_seconds: number;
  external_call_id?: string;
  room_id?: string;
  recording_url?: string;
  created_at: string;
}

export interface Notification {
  id: string;
  organization_id: string;
  user_id?: string;
  type: string;
  title: string;
  body: string;
  entity_type?: string;
  entity_id?: string;
  read: boolean;
  metadata?: Record<string, any>;
  created_at: string;
}

export interface AIAction {
  id: string;
  ai_run_id: string;
  tool_name: string;
  description: string;
  payload: Record<string, any>;
  status: "PROPOSED" | "APPROVED" | "REJECTED" | "EXECUTED" | "FAILED";
  result?: Record<string, any>;
  rejection_reason?: string;
  approved_by?: string;
  approved_at?: string;
  created_at: string;
}

export interface AIRun {
  id: string;
  organization_id: string;
  agent_type: string;
  model_name: string;
  conversation_id?: string;
  prompt_summary?: string;
  latency_ms: number;
  token_count: number;
  status: "SUCCESS" | "FAILED";
  error_message?: string;
  actions?: AIAction[];
  created_at: string;
}

export interface JobProgress {
  job_id: string;
  job_type: string;
  status: "PENDING" | "RUNNING" | "COMPLETED" | "FAILED";
  total: number;
  processed: number;
  percentage: number;
  details?: Record<string, any>;
}

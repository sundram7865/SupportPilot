export type Organization = {
  id: string;
  name?: string;
  slug?: string;
  role?: string;
};

export type AuthMeResponse = {
  user: {
    id: string;
    clerk_user_id?: string | null;
    email: string;
    name?: string | null;
    avatar_url?: string | null;
  };
  organizations?: Organization[];
  memberships?: Array<{
    organization_id?: string;
    role?: string;
    status?: string;
    organization?: Organization;
  }>;
  organization?: Organization;
};

export type Ticket = {
  id: string;
  organization_id: string;
  ticket_number?: string;
  subject: string;
  description?: string | null;
  customer_name?: string | null;
  customer_email?: string | null;
  customer_phone?: string | null;
  external_order_id?: string | null;
  status: string;
  priority: string;
  category: string;
  source: string;
  created_at: string;
  updated_at?: string;
  messages?: TicketMessage[];
};

export type TicketMessage = {
  id: string;
  sender_type: string;
  sender_user_id?: string | null;
  sender_name?: string | null;
  sender_email?: string | null;
  body: string;
  is_public?: boolean;
  created_at: string;
};

export type TimelineEvent = {
  id: string;
  actor_user_id: string | null;
  event_type: string;
  title: string;
  description: string | null;
  old_value: string | null;
  new_value: string | null;
  created_at: string;
};

export type AgentRun = {
  id: string;
  organization_id?: string;
  ticket_id: string;
  started_by_user_id?: string | null;
  status: string;
  provider?: string;
  model_name?: string | null;
  detected_category?: string | null;
  detected_priority?: string | null;
  risk_level?: string | null;
  decision?: string | null;
  draft_response?: string | null;
  reasoning_summary?: string | null;
  planned_tools?: Array<Record<string, unknown>> | null;
  retrieved_context?: Array<Record<string, unknown>> | null;
  final_state?: Record<string, unknown> | null;
  error_message?: string | null;
  duration_ms?: number | null;
  created_at?: string;
  completed_at?: string | null;
  steps?: AgentRunStep[];
};
export type ToolExecution = {
  id: string;
  ticket_id: string | null;
  agent_run_id: string | null;
  tool_name: string;
  risk_level: string;
  status: string;
  approval_status: string;
  input_args?: any;
  output_json?: any;
  error_message?: string | null;
  created_at: string;
};

export type ApprovalRequest = {
  id: string;
  ticket_id: string | null;
  tool_execution_id: string | null;
  status: string;
  title: string;
  description: string | null;
  risk_level: string;
  tool_name: string | null;
  input_args?: any;
  result_json?: any;
  request_reason?: string | null;
  decision_reason?: string | null;
  created_at: string;
};

export type ReplyDraft = {
  id: string;
  organization_id?: string;
  ticket_id: string;
  agent_run_id: string | null;
  approval_request_id: string | null;

  created_by_user_id?: string | null;
  updated_by_user_id?: string | null;
  approved_by_user_id?: string | null;
  rejected_by_user_id?: string | null;
  sent_by_user_id?: string | null;

  source: string;
  status: string;
  subject: string | null;
  body: string;

  rejection_reason?: string | null;
  approval_reason?: string | null;
  send_notes?: string | null;
  metadata_json?: Record<string, unknown> | null;

  sent_message_id: string | null;

  created_at: string;
  updated_at?: string;
  approved_at?: string | null;
  rejected_at?: string | null;
  sent_at?: string | null;
};

export type OrganizationDetails = {
  id: string;
  name: string;
  slug: string;
  support_email?: string | null;
  plan?: string;
};

export type OrganizationMemberUser = {
  id: string;
  clerk_user_id?: string | null;
  email: string;
  name?: string | null;
  avatar_url?: string | null;
};

export type OrganizationMember = {
  id: string;
  organization_id: string;
  user_id: string;
  role: string;
  status: string;
  user?: OrganizationMemberUser | null;
};

export type OrganizationInvitation = {
  id: string;
  organization_id: string;
  email: string;
  name?: string | null;
  role: string;
  status: string;
  invited_by_user_id?: string | null;
  accepted_by_user_id?: string | null;
  accepted_at?: string | null;
  created_at?: string | null;
};

export type InviteMemberResult = {
  type: "membership" | "invitation";
  created: boolean;
  message: string;
  membership?: OrganizationMember | null;
  invitation?: OrganizationInvitation | null;
};

export type IntegrationConnection = {
  id: string;
  organization_id: string;
  provider: string;
  base_url: string;
  status: string;
  last_health_status?: string | null;
  last_health_message?: string | null;
  last_checked_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
};

export type UrbanKartConnectionPayload = {
  base_url: string;
  api_key: string;
};

export type UrbanKartHealthResponse = {
  success?: boolean;
  status?: string;
  message?: string;
  provider?: string;
  base_url?: string;
  checked_at?: string | null;
  details?: unknown;
};

export type ExternalApiLog = {
  id: string;
  organization_id: string;
  provider?: string;
  method?: string;
  url?: string;
  endpoint?: string;
  status?: string;
  status_code?: number | null;
  duration_ms?: number | null;
  error_message?: string | null;
  created_at?: string | null;
};

export type KnowledgeDocument = {
  id: string;
  organization_id?: string;
  title: string;
  document_type: string;
  status: string;
  content?: string | null;
  source_url?: string | null;
  version?: number | null;
  ingestion_status?: string | null;
  ingestion_error?: string | null;
  chunk_count?: number | null;
  metadata_json?: Record<string, unknown> | null;
  created_by_user_id?: string | null;
  updated_by_user_id?: string | null;
  ingested_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
};

export type KnowledgeChunk = {
  id: string;
  document_id: string;
  organization_id?: string;
  chunk_index?: number;
  content: string;
  token_count?: number | null;
  created_at?: string | null;
};

export type KnowledgeSearchResult = {
  chunk_id: string;
  document_id: string;
  document_title: string;
  document_type: string;
  chunk_index: number;
  content: string;
  score: number;
};

export type CreateKnowledgeDocumentPayload = {
  title: string;
  document_type: string;
  content: string;
  source_url?: string | null;
};

export type PublicOrganization = {
  id: string;
  name: string;
  slug: string;
  support_email?: string | null;
};

export type PublicTicketCreatePayload = {
  subject: string;
  description: string;
  customer_name?: string | null;
  customer_email: string;
  customer_phone?: string | null;
  external_order_id?: string | null;
  metadata_json?: Record<string, unknown> | null;
};

export type PublicTicketCreateResponse = {
  id: string;
  organization_id: string;
  ticket_number: string;
  subject: string;
  status: string;
  priority: string;
  category: string;
  source: string;
  customer_email: string;
  external_order_id?: string | null;
  created_at?: string | null;
  message: string;
};

export type TicketListResponse = {
  items: Ticket[];
  total: number;
  limit: number;
  offset: number;
};


export type AgentRunStep = {
  id: string;
  step_name: string;
  status: string;
  input_json?: Record<string, unknown> | null;
  output_json?: Record<string, unknown> | null;
  error_message?: string | null;
  duration_ms?: number | null;
  created_at: string;
  completed_at?: string | null;
};


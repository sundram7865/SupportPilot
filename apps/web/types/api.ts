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
  ticket_id: string;
  status: string;
  decision?: string | null;
  risk_level?: string | null;
  detected_category?: string | null;
  detected_priority?: string | null;
  draft_response?: string | null;
  planned_tools?: any[];
  final_state?: any;
  created_at?: string;
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
  ticket_id: string;
  agent_run_id: string | null;
  approval_request_id: string | null;
  source: string;
  status: string;
  subject: string | null;
  body: string;
  sent_message_id: string | null;
  created_at: string;
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
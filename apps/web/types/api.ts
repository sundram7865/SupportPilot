export type Organization = {
  id: string;
  name?: string;
  slug?: string;
  role?: string;
};

export type AuthMeResponse = {
  user: {
    id: string;
    email: string;
    name?: string | null;
  };
  organizations?: Organization[];
  memberships?: Array<{
    organization_id?: string;
    role?: string;
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
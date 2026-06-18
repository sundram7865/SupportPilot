export function formatDate(value?: string | null) {
  if (!value) return "—";

  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}

export function statusTone(status?: string) {
  if (!status) return "default";

  if (["RESOLVED", "CLOSED", "SUCCESS", "APPROVED", "SENT"].includes(status)) {
    return "green";
  }

  if (["FAILED", "REJECTED", "URGENT", "HIGH"].includes(status)) {
    return "red";
  }

  if (
    [
      "PENDING",
      "PENDING_APPROVAL",
      "BLOCKED_APPROVAL_REQUIRED",
      "WAITING_FOR_CUSTOMER",
      "WAITING_FOR_INTERNAL_REVIEW",
      "MEDIUM",
    ].includes(status)
  ) {
    return "yellow";
  }

  if (["OPEN", "IN_PROGRESS", "STARTED", "DRAFT"].includes(status)) {
    return "blue";
  }

  return "default";
}
import { useState } from "react";

import { Section } from "@/components/ui/Section";

export function CustomerMessagePanel({
  onAdd,
}: {
  onAdd: (body: string) => Promise<void>;
}) {
  const [body, setBody] = useState("Can you give me an update?");

  return (
    <Section title="Customer Message">
      <div className="muted" style={{ marginBottom: 10 }}>
        Add a new customer-side message to simulate follow-up conversation.
      </div>

      <div className="form-row">
        <label className="label">Message</label>
        <textarea
          className="textarea"
          value={body}
          onChange={(event) => setBody(event.target.value)}
          placeholder="Type customer message..."
        />
      </div>

      <button className="btn" onClick={() => onAdd(body)} disabled={!body.trim()}>
        Add Customer Message
      </button>
    </Section>
  );
}
import { useState } from "react";

import { Section } from "@/components/ui/Section";

export function CustomerMessagePanel({
  onAdd,
}: {
  onAdd: (body: string) => Promise<void>;
}) {
  const [body, setBody] = useState("Can you give me an update?");

  return (
    <Section title="Add Customer Message">
      <div className="form-row">
        <textarea
          className="textarea"
          value={body}
          onChange={(event) => setBody(event.target.value)}
        />
      </div>

      <button className="btn" onClick={() => onAdd(body)}>
        Add Message
      </button>
    </Section>
  );
}
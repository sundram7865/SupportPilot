import type { ExternalApiLog } from "@/types/api";

function valueOrDash(value: unknown) {
  if (value === null || value === undefined || value === "") {
    return "-";
  }

  return String(value);
}

export function ExternalApiLogsTable({ logs }: { logs: ExternalApiLog[] }) {
  if (logs.length === 0) {
    return <p className="muted">No external API logs yet.</p>;
  }

  return (
    <div className="table-wrap">
      <table className="table">
        <thead>
          <tr>
            <th>Created</th>
            <th>Provider</th>
            <th>Method</th>
            <th>Endpoint</th>
            <th>Status</th>
            <th>Status Code</th>
            <th>Duration</th>
            <th>Error</th>
          </tr>
        </thead>

        <tbody>
          {logs.map((log) => (
            <tr key={log.id}>
              <td>
                {log.created_at
                  ? new Date(log.created_at).toLocaleString()
                  : "-"}
              </td>
              <td>{valueOrDash(log.provider)}</td>
              <td>{valueOrDash(log.method)}</td>
              <td>{valueOrDash(log.endpoint || log.url)}</td>
              <td>{valueOrDash(log.status)}</td>
              <td>{valueOrDash(log.status_code)}</td>
              <td>
                {log.duration_ms !== null && log.duration_ms !== undefined
                  ? `${log.duration_ms} ms`
                  : "-"}
              </td>
              <td>{valueOrDash(log.error_message)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
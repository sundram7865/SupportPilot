"use client";

import { useState } from "react";

import { apiFetch } from "@/lib/api";
import type { KnowledgeSearchResult } from "@/types/api";

export function KnowledgeSearchPanel({
  getToken,
}: {
  getToken?: () => Promise<string | null>;
}) {
  const [query, setQuery] = useState("");
  const [limit, setLimit] = useState(5);
  const [results, setResults] = useState<KnowledgeSearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function search(event: React.FormEvent) {
    event.preventDefault();

    if (!getToken) {
      setMessage("Authentication is not ready.");
      return;
    }

    setSearching(true);
    setMessage(null);

    try {
      const response = await apiFetch<{
        query: string;
        results: KnowledgeSearchResult[];
      }>("/knowledge/search", {
        method: "POST",
        getToken,
        body: JSON.stringify({
          query,
          limit,
        }),
      });

      const searchResults = response.results || [];

      setResults(searchResults);
      setMessage(
        searchResults.length === 0 ? "No matching knowledge found." : null
      );
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Search failed.");
    } finally {
      setSearching(false);
    }
  }

  return (
    <div className="stack">
      <form className="grid-two" onSubmit={search}>
        <div>
          <label className="label">Search Query</label>
          <input
            className="input"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="refund after payment deducted"
            required
          />
        </div>

        <div>
          <label className="label">Limit</label>
          <input
            className="input"
            type="number"
            min={1}
            max={20}
            value={limit}
            onChange={(event) => setLimit(Number(event.target.value))}
          />
        </div>

        <div>
          <button className="button" disabled={searching}>
            {searching ? "Searching..." : "Search"}
          </button>
        </div>
      </form>

      {message ? <p className="muted">{message}</p> : null}

      {results.length > 0 ? (
        <div className="stack">
          {results.map((result, index) => (
            <div
              key={`${result.chunk_id || result.document_id || index}`}
              className="card"
            >
              <div className="muted" style={{ marginBottom: 8 }}>
                {result.document_title || "Knowledge Result"} •{" "}
                {result.document_type} • chunk {result.chunk_index} • score{" "}
                {result.score.toFixed(4)}
              </div>

              <p style={{ whiteSpace: "pre-wrap" }}>{result.content}</p>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}
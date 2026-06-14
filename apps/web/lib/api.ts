const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function getApiHealth() {
  const response = await fetch(`${API_URL}/health`, {
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error("Failed to fetch API health");
  }

  return response.json();
}

export async function testUrbanKartConnection() {
  const response = await fetch(`${API_URL}/integrations/urbankart/test-connection`, {
    method: "POST",
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error("Failed to test UrbanKart connection");
  }

  return response.json();
}
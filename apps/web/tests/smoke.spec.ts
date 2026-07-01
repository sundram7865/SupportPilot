import { expect, test } from "@playwright/test";

test.describe("SupportPilot frontend smoke tests", () => {
  test("e2e health route is available", async ({ request }) => {
    const response = await request.get("/e2e-health");

    expect(response.status()).toBe(200);

    const data = await response.json();

    expect(data.ok).toBe(true);
    expect(data.service).toBe("supportpilot-web");
  });

  test("e2e health route returns json", async ({ request }) => {
    const response = await request.get("/e2e-health");

    expect(response.status()).toBe(200);
    expect(response.headers()["content-type"]).toContain("application/json");
  });
});
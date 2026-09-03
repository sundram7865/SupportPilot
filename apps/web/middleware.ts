import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";

const isPublicRoute = createRouteMatcher([
  "/sign-in(.*)",
  "/sign-up(.*)",

  // Public customer support page
  "/support(.*)",

  // Embeddable iframe page
  "/embed(.*)",

  // Static widget script
  "/widget(.*)",
   "/e2e-health",
]);

export default clerkMiddleware(async (auth, req) => {
  if (process.env.E2E_TEST === "true") {
    return;
  }

  if (!isPublicRoute(req)) {
    await auth.protect();
  }
});

export const config = {
  matcher: [
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    "/(api|trpc)(.*)",
  ],
};
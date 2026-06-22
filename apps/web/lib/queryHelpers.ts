export function isQueryEnabled(
  isSignedIn: boolean | undefined,
  getToken?: () => Promise<string | null>
) {
  return Boolean(isSignedIn && getToken);
}
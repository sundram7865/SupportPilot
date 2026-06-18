export function LoadingState({ message = "Loading..." }: { message?: string }) {
  return <div className="muted">{message}</div>;
}
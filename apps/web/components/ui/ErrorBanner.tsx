export function ErrorBanner({
  message,
  onDismiss,
}: {
  message: string | null;
  onDismiss?: () => void;
}) {
  if (!message) return null;

  return (
    <div className="error" role="alert">
      <span>{message}</span>
      {onDismiss ? (
        <button type="button" className="button secondary" onClick={onDismiss}>
          Dismiss
        </button>
      ) : null}
    </div>
  );
}
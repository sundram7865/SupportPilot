type BadgeTone = "default" | "green" | "red" | "yellow" | "blue";

function toneClass(tone: BadgeTone) {
  if (tone === "green") return "badge badge-green";
  if (tone === "red") return "badge badge-red";
  if (tone === "yellow") return "badge badge-yellow";
  if (tone === "blue") return "badge badge-blue";
  return "badge";
}

export function Badge({
  children,
  tone = "default",
}: {
  children: React.ReactNode;
  tone?: BadgeTone;
}) {
  return <span className={toneClass(tone)}>{children}</span>;
}
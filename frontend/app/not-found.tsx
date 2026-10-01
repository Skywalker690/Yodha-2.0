import Link from "next/link";
export default function NotFound() {
  return (
    <main className="center-screen">
      <h1>Page not found</h1>
      <p>This workspace page is unavailable.</p>
      <Link className="button button-primary" href="/dashboard">
        Back to dashboard
      </Link>
    </main>
  );
}

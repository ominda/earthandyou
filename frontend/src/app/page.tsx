async function getApiHealth() {
  try {
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/health/`, {
      cache: "no-store",
    });
    return res.ok ? await res.json() : null;
  } catch {
    return null;
  }
}

export default async function HomePage() {
  const health = await getApiHealth();

  return (
    <main style={{ fontFamily: "sans-serif", padding: "2rem" }}>
      <h1>Earth&amp;You</h1>
      <p>Premium Sri Lankan Gemstones</p>
      <hr />
      <h2>API Status</h2>
      {health ? (
        <p style={{ color: "green" }}>✓ API connected — {health.service}</p>
      ) : (
        <p style={{ color: "red" }}>✗ API not reachable</p>
      )}
    </main>
  );
}

"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { login } from "@/lib/api";

export default function LoginPage() {
  const { login: setAuth } = useAuth();
  const router = useRouter();
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const tokens = await login(form);
      setAuth(tokens.access);
      router.push("/account");
    } catch {
      setError("Invalid email or password.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="section-container py-16 max-w-md">
      <p className="text-xs tracking-[0.3em] uppercase text-gold-500 mb-2">Welcome Back</p>
      <h1 className="font-serif text-heading text-stone-900 mb-8">Log In</h1>

      <form onSubmit={handleSubmit} className="flex flex-col gap-5">
        {error && <p className="text-red-600 text-sm">{error}</p>}

        <div className="flex flex-col gap-1">
          <label className="text-xs tracking-widest uppercase text-stone-500">Email</label>
          <input
            type="email"
            required
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
            className="border border-stone-300 px-4 py-3 text-sm text-stone-900 focus:outline-none focus:border-gold-400"
          />
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-xs tracking-widest uppercase text-stone-500">Password</label>
          <input
            type="password"
            required
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            className="border border-stone-300 px-4 py-3 text-sm text-stone-900 focus:outline-none focus:border-gold-400"
          />
        </div>

        <button type="submit" disabled={loading} className="btn-primary disabled:opacity-50">
          {loading ? "Logging in..." : "Log In"}
        </button>
      </form>

      <p className="mt-6 text-sm text-stone-500 text-center">
        Don&apos;t have an account?{" "}
        <Link href="/account/register" className="text-gold-500 hover:underline">Register</Link>
      </p>
    </div>
  );
}

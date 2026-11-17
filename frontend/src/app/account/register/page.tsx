"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { register, registerFull, login } from "@/lib/api";

export default function RegisterPage() {
  const { login: setAuth } = useAuth();
  const router = useRouter();
  const [form, setForm] = useState({ email: "", first_name: "", last_name: "", password: "", password_confirm: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (form.password !== form.password_confirm) {
      setError("Passwords do not match.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      await registerFull({ email: form.email, first_name: form.first_name, last_name: form.last_name, password: form.password, password_confirm: form.password_confirm });
      const tokens = await login({ email: form.email, password: form.password });
      setAuth(tokens.access);
      router.push("/account");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Registration failed. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  const field = (key: keyof typeof form, label: string, type = "text") => (
    <div className="flex flex-col gap-1">
      <label className="text-xs tracking-widest uppercase text-stone-500">{label}</label>
      <input
        type={type}
        required
        value={form[key]}
        onChange={(e) => setForm({ ...form, [key]: e.target.value })}
        className="border border-stone-300 px-4 py-3 text-sm text-stone-900 focus:outline-none focus:border-gold-400"
      />
    </div>
  );

  return (
    <div className="section-container py-16 max-w-md">
      <p className="text-xs tracking-[0.3em] uppercase text-gold-500 mb-2">Create Account</p>
      <h1 className="font-serif text-heading text-stone-900 mb-8">Register</h1>

      <form onSubmit={handleSubmit} className="flex flex-col gap-5">
        {error && <p className="text-red-600 text-sm">{error}</p>}
        {field("first_name", "First Name")}
        {field("last_name", "Last Name")}
        {field("email", "Email", "email")}
        {field("password", "Password", "password")}
        {field("password_confirm", "Confirm Password", "password")}

        <button type="submit" disabled={loading} className="btn-primary disabled:opacity-50">
          {loading ? "Creating account..." : "Create Account"}
        </button>
      </form>

      <p className="mt-6 text-sm text-stone-500 text-center">
        Already have an account?{" "}
        <Link href="/account/login" className="text-gold-500 hover:underline">Log In</Link>
      </p>
    </div>
  );
}

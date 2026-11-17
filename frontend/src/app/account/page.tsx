"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { getMe, updateMe, getAddresses, deleteAddress } from "@/lib/api";
import type { CustomerAddress } from "@/types/commerce";

type Me = { id: number; email: string; first_name: string; last_name: string; full_name: string; is_email_verified: boolean };

export default function AccountPage() {
  const { token, isLoggedIn, logout } = useAuth();
  const router = useRouter();

  const [me, setMe] = useState<Me | null>(null);
  const [addresses, setAddresses] = useState<CustomerAddress[]>([]);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({ first_name: "", last_name: "" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!isLoggedIn) { router.push("/account/login"); return; }
    if (!token) return;
    Promise.all([getMe(token), getAddresses(token)]).then(([meData, addrs]) => {
      setMe(meData);
      setForm({ first_name: meData.first_name, last_name: meData.last_name });
      setAddresses(addrs);
    });
  }, [token, isLoggedIn, router]);

  async function handleSaveProfile(e: React.FormEvent) {
    e.preventDefault();
    if (!token) return;
    setSaving(true);
    setError("");
    try {
      const updated = await updateMe(token, form) as Me;
      setMe(updated);
      setEditing(false);
    } catch {
      setError("Failed to save changes.");
    } finally {
      setSaving(false);
    }
  }

  async function handleDeleteAddress(id: number) {
    if (!token) return;
    await deleteAddress(token, id);
    setAddresses((prev) => prev.filter((a) => a.id !== id));
  }

  if (!me) return <div className="section-container py-24 text-center text-stone-400">Loading...</div>;

  return (
    <div className="section-container py-12 max-w-2xl">
      <div className="flex items-center justify-between mb-8">
        <div>
          <p className="text-xs tracking-[0.3em] uppercase text-gold-500 mb-1">My Account</p>
          <h1 className="font-serif text-heading text-stone-900">{me.full_name || me.email}</h1>
        </div>
        <button onClick={logout} className="text-xs tracking-widest uppercase text-stone-400 hover:text-stone-700 transition-colors">
          Log Out
        </button>
      </div>

      {/* Profile */}
      <section className="border border-stone-200 p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <p className="text-xs tracking-widest uppercase text-stone-500">Profile</p>
          {!editing && (
            <button onClick={() => setEditing(true)} className="text-xs text-gold-500 hover:underline">Edit</button>
          )}
        </div>

        {editing ? (
          <form onSubmit={handleSaveProfile} className="flex flex-col gap-4">
            {error && <p className="text-red-600 text-sm">{error}</p>}
            <div className="grid grid-cols-2 gap-4">
              {(["first_name", "last_name"] as const).map((key) => (
                <div key={key} className="flex flex-col gap-1">
                  <label className="text-xs tracking-widest uppercase text-stone-500">
                    {key === "first_name" ? "First Name" : "Last Name"}
                  </label>
                  <input
                    value={form[key]}
                    onChange={(e) => setForm({ ...form, [key]: e.target.value })}
                    className="border border-stone-300 px-3 py-2 text-sm focus:outline-none focus:border-gold-400"
                  />
                </div>
              ))}
            </div>
            <div className="flex gap-3">
              <button type="submit" disabled={saving} className="btn-primary text-sm disabled:opacity-50">
                {saving ? "Saving..." : "Save"}
              </button>
              <button type="button" onClick={() => setEditing(false)} className="text-sm text-stone-400 hover:text-stone-600">
                Cancel
              </button>
            </div>
          </form>
        ) : (
          <dl className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
            {[
              ["Email", me.email],
              ["Name", me.full_name || "—"],
              ["Email Verified", me.is_email_verified ? "Yes" : "No"],
            ].map(([label, value]) => (
              <div key={label}>
                <dt className="text-stone-400 text-xs">{label}</dt>
                <dd className="text-stone-800 font-medium">{value}</dd>
              </div>
            ))}
          </dl>
        )}
      </section>

      {/* Addresses */}
      <section className="border border-stone-200 p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <p className="text-xs tracking-widest uppercase text-stone-500">Saved Addresses</p>
          <Link href="/account/addresses/new" className="text-xs text-gold-500 hover:underline">+ Add New</Link>
        </div>

        {addresses.length === 0 ? (
          <p className="text-sm text-stone-400">No saved addresses yet.</p>
        ) : (
          <div className="flex flex-col gap-4">
            {addresses.map((addr) => (
              <div key={addr.id} className="flex items-start justify-between gap-4 text-sm text-stone-700">
                <div className="leading-relaxed">
                  {addr.is_default && (
                    <span className="text-xs tracking-widest uppercase text-gold-500 mr-2">Default</span>
                  )}
                  <span className="font-medium">{addr.recipient_name}</span>
                  <p>{addr.line1}{addr.line2 ? `, ${addr.line2}` : ""}</p>
                  <p>{addr.city}{addr.state ? `, ${addr.state}` : ""} {addr.postal_code}</p>
                  <p>{addr.country}</p>
                </div>
                <div className="flex gap-3 shrink-0">
                  <Link href={`/account/addresses/${addr.id}`} className="text-xs text-stone-400 hover:text-stone-700">Edit</Link>
                  <button onClick={() => handleDeleteAddress(addr.id)} className="text-xs text-stone-400 hover:text-red-500">Delete</button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Quick links */}
      <div className="flex gap-4">
        <Link href="/account/orders" className="btn-outline text-sm">View Orders</Link>
        <Link href="/catalog" className="text-sm text-stone-500 hover:text-stone-800 transition-colors self-center">Browse Collection →</Link>
      </div>
    </div>
  );
}

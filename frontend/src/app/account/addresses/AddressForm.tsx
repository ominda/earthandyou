"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { createAddress, updateAddress } from "@/lib/api";
import type { CustomerAddress } from "@/types/commerce";

type FormState = {
  recipient_name: string;
  phone: string;
  line1: string;
  line2: string;
  city: string;
  state: string;
  postal_code: string;
  country: string;
  label: string;
  is_default: boolean;
  address_type: "shipping" | "billing";
};

const EMPTY: FormState = {
  recipient_name: "", phone: "", line1: "", line2: "",
  city: "", state: "", postal_code: "", country: "",
  label: "", is_default: false, address_type: "shipping",
};

export default function AddressForm({ existing }: { existing?: CustomerAddress }) {
  const { token } = useAuth();
  const router = useRouter();
  const [form, setForm] = useState<FormState>(existing ? {
    recipient_name: existing.recipient_name,
    phone: existing.phone ?? "",
    line1: existing.line1,
    line2: existing.line2 ?? "",
    city: existing.city,
    state: existing.state ?? "",
    postal_code: existing.postal_code ?? "",
    country: existing.country,
    label: existing.label ?? "",
    is_default: existing.is_default,
    address_type: existing.address_type as "shipping" | "billing",
  } : EMPTY);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const set = (key: keyof FormState) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setForm({ ...form, [key]: e.target.type === "checkbox" ? (e.target as HTMLInputElement).checked : e.target.value });

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!token) return;
    setSaving(true);
    setError("");
    try {
      if (existing) {
        await updateAddress(token, existing.id, form);
      } else {
        await createAddress(token, form);
      }
      router.push("/account");
    } catch {
      setError("Failed to save address.");
    } finally {
      setSaving(false);
    }
  }

  const textField = (key: keyof FormState, label: string, required = false) => (
    <div className="flex flex-col gap-1">
      <label className="text-xs tracking-widest uppercase text-stone-500">{label}</label>
      <input
        type="text"
        required={required}
        value={form[key] as string}
        onChange={set(key)}
        className="border border-stone-300 px-4 py-3 text-sm text-stone-900 focus:outline-none focus:border-gold-400"
      />
    </div>
  );

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-5">
      {error && <p className="text-red-600 text-sm">{error}</p>}

      {textField("label", "Label (e.g. Home, Office)")}
      {textField("recipient_name", "Recipient Name", true)}
      {textField("phone", "Phone")}
      {textField("line1", "Address Line 1", true)}
      {textField("line2", "Address Line 2")}

      <div className="grid grid-cols-2 gap-4">
        {textField("city", "City", true)}
        {textField("state", "State / Province")}
      </div>

      <div className="grid grid-cols-2 gap-4">
        {textField("postal_code", "Postal Code")}
        <div className="flex flex-col gap-1">
          <label className="text-xs tracking-widest uppercase text-stone-500">Country (ISO)</label>
          <input
            type="text"
            required
            maxLength={2}
            placeholder="e.g. US"
            value={form.country}
            onChange={set("country")}
            className="border border-stone-300 px-4 py-3 text-sm text-stone-900 focus:outline-none focus:border-gold-400 uppercase"
          />
        </div>
      </div>

      <div className="flex flex-col gap-1">
        <label className="text-xs tracking-widest uppercase text-stone-500">Address Type</label>
        <select
          value={form.address_type}
          onChange={set("address_type")}
          className="border border-stone-300 px-4 py-3 text-sm text-stone-900 focus:outline-none focus:border-gold-400"
        >
          <option value="shipping">Shipping</option>
          <option value="billing">Billing</option>
        </select>
      </div>

      <label className="flex items-center gap-3 text-sm text-stone-700 cursor-pointer">
        <input
          type="checkbox"
          checked={form.is_default}
          onChange={set("is_default")}
          className="accent-gold-500"
        />
        Set as default address
      </label>

      <div className="flex gap-3 pt-2">
        <button type="submit" disabled={saving} className="btn-primary disabled:opacity-50">
          {saving ? "Saving..." : existing ? "Save Changes" : "Add Address"}
        </button>
        <button type="button" onClick={() => router.push("/account")} className="text-sm text-stone-400 hover:text-stone-600">
          Cancel
        </button>
      </div>
    </form>
  );
}

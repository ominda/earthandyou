"use client";

import { useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { getAddresses, createCheckout, placeOrder } from "@/lib/api";
import type { CustomerAddress, CheckoutSession } from "@/types/commerce";

export default function CheckoutPage() {
  const { token, isLoggedIn } = useAuth();
  const searchParams = useSearchParams();
  const router = useRouter();

  const reservationId = Number(searchParams.get("reservation_id"));

  const [addresses, setAddresses] = useState<CustomerAddress[]>([]);
  const [shippingId, setShippingId] = useState<number | null>(null);
  const [session, setSession] = useState<CheckoutSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [placing, setPlacing] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token || !reservationId) { setLoading(false); return; }
    getAddresses(token).then((addrs) => {
      setAddresses(addrs);
      const def = addrs.find((a) => a.is_default) ?? addrs[0];
      if (def) setShippingId(def.id);
    }).finally(() => setLoading(false));
  }, [token, reservationId]);

  async function handleCreateSession() {
    if (!token || !shippingId) return;
    setError("");
    try {
      const s = await createCheckout(token, reservationId, shippingId);
      setSession(s);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to create checkout session.");
    }
  }

  async function handlePlaceOrder() {
    if (!token || !session) return;
    setPlacing(true);
    setError("");
    try {
      const order = await placeOrder(token, session.id);
      router.push(`/account/orders/${order.id}?placed=1`);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to place order.");
      setPlacing(false);
    }
  }

  if (!isLoggedIn) {
    return (
      <div className="section-container py-24 text-center">
        <p className="text-stone-500 mb-4">Please log in to continue.</p>
        <a href="/account/login" className="btn-primary">Log In</a>
      </div>
    );
  }

  if (!reservationId) {
    return (
      <div className="section-container py-24 text-center">
        <p className="text-stone-500">No reservation found. Please start from your cart.</p>
      </div>
    );
  }

  if (loading) {
    return <div className="section-container py-24 text-center text-stone-400">Loading...</div>;
  }

  return (
    <div className="section-container py-12 max-w-2xl">
      <h1 className="font-serif text-heading text-stone-900 mb-8">Checkout</h1>

      {error && <p className="text-red-600 text-sm mb-4">{error}</p>}

      {!session ? (
        /* Step 1 — address selection */
        <div className="flex flex-col gap-6">
          <div>
            <p className="text-xs tracking-widest uppercase text-stone-500 mb-4">Shipping Address</p>
            {addresses.length === 0 ? (
              <p className="text-stone-500 text-sm">
                No saved addresses.{" "}
                <a href="/account/addresses/new" className="text-gold-500 hover:underline">Add one</a>.
              </p>
            ) : (
              <div className="flex flex-col gap-3">
                {addresses.map((addr) => (
                  <label
                    key={addr.id}
                    className={`flex items-start gap-3 border p-4 cursor-pointer transition-colors ${
                      shippingId === addr.id ? "border-gold-400 bg-gold-50" : "border-stone-200"
                    }`}
                  >
                    <input
                      type="radio"
                      name="shipping"
                      value={addr.id}
                      checked={shippingId === addr.id}
                      onChange={() => setShippingId(addr.id)}
                      className="mt-1 accent-gold-500"
                    />
                    <div className="text-sm text-stone-700 leading-relaxed">
                      <p className="font-medium">{addr.recipient_name}</p>
                      <p>{addr.line1}{addr.line2 ? `, ${addr.line2}` : ""}</p>
                      <p>{addr.city}{addr.state ? `, ${addr.state}` : ""} {addr.postal_code}</p>
                      <p>{addr.country}</p>
                    </div>
                  </label>
                ))}
              </div>
            )}
          </div>

          <button
            onClick={handleCreateSession}
            disabled={!shippingId}
            className="btn-primary disabled:opacity-50"
          >
            Continue to Order Summary
          </button>
        </div>
      ) : (
        /* Step 2 — order summary & confirm */
        <div className="flex flex-col gap-6">
          <div className="border border-stone-200 p-6 flex flex-col gap-3">
            <p className="text-xs tracking-widest uppercase text-stone-500 mb-2">Order Summary</p>
            <p className="font-serif text-lg text-stone-900">{session.headline}</p>
            <p className="text-xs text-stone-400">{session.gemstone_id}</p>
            <div className="border-t border-stone-100 pt-4 flex flex-col gap-2 text-sm">
              <div className="flex justify-between text-stone-600">
                <span>Subtotal</span><span>USD {session.subtotal_usd}</span>
              </div>
              <div className="flex justify-between text-stone-600">
                <span>Shipping</span><span>USD {session.shipping_usd}</span>
              </div>
              <div className="flex justify-between font-medium text-stone-900 text-base pt-2 border-t border-stone-100">
                <span>Total</span><span>USD {session.total_usd}</span>
              </div>
            </div>
          </div>

          <div className="border border-stone-200 p-4 text-sm text-stone-600">
            <p className="text-xs tracking-widest uppercase text-stone-500 mb-2">Shipping To</p>
            <p>{session.shipping_address.recipient_name}</p>
            <p>{session.shipping_address.line1}</p>
            <p>{session.shipping_address.city}, {session.shipping_address.country}</p>
          </div>

          <button
            onClick={handlePlaceOrder}
            disabled={placing}
            className="btn-primary disabled:opacity-50"
          >
            {placing ? "Placing Order..." : "Place Order"}
          </button>

          <button
            onClick={() => setSession(null)}
            className="text-sm text-stone-400 hover:text-stone-600 transition-colors text-center"
          >
            ← Change Address
          </button>
        </div>
      )}
    </div>
  );
}

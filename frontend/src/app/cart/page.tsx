"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import { getCart, removeFromCart, createReservation } from "@/lib/api";
import type { Cart } from "@/types/commerce";

export default function CartPage() {
  const { token, isLoggedIn } = useAuth();
  const [cart, setCart] = useState<Cart | null>(null);
  const [loading, setLoading] = useState(true);
  const [reserving, setReserving] = useState<number | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token) { setLoading(false); return; }
    getCart(token).then(setCart).finally(() => setLoading(false));
  }, [token]);

  async function handleRemove(productId: number) {
    if (!token) return;
    await removeFromCart(token, productId);
    const updated = await getCart(token);
    setCart(updated);
  }

  async function handleReserve(productId: number) {
    if (!token) return;
    setReserving(productId);
    setError("");
    try {
      const reservation = await createReservation(token, productId);
      window.location.href = `/checkout?reservation_id=${reservation.id}`;
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to reserve. Please try again.");
      setReserving(null);
    }
  }

  if (!isLoggedIn) {
    return (
      <div className="section-container py-24 text-center">
        <p className="font-serif text-2xl text-stone-900 mb-4">Your Cart</p>
        <p className="text-stone-500 mb-6">Please log in to view your cart.</p>
        <Link href="/account/login" className="btn-primary">Log In</Link>
      </div>
    );
  }

  if (loading) {
    return <div className="section-container py-24 text-center text-stone-400">Loading...</div>;
  }

  if (!cart || cart.items.length === 0) {
    return (
      <div className="section-container py-24 text-center">
        <p className="font-serif text-2xl text-stone-900 mb-4">Your Cart is Empty</p>
        <p className="text-stone-500 mb-6">Explore our collection to find your perfect stone.</p>
        <Link href="/catalog" className="btn-primary">View Collection</Link>
      </div>
    );
  }

  return (
    <div className="section-container py-12 max-w-3xl">
      <h1 className="font-serif text-heading text-stone-900 mb-8">Your Cart</h1>

      {error && <p className="text-red-600 text-sm mb-4">{error}</p>}

      <div className="flex flex-col divide-y divide-stone-200">
        {cart.items.map((item) => (
          <div key={item.id} className="py-6 flex items-start justify-between gap-4">
            <div className="flex flex-col gap-1">
              <p className="text-xs tracking-widest uppercase text-gold-500">{item.gemstone_id}</p>
              <Link
                href={`/catalog/${item.slug}`}
                className="font-serif text-lg text-stone-900 hover:text-gold-600 transition-colors"
              >
                {item.headline}
              </Link>
              <p className="text-stone-700 font-medium">USD {item.price_usd}</p>
            </div>
            <div className="flex flex-col gap-2 items-end shrink-0">
              <button
                onClick={() => handleReserve(item.product_id)}
                disabled={reserving === item.product_id}
                className="btn-primary text-xs py-2 px-4 disabled:opacity-50"
              >
                {reserving === item.product_id ? "Reserving..." : "Reserve & Checkout"}
              </button>
              <button
                onClick={() => handleRemove(item.product_id)}
                className="text-xs text-stone-400 hover:text-red-500 transition-colors"
              >
                Remove
              </button>
            </div>
          </div>
        ))}
      </div>

      <div className="border-t border-stone-200 pt-6 flex justify-between items-center">
        <p className="text-stone-500 text-sm">{cart.item_count} item{cart.item_count !== 1 ? "s" : ""}</p>
        <p className="font-serif text-xl text-stone-900">USD {cart.total_usd}</p>
      </div>
    </div>
  );
}

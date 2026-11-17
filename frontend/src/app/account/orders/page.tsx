"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { getOrders } from "@/lib/api";
import type { Order } from "@/types/commerce";

const STATUS_LABEL: Record<string, string> = {
  pending:    "Pending",
  confirmed:  "Confirmed",
  paid:       "Paid",
  dispatched: "Dispatched",
  delivered:  "Delivered",
  cancelled:  "Cancelled",
  refunded:   "Refunded",
};

const STATUS_COLOR: Record<string, string> = {
  pending:    "text-stone-400",
  confirmed:  "text-blue-500",
  paid:       "text-emerald-600",
  dispatched: "text-gold-500",
  delivered:  "text-emerald-700",
  cancelled:  "text-red-400",
  refunded:   "text-stone-400",
};

export default function OrdersPage() {
  const { token, isLoggedIn } = useAuth();
  const router = useRouter();
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isLoggedIn) { router.push("/account/login"); return; }
    if (!token) return;
    getOrders(token).then(setOrders).finally(() => setLoading(false));
  }, [token, isLoggedIn, router]);

  if (loading) return <div className="section-container py-24 text-center text-stone-400">Loading...</div>;

  return (
    <div className="section-container py-12 max-w-3xl">
      <div className="flex items-center justify-between mb-8">
        <div>
          <p className="text-xs tracking-[0.3em] uppercase text-gold-500 mb-1">My Account</p>
          <h1 className="font-serif text-heading text-stone-900">Orders</h1>
        </div>
        <Link href="/account" className="text-xs tracking-widest uppercase text-stone-400 hover:text-stone-700 transition-colors">
          ← Account
        </Link>
      </div>

      {orders.length === 0 ? (
        <div className="py-16 text-center">
          <p className="font-serif text-2xl text-stone-900 mb-3">No orders yet</p>
          <p className="text-stone-500 text-sm mb-6">When you place an order it will appear here.</p>
          <Link href="/catalog" className="btn-primary">Browse Collection</Link>
        </div>
      ) : (
        <div className="flex flex-col divide-y divide-stone-200">
          {orders.map((order) => (
            <Link
              key={order.id}
              href={`/account/orders/${order.id}`}
              className="py-6 flex items-start justify-between gap-4 hover:bg-stone-50 transition-colors -mx-4 px-4"
            >
              <div className="flex flex-col gap-1">
                <p className="text-xs tracking-widest uppercase text-gold-500">{order.order_ref}</p>
                <p className="font-serif text-stone-900">{order.product_headline}</p>
                <p className="text-xs text-stone-400">{order.gemstone_id}</p>
              </div>
              <div className="flex flex-col items-end gap-1 shrink-0">
                <p className="font-medium text-stone-900">USD {order.total_usd}</p>
                <p className={`text-xs tracking-widest uppercase ${STATUS_COLOR[order.status] ?? "text-stone-400"}`}>
                  {STATUS_LABEL[order.status] ?? order.status}
                </p>
                <p className="text-xs text-stone-400">{new Date(order.created_at).toLocaleDateString()}</p>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

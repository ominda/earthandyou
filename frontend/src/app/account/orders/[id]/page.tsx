"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { getOrder } from "@/lib/api";
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

export default function OrderDetailPage() {
  const { token } = useAuth();
  const { id } = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const justPlaced = searchParams.get("placed") === "1";

  const [order, setOrder] = useState<Order | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) return;
    getOrder(token, Number(id)).then(setOrder).finally(() => setLoading(false));
  }, [token, id]);

  if (loading) return <div className="section-container py-24 text-center text-stone-400">Loading...</div>;
  if (!order) return <div className="section-container py-24 text-center text-stone-400">Order not found.</div>;

  const addr = order.shipping_address as { recipient_name?: string; line1?: string; city?: string; country?: string } | null;

  return (
    <div className="section-container py-12 max-w-2xl">
      {justPlaced && (
        <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 text-sm px-5 py-4 mb-8">
          <p className="font-medium">Order placed successfully.</p>
          <p className="text-xs mt-1">You will receive a confirmation email shortly.</p>
        </div>
      )}

      <div className="flex items-center justify-between mb-8">
        <div>
          <p className="text-xs tracking-[0.3em] uppercase text-gold-500 mb-1">{order.order_ref}</p>
          <h1 className="font-serif text-heading text-stone-900">{order.product_headline}</h1>
          <p className="text-xs text-stone-400 mt-1">{order.gemstone_id}</p>
        </div>
        <Link href="/account/orders" className="text-xs tracking-widest uppercase text-stone-400 hover:text-stone-700 transition-colors">
          ← Orders
        </Link>
      </div>

      {/* Summary */}
      <section className="border border-stone-200 p-6 mb-6">
        <p className="text-xs tracking-widest uppercase text-stone-500 mb-4">Order Summary</p>
        <dl className="flex flex-col gap-2 text-sm">
          <div className="flex justify-between text-stone-600">
            <dt>Subtotal</dt><dd>USD {order.subtotal_usd}</dd>
          </div>
          <div className="flex justify-between text-stone-600">
            <dt>Shipping</dt><dd>USD {order.shipping_usd}</dd>
          </div>
          <div className="flex justify-between font-medium text-stone-900 text-base pt-2 border-t border-stone-100">
            <dt>Total</dt><dd>USD {order.total_usd}</dd>
          </div>
        </dl>
      </section>

      {/* Status */}
      <section className="border border-stone-200 p-6 mb-6">
        <p className="text-xs tracking-widest uppercase text-stone-500 mb-4">Status</p>
        <p className="text-sm font-medium text-stone-900 mb-4">
          {STATUS_LABEL[order.status] ?? order.status}
        </p>

        {order.status_logs && order.status_logs.length > 0 && (
          <ol className="flex flex-col gap-3">
            {order.status_logs.map((log, i) => (
              <li key={i} className="flex items-start gap-3 text-sm">
                <span className="mt-1 w-2 h-2 rounded-full bg-gold-400 shrink-0" />
                <div>
                  <p className="text-stone-700 font-medium">{STATUS_LABEL[log.to_status] ?? log.to_status}</p>
                  <p className="text-xs text-stone-400">{new Date(log.created_at).toLocaleString()}</p>
                  {log.notes && <p className="text-xs text-stone-500 mt-0.5">{log.notes}</p>}
                </div>
              </li>
            ))}
          </ol>
        )}
      </section>

      {/* Shipment */}
      {order.shipment && (
        <section className="border border-stone-200 p-6 mb-6">
          <p className="text-xs tracking-widest uppercase text-stone-500 mb-4">Shipment</p>
          <dl className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
            {[
              ["Carrier", order.shipment.carrier],
              ["Tracking No.", order.shipment.tracking_number],
              ["Status", order.shipment.status],
              ["Est. Delivery", order.shipment.estimated_delivery_date],
            ].map(([label, value]) => value ? (
              <div key={label}>
                <dt className="text-stone-400 text-xs">{label}</dt>
                <dd className="text-stone-800 font-medium">{value}</dd>
              </div>
            ) : null)}
          </dl>
          {order.shipment.tracking_url && (
            <a
              href={order.shipment.tracking_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-block mt-4 text-xs tracking-widest uppercase text-gold-500 hover:text-gold-600 transition-colors"
            >
              Track Shipment →
            </a>
          )}
        </section>
      )}

      {/* Shipping address */}
      {addr && (
        <section className="border border-stone-200 p-6 mb-6">
          <p className="text-xs tracking-widest uppercase text-stone-500 mb-3">Shipping To</p>
          <div className="text-sm text-stone-700 leading-relaxed">
            <p className="font-medium">{addr.recipient_name}</p>
            <p>{addr.line1}</p>
            <p>{addr.city}, {addr.country}</p>
          </div>
        </section>
      )}

      {/* Public tracking link */}
      <Link
        href={`/tracking/${order.order_ref}`}
        className="text-xs tracking-widest uppercase text-gold-500 hover:text-gold-600 transition-colors"
      >
        Public Tracking Page →
      </Link>
    </div>
  );
}

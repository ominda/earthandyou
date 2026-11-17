import { getOrderTracking } from "@/lib/api";
import Link from "next/link";

type TrackingData = {
  order_ref: string;
  gemstone_id: string;
  product_headline: string;
  status: string;
  created_at: string;
  shipment: {
    carrier: string;
    tracking_number: string;
    tracking_url: string;
    status: string;
    estimated_delivery_date: string | null;
    actual_delivery_date: string | null;
  } | null;
  timeline: { status: string; timestamp: string }[];
};

const STATUS_LABEL: Record<string, string> = {
  pending: "Pending", confirmed: "Confirmed", paid: "Paid",
  dispatched: "Dispatched", delivered: "Delivered",
  cancelled: "Cancelled", refunded: "Refunded",
};

type Props = { params: { order_ref: string } };

export default async function TrackingPage({ params }: Props) {
  let data: TrackingData | null = null;
  try {
    data = await getOrderTracking(params.order_ref) as TrackingData;
  } catch {
    // not found
  }

  if (!data) {
    return (
      <div className="section-container py-24 text-center">
        <p className="font-serif text-2xl text-stone-900 mb-3">Order Not Found</p>
        <p className="text-stone-500 text-sm mb-6">Check your order reference and try again.</p>
        <Link href="/" className="btn-outline">Go Home</Link>
      </div>
    );
  }

  return (
    <div className="section-container py-12 max-w-xl">
      <p className="text-xs tracking-[0.3em] uppercase text-gold-500 mb-2">Order Tracking</p>
      <h1 className="font-serif text-heading text-stone-900 mb-1">{data.product_headline}</h1>
      <p className="text-xs text-stone-400 mb-8">{data.order_ref} · {data.gemstone_id}</p>

      <div className="border border-stone-200 p-6 mb-6">
        <p className="text-xs tracking-widest uppercase text-stone-500 mb-2">Current Status</p>
        <p className="font-serif text-xl text-stone-900">{STATUS_LABEL[data.status] ?? data.status}</p>
      </div>

      {data.shipment && (
        <div className="border border-stone-200 p-6 mb-6">
          <p className="text-xs tracking-widest uppercase text-stone-500 mb-4">Shipment</p>
          <dl className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
            {([
              ["Carrier", data.shipment.carrier],
              ["Tracking No.", data.shipment.tracking_number],
              ["Status", data.shipment.status],
              ["Est. Delivery", data.shipment.estimated_delivery_date],
              ["Delivered", data.shipment.actual_delivery_date],
            ] as [string, string | null][]).map(([label, value]) => value ? (
              <div key={label}>
                <dt className="text-stone-400 text-xs">{label}</dt>
                <dd className="text-stone-800 font-medium">{value}</dd>
              </div>
            ) : null)}
          </dl>
          {data.shipment.tracking_url && (
            <a href={data.shipment.tracking_url} target="_blank" rel="noopener noreferrer"
              className="inline-block mt-4 text-xs tracking-widest uppercase text-gold-500 hover:text-gold-600 transition-colors">
              Track with Carrier →
            </a>
          )}
        </div>
      )}

      {data.timeline.length > 0 && (
        <div className="border border-stone-200 p-6">
          <p className="text-xs tracking-widest uppercase text-stone-500 mb-4">Timeline</p>
          <ol className="flex flex-col gap-4">
            {data.timeline.map((entry, i) => (
              <li key={i} className="flex items-start gap-3 text-sm">
                <span className="mt-1 w-2 h-2 rounded-full bg-gold-400 shrink-0" />
                <div>
                  <p className="text-stone-700 font-medium">{STATUS_LABEL[entry.status] ?? entry.status}</p>
                  <p className="text-xs text-stone-400">{new Date(entry.timestamp).toLocaleString()}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      )}
    </div>
  );
}

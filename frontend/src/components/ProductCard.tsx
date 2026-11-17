import Link from "next/link";
import type { ProductListItem } from "@/types/catalog";

const TIER_LABELS: Record<string, string> = {
  standard:     "Standard",
  premium:      "Premium",
  luxury:       "Luxury",
  ultra_luxury: "Ultra Luxury",
};

export default function ProductCard({ product }: { product: ProductListItem }) {
  return (
    <Link
      href={`/catalog/${product.slug}`}
      className="group flex flex-col bg-white border border-stone-200 hover:border-gold-400 transition-colors duration-200"
    >
      {/* Image */}
      <div className="aspect-square bg-stone-100 overflow-hidden">
        {product.primary_media ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={
              product.primary_media.s3_key.startsWith("http")
                ? product.primary_media.s3_key
                : `${process.env.NEXT_PUBLIC_API_URL}/api/v1/catalog/media/sign/?key=${encodeURIComponent(product.primary_media.s3_key)}`
            }
            alt={product.primary_media.alt_text || product.headline}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <span className="font-serif text-4xl text-stone-300">✦</span>
          </div>
        )}
      </div>

      {/* Info */}
      <div className="p-4 flex flex-col gap-1 flex-1">
        <p className="text-xs tracking-widest uppercase text-gold-500">
          {product.species}{product.variety ? ` · ${product.variety}` : ""}
        </p>
        <h3 className="font-serif text-stone-900 leading-snug">{product.headline}</h3>
        <div className="mt-auto pt-3 flex items-center justify-between">
          <span className="text-stone-900 font-medium">USD {product.price_usd}</span>
          {!product.is_available && (
            <span className="text-xs tracking-widest uppercase text-stone-400">Sold</span>
          )}
        </div>
      </div>
    </Link>
  );
}

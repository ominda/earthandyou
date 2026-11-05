import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getProduct } from "@/lib/api";
import type { ProductDetail } from "@/types/catalog";
import MediaGallery from "./MediaGallery";

type Props = { params: { slug: string } };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  try {
    const product = await getProduct(params.slug);
    return {
      title: product.meta_title || product.headline,
      description: product.meta_description || product.description,
    };
  } catch {
    return { title: "Product Not Found" };
  }
}

export default async function ProductDetailPage({ params }: Props) {
  let product: ProductDetail;
  try {
    product = await getProduct(params.slug);
  } catch {
    notFound();
  }

  const primaryCert = product.certification_reports.find((r) => r.is_primary) ?? product.certification_reports[0];

  return (
    <div className="section-container py-12">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-12">

        {/* Media gallery */}
        <MediaGallery media={product.media} headline={product.headline} />

        {/* Details */}
        <div className="flex flex-col gap-6">
          <div>
            <p className="text-xs tracking-[0.3em] uppercase text-gold-500 mb-1">
              {product.species}{product.variety ? ` · ${product.variety}` : ""}
            </p>
            <h1 className="font-serif text-heading text-stone-900">{product.headline}</h1>
            <p className="text-xs text-stone-400 mt-1">{product.gemstone_id}</p>
          </div>

          <p className="text-2xl font-medium text-stone-900">USD {product.price_usd}</p>

          {product.is_available ? (
            <a href={`/cart/add/${product.id}`} className="btn-primary text-center">
              Reserve This Stone
            </a>
          ) : (
            <p className="text-sm tracking-widest uppercase text-stone-400 border border-stone-200 px-6 py-3 text-center">
              Sold
            </p>
          )}

          {product.description && (
            <p className="text-stone-600 leading-relaxed text-sm">{product.description}</p>
          )}

          {/* Certification */}
          {primaryCert && (
            <div className="border-t border-stone-200 pt-6">
              <p className="text-xs tracking-widest uppercase text-stone-500 mb-4">Certification</p>
              <dl className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
                {[
                  ["Laboratory", primaryCert.laboratory_name],
                  ["Report No.", primaryCert.report_number],
                  ["Carat Weight", primaryCert.reported_carat_weight],
                  ["Origin", primaryCert.origin_country],
                  ["Treatment", primaryCert.treatment_status],
                  ["Natural", primaryCert.natural_status],
                ].map(([label, value]) => value ? (
                  <div key={label}>
                    <dt className="text-stone-400 text-xs">{label}</dt>
                    <dd className="text-stone-800 font-medium">{value}</dd>
                  </div>
                ) : null)}
              </dl>
              {primaryCert.verification_url && (
                <a
                  href={primaryCert.verification_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-block mt-4 text-xs tracking-widest uppercase text-gold-500 hover:text-gold-600 transition-colors"
                >
                  Verify Certificate →
                </a>
              )}
            </div>
          )}

          {/* Provenance */}
          {product.provenance && (
            <div className="border-t border-stone-200 pt-6">
              <p className="text-xs tracking-widest uppercase text-stone-500 mb-4">Provenance</p>
              <dl className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
                {[
                  ["Country", product.provenance.origin_country],
                  ["Region", product.provenance.source_region],
                  ["Mine", product.provenance.mine_locality],
                  ["Confidence", product.provenance.confidence],
                ].map(([label, value]) => value ? (
                  <div key={label}>
                    <dt className="text-stone-400 text-xs">{label}</dt>
                    <dd className="text-stone-800 font-medium">{value}</dd>
                  </div>
                ) : null)}
              </dl>
              {product.provenance.customer_description && (
                <p className="mt-3 text-sm text-stone-600 leading-relaxed">
                  {product.provenance.customer_description}
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

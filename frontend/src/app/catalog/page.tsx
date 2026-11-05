import type { Metadata } from "next";
import { getProducts } from "@/lib/api";
import ProductCard from "@/components/ProductCard";
import CatalogFilters from "./CatalogFilters";

export const metadata: Metadata = { title: "Collection" };

const SPECIES_OPTIONS = [
  { label: "All", value: "" },
  { label: "Sapphire", value: "SAP" },
  { label: "Ruby", value: "RUB" },
  { label: "Spinel", value: "SPI" },
  { label: "Alexandrite", value: "ALE" },
  { label: "Cat's Eye", value: "CAT" },
  { label: "Tourmaline", value: "TOU" },
];

const TIER_OPTIONS = [
  { label: "All Tiers", value: "" },
  { label: "Standard", value: "standard" },
  { label: "Premium", value: "premium" },
  { label: "Luxury", value: "luxury" },
  { label: "Ultra Luxury", value: "ultra_luxury" },
];

type Props = {
  searchParams: { species?: string; value_tier?: string; search?: string; page?: string };
};

export default async function CatalogPage({ searchParams }: Props) {
  const { species, value_tier, search, page } = searchParams;

  let data;
  try {
    data = await getProducts({
      species,
      value_tier,
      search,
      listing_status: "active",
      page: page ? Number(page) : undefined,
    });
  } catch {
    data = { count: 0, results: [], next: null, previous: null };
  }

  return (
    <div className="section-container py-12">
      {/* Page header */}
      <div className="mb-10">
        <p className="text-xs tracking-[0.3em] uppercase text-gold-500 mb-2">Earth&amp;You</p>
        <h1 className="font-serif text-heading text-stone-900">The Collection</h1>
        <p className="text-stone-500 mt-2">{data.count} stone{data.count !== 1 ? "s" : ""}</p>
      </div>

      {/* Filters */}
      <CatalogFilters speciesOptions={SPECIES_OPTIONS} tierOptions={TIER_OPTIONS} />

      {/* Grid */}
      {data.results.length === 0 ? (
        <div className="py-24 text-center text-stone-400">
          <p className="font-serif text-2xl mb-2">No stones found</p>
          <p className="text-sm">Try adjusting your filters.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 mt-8">
          {data.results.map((product) => (
            <ProductCard key={product.id} product={product} />
          ))}
        </div>
      )}

      {/* Pagination */}
      {(data.next || data.previous) && (
        <div className="mt-12 flex justify-center gap-4">
          {data.previous && (
            <a href={`?page=${Number(page || 1) - 1}`} className="btn-outline">
              Previous
            </a>
          )}
          {data.next && (
            <a href={`?page=${Number(page || 1) + 1}`} className="btn-primary">
              Next
            </a>
          )}
        </div>
      )}
    </div>
  );
}

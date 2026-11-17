import Link from "next/link";
import { getProducts } from "@/lib/api";
import ProductCard from "@/components/ProductCard";

export default async function HomePage() {
  let featured;
  try {
    const data = await getProducts({ listing_status: "active", page: 1 });
    featured = data.results.slice(0, 4);
  } catch {
    featured = [];
  }

  return (
    <>
      {/* Hero */}
      <section className="bg-stone-900 text-white">
        <div className="section-container py-32 flex flex-col items-center text-center gap-6">
          <p className="text-xs tracking-[0.3em] uppercase text-gold-400">
            Sri Lankan Gemstones
          </p>
          <h1 className="font-serif text-display text-white max-w-2xl">
            Rare Gems, Ethically Sourced
          </h1>
          <p className="text-stone-400 max-w-md leading-relaxed">
            Each stone is a unique creation of the earth — certified, traceable,
            and chosen for exceptional quality.
          </p>
          <Link href="/catalog" className="btn-primary mt-4">
            Explore the Collection
          </Link>
        </div>
      </section>

      {/* Values strip */}
      <section className="border-b border-stone-200">
        <div className="section-container py-10 grid grid-cols-1 md:grid-cols-3 gap-8 text-center">
          {[
            { title: "Certified", body: "Every gemstone comes with a laboratory certification report." },
            { title: "Traceable", body: "Full provenance records from mine to your hands." },
            { title: "Unique", body: "No two stones are alike — each is a one-of-a-kind piece." },
          ].map((item) => (
            <div key={item.title} className="flex flex-col items-center gap-2">
              <h3 className="font-serif text-lg text-stone-900">{item.title}</h3>
              <p className="text-sm text-stone-500 leading-relaxed">{item.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Featured products */}
      {featured.length > 0 && (
        <section className="section-container py-16">
          <div className="flex items-end justify-between mb-8">
            <div>
              <p className="text-xs tracking-[0.3em] uppercase text-gold-500 mb-1">Featured</p>
              <h2 className="font-serif text-heading text-stone-900">From the Collection</h2>
            </div>
            <Link href="/catalog" className="text-sm tracking-widest uppercase text-stone-500 hover:text-gold-500 transition-colors">
              View All →
            </Link>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {featured.map((product) => (
              <ProductCard key={product.id} product={product} />
            ))}
          </div>
        </section>
      )}
    </>
  );
}

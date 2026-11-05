import Link from "next/link";

export default function HomePage() {
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
    </>
  );
}

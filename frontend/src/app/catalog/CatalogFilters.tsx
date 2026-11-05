"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useCallback } from "react";

type Option = { label: string; value: string };

type Props = {
  speciesOptions: Option[];
  tierOptions: Option[];
};

export default function CatalogFilters({ speciesOptions, tierOptions }: Props) {
  const router = useRouter();
  const searchParams = useSearchParams();

  const update = useCallback(
    (key: string, value: string) => {
      const params = new URLSearchParams(searchParams.toString());
      if (value) {
        params.set(key, value);
      } else {
        params.delete(key);
      }
      params.delete("page");
      router.push(`/catalog?${params.toString()}`);
    },
    [router, searchParams]
  );

  return (
    <div className="flex flex-wrap gap-4 items-center">
      {/* Search */}
      <input
        type="text"
        placeholder="Search..."
        defaultValue={searchParams.get("search") ?? ""}
        onKeyDown={(e) => {
          if (e.key === "Enter") update("search", (e.target as HTMLInputElement).value);
        }}
        className="border border-stone-300 px-4 py-2 text-sm text-stone-700 focus:outline-none focus:border-gold-400 w-48"
      />

      {/* Species */}
      <select
        value={searchParams.get("species") ?? ""}
        onChange={(e) => update("species", e.target.value)}
        className="border border-stone-300 px-4 py-2 text-sm text-stone-700 focus:outline-none focus:border-gold-400 bg-white"
      >
        {speciesOptions.map((o) => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>

      {/* Tier */}
      <select
        value={searchParams.get("value_tier") ?? ""}
        onChange={(e) => update("value_tier", e.target.value)}
        className="border border-stone-300 px-4 py-2 text-sm text-stone-700 focus:outline-none focus:border-gold-400 bg-white"
      >
        {tierOptions.map((o) => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>
    </div>
  );
}

"use client";

import { useState } from "react";
import type { ProductMedia } from "@/types/catalog";

const resolveUrl = (s3_key: string) =>
  s3_key.startsWith("http")
    ? s3_key
    : `${process.env.NEXT_PUBLIC_API_URL}/api/v1/catalog/media/sign/?key=${encodeURIComponent(s3_key)}`;

type Props = { media: ProductMedia[]; headline: string };

export default function MediaGallery({ media, headline }: Props) {
  const photos = media.filter((m) => m.media_type === "photo");
  const [active, setActive] = useState(0);

  if (photos.length === 0) {
    return (
      <div className="aspect-square bg-stone-100 flex items-center justify-center">
        <span className="font-serif text-6xl text-stone-300">✦</span>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {/* Main image */}
      <div className="aspect-square bg-stone-100 overflow-hidden">
        <img
          src={resolveUrl(photos[active].s3_key)}
          alt={photos[active].alt_text || headline}
          className="w-full h-full object-cover"
        />
      </div>

      {/* Thumbnails */}
      {photos.length > 1 && (
        <div className="flex gap-2 overflow-x-auto">
          {photos.map((photo, i) => (
            <button
              key={photo.id}
              onClick={() => setActive(i)}
              className={`flex-shrink-0 w-16 h-16 overflow-hidden border-2 transition-colors ${
                i === active ? "border-gold-500" : "border-transparent"
              }`}
            >
              <img
                src={resolveUrl(photo.s3_key)}
                alt={photo.alt_text || `${headline} ${i + 1}`}
                className="w-full h-full object-cover"
              />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

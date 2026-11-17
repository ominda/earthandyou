"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { getAddresses } from "@/lib/api";
import type { CustomerAddress } from "@/types/commerce";
import AddressForm from "../AddressForm";

export default function EditAddressPage() {
  const { token } = useAuth();
  const { id } = useParams<{ id: string }>();
  const [address, setAddress] = useState<CustomerAddress | null>(null);

  useEffect(() => {
    if (!token) return;
    getAddresses(token).then((addrs) => {
      const found = addrs.find((a) => a.id === Number(id));
      if (found) setAddress(found);
    });
  }, [token, id]);

  if (!address) return <div className="section-container py-24 text-center text-stone-400">Loading...</div>;

  return (
    <div className="section-container py-12 max-w-lg">
      <p className="text-xs tracking-[0.3em] uppercase text-gold-500 mb-2">My Account</p>
      <h1 className="font-serif text-heading text-stone-900 mb-8">Edit Address</h1>
      <AddressForm existing={address} />
    </div>
  );
}

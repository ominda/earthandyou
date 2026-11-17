import AddressForm from "../AddressForm";

export default function NewAddressPage() {
  return (
    <div className="section-container py-12 max-w-lg">
      <p className="text-xs tracking-[0.3em] uppercase text-gold-500 mb-2">My Account</p>
      <h1 className="font-serif text-heading text-stone-900 mb-8">Add Address</h1>
      <AddressForm />
    </div>
  );
}

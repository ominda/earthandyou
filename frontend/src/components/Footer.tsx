import Link from "next/link";

export default function Footer() {
  return (
    <footer className="bg-stone-900 text-stone-400 mt-auto">
      <div className="section-container py-12">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">

          {/* Brand */}
          <div>
            <p className="font-serif text-xl text-white mb-2">
              Earth<span className="text-gold-500">&</span>You
            </p>
            <p className="text-sm leading-relaxed">
              Premium Sri Lankan gemstones, ethically sourced and certified.
            </p>
          </div>

          {/* Navigation */}
          <div>
            <p className="text-xs tracking-widest uppercase text-stone-500 mb-4">Explore</p>
            <ul className="space-y-2 text-sm">
              <li><Link href="/catalog" className="hover:text-gold-400 transition-colors">Collection</Link></li>
              <li><Link href="/about" className="hover:text-gold-400 transition-colors">About</Link></li>
            </ul>
          </div>

          {/* Account */}
          <div>
            <p className="text-xs tracking-widest uppercase text-stone-500 mb-4">Account</p>
            <ul className="space-y-2 text-sm">
              <li><Link href="/account" className="hover:text-gold-400 transition-colors">My Account</Link></li>
              <li><Link href="/account/orders" className="hover:text-gold-400 transition-colors">My Orders</Link></li>
            </ul>
          </div>
        </div>

        <div className="border-t border-stone-800 mt-10 pt-6 text-xs text-stone-600 flex flex-col md:flex-row justify-between gap-2">
          <p>© {new Date().getFullYear()} Earth&amp;You. All rights reserved.</p>
          <p>Sri Lanka</p>
        </div>
      </div>
    </footer>
  );
}

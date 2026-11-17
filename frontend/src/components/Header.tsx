"use client";

import Link from "next/link";
import { useState } from "react";
import { useAuth } from "@/context/AuthContext";

const NAV_LINKS = [
  { label: "Collection", href: "/catalog" },
  { label: "About", href: "/about" },
];

export default function Header() {
  const [menuOpen, setMenuOpen] = useState(false);
  const { isLoggedIn, logout } = useAuth();

  return (
    <header className="bg-white border-b border-stone-200 sticky top-0 z-50">
      <div className="section-container">
        <div className="flex items-center justify-between h-16">

          {/* Logo */}
          <Link href="/" className="font-serif text-2xl text-stone-900 tracking-wide">
            Earth<span className="text-gold-500">&</span>You
          </Link>

          {/* Desktop nav */}
          <nav className="hidden md:flex items-center gap-8">
            {NAV_LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="text-sm tracking-widest uppercase text-stone-600 hover:text-gold-500 transition-colors"
              >
                {link.label}
              </Link>
            ))}
          </nav>

          {/* Actions */}
          <div className="flex items-center gap-4">
            {isLoggedIn ? (
              <>
                <Link href="/account" className="text-sm tracking-widest uppercase text-stone-600 hover:text-gold-500 transition-colors hidden md:block">Account</Link>
                <button onClick={logout} className="text-sm tracking-widest uppercase text-stone-600 hover:text-gold-500 transition-colors hidden md:block">Log Out</button>
              </>
            ) : (
              <Link href="/account/login" className="text-sm tracking-widest uppercase text-stone-600 hover:text-gold-500 transition-colors hidden md:block">Log In</Link>
            )}
            <Link href="/cart" className="text-sm tracking-widest uppercase text-stone-600 hover:text-gold-500 transition-colors">Cart</Link>

            {/* Mobile menu toggle */}
            <button
              className="md:hidden text-stone-600"
              onClick={() => setMenuOpen((o) => !o)}
              aria-label="Toggle menu"
            >
              <span className="block w-5 h-px bg-current mb-1" />
              <span className="block w-5 h-px bg-current mb-1" />
              <span className="block w-5 h-px bg-current" />
            </button>
          </div>
        </div>

        {/* Mobile nav */}
        {menuOpen && (
          <nav className="md:hidden border-t border-stone-100 py-4 flex flex-col gap-4">
            {NAV_LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="text-sm tracking-widest uppercase text-stone-600 hover:text-gold-500 transition-colors"
                onClick={() => setMenuOpen(false)}
              >
                {link.label}
              </Link>
            ))}
            <Link
              href="/account"
              className="text-sm tracking-widest uppercase text-stone-600 hover:text-gold-500 transition-colors"
              onClick={() => setMenuOpen(false)}
            >
              Account
            </Link>
          </nav>
        )}
      </div>
    </header>
  );
}

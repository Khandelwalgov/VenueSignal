import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "VenueSignal | Unity Stadium Operations",
  description: "Deterministic venue-state and accessibility inspection for the synthetic Unity Stadium prototype.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <a href="#main-content" className="skip-link">Skip to main content</a>
        {children}
      </body>
    </html>
  );
}

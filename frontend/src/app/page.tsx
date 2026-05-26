'use client';

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useChatStore } from "@/shared/store";

export default function Home() {
  const router = useRouter();
  const accessToken = useChatStore((state) => state.accessToken);

  useEffect(() => {
    // Small timeout for smooth experience
    const timer = setTimeout(() => {
      if (accessToken) {
        router.push("/dashboard");
      } else {
        router.push("/auth/login");
      }
    }, 400);

    return () => clearTimeout(timer);
  }, [accessToken, router]);

  return (
    <div className="flex h-screen w-full items-center justify-center bg-[#0f111a]">
      <div className="flex flex-col items-center gap-4 text-center">
        {/* Visual Premium Spinner */}
        <div className="relative h-12 w-12">
          <div className="absolute inset-0 rounded-full border-4 border-indigo-500/20"></div>
          <div className="absolute inset-0 rounded-full border-4 border-t-indigo-500 animate-spin"></div>
        </div>
        <p className="text-sm font-medium text-gray-400 tracking-wide">Initializing secure chat workspace...</p>
      </div>
    </div>
  );
}

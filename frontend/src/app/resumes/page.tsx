"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function ResumesRedirectPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/dashboard/resumes");
  }, [router]);

  return null;
}


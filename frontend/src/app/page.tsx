import Link from "next/link";
import { ArrowRight, CheckCircle2, Compass, FileText, Lock } from "lucide-react";

export default function Home() {
  return (
    <main className="flex-1 flex flex-col items-center justify-center px-6 py-20 text-center">
      <div className="inline-flex items-center gap-2 px-3 py-1 mb-8 text-xs font-semibold tracking-wide uppercase rounded-full bg-secondary text-secondary-foreground border border-border">
        <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
        Authentication Active
      </div>

      <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight max-w-4xl">
        AI-Powered Career Discovery & Application Management
      </h1>

      <p className="mt-6 text-lg text-muted-foreground max-w-2xl">
        Discover relevant opportunities, tailor applications, evaluate career trajectory, and
        streamline your entire job search workflow in one unified platform.
      </p>

      <div className="mt-8 flex flex-wrap items-center justify-center gap-4">
        <Link
          href="/register"
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-md bg-primary text-primary-foreground font-medium text-sm hover:opacity-90 transition-opacity"
        >
          Get Started <ArrowRight className="w-4 h-4" />
        </Link>
        <Link
          href="/login"
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-md border border-border bg-background hover:bg-secondary font-medium text-sm transition-colors"
        >
          Sign In
        </Link>
        <Link
          href="/dashboard"
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-md border border-border bg-secondary/50 hover:bg-secondary font-medium text-sm transition-colors"
        >
          <Lock className="w-4 h-4 text-muted-foreground" /> Protected Area
        </Link>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-4xl mt-16 w-full text-left">
        <div className="p-6 rounded-lg border border-border bg-card">
          <div className="p-2 w-fit rounded-md bg-secondary mb-4">
            <Compass className="w-5 h-5 text-primary" />
          </div>
          <h2 className="text-lg font-semibold">Career Discovery</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Explore company insights, role expectations, and intelligent career trajectory matching.
          </p>
        </div>

        <div className="p-6 rounded-lg border border-border bg-card">
          <div className="p-2 w-fit rounded-md bg-secondary mb-4">
            <FileText className="w-5 h-5 text-primary" />
          </div>
          <h2 className="text-lg font-semibold">Resume Intelligence</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Analyze skill alignment, customize application content, and optimize opportunity fit.
          </p>
        </div>

        <div className="p-6 rounded-lg border border-border bg-card">
          <div className="p-2 w-fit rounded-md bg-secondary mb-4">
            <CheckCircle2 className="w-5 h-5 text-primary" />
          </div>
          <h2 className="text-lg font-semibold">Pipeline Tracker</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Manage submissions, interview timelines, recruiter notes, and stage progressions.
          </p>
        </div>
      </div>

      <div className="mt-12 text-xs text-muted-foreground">
        Nexora Platform &bull; Authentication &amp; User Management Active
      </div>
    </main>
  );
}

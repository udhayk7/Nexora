"use client";

import React, { useEffect, useState } from "react";
import {
  BookmarkCheck,
  Check,
  Download,
  FileCode,
  FileText,
  Loader2,
  RefreshCw,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

interface PdfPreviewPanelProps {
  sessionId: string;
  pdfBlobUrl: string | null;
  compilationEngine: string;
  isCompiling: boolean;
  onRecompile: () => Promise<void>;
  onDownloadPdf: () => Promise<void>;
  onDownloadLatex: () => Promise<void>;
  onOpenSaveModal: () => void;
  isSavedVersion: boolean;
}

export function PdfPreviewPanel({
  sessionId,
  pdfBlobUrl,
  compilationEngine,
  isCompiling,
  onRecompile,
  onDownloadPdf,
  onDownloadLatex,
  onOpenSaveModal,
  isSavedVersion,
}: PdfPreviewPanelProps) {
  const [downloadingPdf, setDownloadingPdf] = useState(false);
  const [downloadingLatex, setDownloadingLatex] = useState(false);

  const handleDownloadPdf = async () => {
    setDownloadingPdf(true);
    try {
      await onDownloadPdf();
    } finally {
      setDownloadingPdf(false);
    }
  };

  const handleDownloadLatex = async () => {
    setDownloadingLatex(true);
    try {
      await onDownloadLatex();
    } finally {
      setDownloadingLatex(false);
    }
  };

  return (
    <div className="h-full flex flex-col bg-slate-950 text-slate-200 overflow-hidden">
      {/* Panel Header */}
      <div className="p-2.5 px-4 bg-slate-900 border-b border-slate-800 flex items-center justify-between gap-2 shrink-0">
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4 text-emerald-400" />
          <span className="text-xs font-semibold text-white">Live PDF Preview</span>
          <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700/60 font-mono">
            A4 Standard
          </span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={onRecompile}
            disabled={isCompiling}
            className="inline-flex items-center gap-1 px-2.5 py-1 text-xs rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition disabled:opacity-50"
            title="Recompile PDF from active editor source"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isCompiling ? "animate-spin text-indigo-400" : ""}`} />
            {isCompiling ? "Compiling..." : "Recompile"}
          </button>
        </div>
      </div>

      {/* PDF Viewer Container */}
      <div className="flex-1 w-full bg-slate-950 relative overflow-hidden flex items-center justify-center">
        {isCompiling ? (
          <div className="flex flex-col items-center gap-2 text-slate-400 text-xs">
            <Loader2 className="w-6 h-6 animate-spin text-indigo-500" />
            <span>Compiling PDF document in secure sandbox...</span>
          </div>
        ) : pdfBlobUrl ? (
          <iframe
            src={`${pdfBlobUrl}#toolbar=0&navpanes=0`}
            className="w-full h-full border-0 bg-slate-900"
            title="Tailored Resume Document Preview"
          />
        ) : (
          <div className="text-center p-6 text-slate-500 text-xs">
            <p>PDF preview not yet compiled.</p>
            <button
              onClick={onRecompile}
              className="mt-2 px-3 py-1 bg-indigo-600 hover:bg-indigo-500 text-white rounded text-xs"
            >
              Compile Now
            </button>
          </div>
        )}
      </div>

      {/* Export & Save Action Bar */}
      <div className="p-3 bg-slate-900/90 border-t border-slate-800 flex flex-wrap items-center justify-between gap-2 shrink-0">
        <div className="flex items-center gap-2 text-xs">
          <button
            onClick={handleDownloadPdf}
            disabled={downloadingPdf || isCompiling}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-medium transition text-xs disabled:opacity-50"
          >
            {downloadingPdf ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Download className="w-3.5 h-3.5 text-emerald-400" />
            )}
            Download PDF
          </button>

          <button
            onClick={handleDownloadLatex}
            disabled={downloadingLatex || isCompiling}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition text-xs disabled:opacity-50"
          >
            {downloadingLatex ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <FileCode className="w-3.5 h-3.5 text-indigo-400" />
            )}
            Export .tex
          </button>
        </div>

        <div>
          <button
            onClick={onOpenSaveModal}
            className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-lg font-semibold bg-emerald-600 hover:bg-emerald-500 text-white shadow-md transition text-xs"
          >
            <BookmarkCheck className="w-4 h-4" />
            {isSavedVersion ? "Save As New Version" : "Save Tailored Version"}
          </button>
        </div>
      </div>
    </div>
  );
}


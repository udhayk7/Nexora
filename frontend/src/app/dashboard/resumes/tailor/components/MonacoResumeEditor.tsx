"use client";

import React, { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import {
  AlertTriangle,
  Check,
  Copy,
  FileCode,
  RotateCcw,
  Save,
  ShieldCheck,
} from "lucide-react";

// Dynamically import Monaco Editor to avoid SSR window is undefined
const Editor = dynamic(() => import("@monaco-editor/react"), {
  ssr: false,
  loading: () => (
    <div className="h-full flex items-center justify-center bg-slate-950 text-slate-500 text-sm">
      Loading Monaco LaTeX Editor...
    </div>
  ),
});

interface MonacoResumeEditorProps {
  initialContent: string;
  onSave: (content: string) => Promise<void>;
  isSaving: boolean;
}

export function MonacoResumeEditor({
  initialContent,
  onSave,
  isSaving,
}: MonacoResumeEditorProps) {
  const [content, setContent] = useState<string>(initialContent);
  const [copied, setCopied] = useState(false);
  const [securityWarning, setSecurityWarning] = useState<string | null>(null);

  useEffect(() => {
    setContent(initialContent);
  }, [initialContent]);

  const hasUnsavedChanges = content !== initialContent;

  const handleEditorChange = (value?: string) => {
    const val = value || "";
    setContent(val);

    // Instant security check for prohibited tokens
    const forbiddenPatterns = [
      "\\write18",
      "\\sys_exec",
      "\\input{",
      "\\include{",
      "\\openin",
      "\\openout",
      "\\newwrite",
    ];
    const match = forbiddenPatterns.find((p) => val.includes(p));
    if (match) {
      setSecurityWarning(
        `Sandbox Alert: Prohibited directive '${match}' detected. This command will be blocked during compilation.`
      );
    } else {
      setSecurityWarning(null);
    }
  };

  const handleSave = async () => {
    if (!hasUnsavedChanges || isSaving) return;
    await onSave(content);
  };

  const handleRevert = () => {
    setContent(initialContent);
    setSecurityWarning(null);
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="h-full flex flex-col bg-slate-950 text-slate-200 overflow-hidden">
      {/* Editor Header Toolbar */}
      <div className="p-2.5 px-4 bg-slate-900 border-b border-slate-800 flex items-center justify-between gap-2 shrink-0">
        <div className="flex items-center gap-2">
          <FileCode className="w-4 h-4 text-indigo-400" />
          <span className="text-xs font-semibold text-white">resume.tex</span>
          {hasUnsavedChanges ? (
            <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-amber-950/80 text-amber-300 border border-amber-800/40 animate-pulse">
              ● Unsaved Changes
            </span>
          ) : (
            <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-emerald-950/60 text-emerald-400 border border-emerald-800/30 flex items-center gap-1">
              <ShieldCheck className="w-3 h-3" />
              Synced
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleCopy}
            className="inline-flex items-center gap-1 px-2.5 py-1 text-xs rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition"
            title="Copy LaTeX source"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            {copied ? "Copied" : "Copy"}
          </button>

          {hasUnsavedChanges && (
            <button
              onClick={handleRevert}
              disabled={isSaving}
              className="inline-flex items-center gap-1 px-2.5 py-1 text-xs rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition"
              title="Discard unsaved edits"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              Revert
            </button>
          )}

          <button
            onClick={handleSave}
            disabled={!hasUnsavedChanges || isSaving || securityWarning !== null}
            className="inline-flex items-center gap-1 px-3 py-1 text-xs rounded-lg font-medium bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white transition shadow-sm"
          >
            <Save className="w-3.5 h-3.5" />
            {isSaving ? "Saving..." : "Save Edits"}
          </button>
        </div>
      </div>

      {/* Security Banner if user enters prohibited command */}
      {securityWarning && (
        <div className="bg-rose-950/80 border-b border-rose-800/80 px-4 py-2 text-xs text-rose-200 flex items-center gap-2 shrink-0">
          <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
          <span>{securityWarning}</span>
        </div>
      )}

      {/* Monaco LaTeX Code Editor */}
      <div className="flex-1 w-full relative">
        <Editor
          height="100%"
          language="latex"
          theme="vs-dark"
          value={content}
          onChange={handleEditorChange}
          options={{
            fontSize: 13,
            lineHeight: 20,
            lineNumbers: "on",
            minimap: { enabled: false },
            wordWrap: "on",
            automaticLayout: true,
            scrollBeyondLastLine: false,
            tabSize: 2,
            fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
            renderLineHighlight: "all",
          }}
        />
      </div>
    </div>
  );
}

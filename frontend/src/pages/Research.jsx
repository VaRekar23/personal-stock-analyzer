import React, { useRef, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Upload, FileText, Trash2, Search, BookOpen, AlertTriangle } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { Panel, PanelHeader, Spinner, ErrorState } from "@/components/common";

const DOC_TYPES = ["annual_report", "quarterly_result", "investor_presentation",
  "earnings_call", "announcement", "research_note", "other"];

export default function Research() {
  const qc = useQueryClient();
  const fileRef = useRef();
  const [symbol, setSymbol] = useState("");
  const [docType, setDocType] = useState("annual_report");
  const [query, setQuery] = useState("");
  const [qSymbol, setQSymbol] = useState("");
  const [answer, setAnswer] = useState(null);

  const docs = useQuery({ queryKey: ["kdocs"], queryFn: () => api.knowledgeDocuments(), retry: 1 });

  const upload = useMutation({
    mutationFn: (fd) => api.knowledgeUpload(fd),
    onSuccess: (r) => {
      toast.success(r.duplicate ? "Already indexed (duplicate content)" : `Indexed: ${r.title}`);
      qc.invalidateQueries({ queryKey: ["kdocs"] });
      if (fileRef.current) fileRef.current.value = "";
    },
    onError: (e) => toast.error(e?.response?.data?.detail || "Upload failed"),
  });

  const del = useMutation({
    mutationFn: (id) => api.knowledgeDelete(id),
    onSuccess: () => { toast.success("Document removed"); qc.invalidateQueries({ queryKey: ["kdocs"] }); },
  });

  const research = useMutation({
    mutationFn: (body) => api.research(body),
    onSuccess: (d) => setAnswer(d),
    onError: (e) => toast.error(e?.response?.data?.detail || "Research failed"),
  });

  const onUpload = () => {
    const f = fileRef.current?.files?.[0];
    if (!f) return toast.error("Choose a PDF or text file first");
    const fd = new FormData();
    fd.append("file", f);
    fd.append("title", f.name);
    if (symbol.trim()) fd.append("symbol", symbol.trim().toUpperCase());
    fd.append("doc_type", docType);
    upload.mutate(fd);
  };

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-display font-bold text-slate-100 flex items-center gap-2">
            <BookOpen size={22} /> Company Research
          </h1>
          <p className="text-sm text-slate-500">Upload documents · ask grounded questions · every claim cites a real source</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Library */}
        <Panel testid="research-library" className="lg:col-span-1">
          <PanelHeader title="Research Library" />
          <div className="p-4 space-y-3">
            <input ref={fileRef} type="file" accept=".pdf,.txt,.md,.csv" data-testid="doc-file-input"
              className="w-full text-xs text-slate-300 file:mr-3 file:py-1.5 file:px-3 file:rounded file:border-0 file:bg-cyan/15 file:text-cyan" />
            <div className="flex gap-2">
              <input value={symbol} onChange={(e) => setSymbol(e.target.value)} placeholder="Symbol (optional)"
                data-testid="doc-symbol-input"
                className="flex-1 bg-surface px-2 py-1.5 text-xs font-mono rounded border border-surface-2 focus:border-cyan focus:outline-none" />
              <select value={docType} onChange={(e) => setDocType(e.target.value)} data-testid="doc-type-select"
                className="bg-surface px-2 py-1.5 text-xs rounded border border-surface-2">
                {DOC_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            <button onClick={onUpload} disabled={upload.isPending} data-testid="doc-upload-btn"
              className="w-full flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-mono rounded bg-cyan/15 text-cyan border border-cyan/30 hover:bg-cyan/25 disabled:opacity-40">
              <Upload size={13} /> {upload.isPending ? "Indexing…" : "Upload & Index"}
            </button>
            <div className="text-[10px] text-slate-500">PDF (text-based) or .txt/.md · max 15 MB · scanned PDFs need OCR (unsupported)</div>

            <div className="pt-2 space-y-1.5 max-h-[420px] overflow-y-auto">
              {docs.isLoading ? <Spinner /> : docs.isError ? <ErrorState title="Library unavailable" error={docs.error} />
                : (docs.data?.documents || []).length === 0 ? <div className="text-xs text-slate-500 py-4 text-center">No documents yet.</div>
                : docs.data.documents.map((d) => (
                  <div key={d.id} data-testid="doc-row" className="flex items-start justify-between gap-2 p-2 rounded bg-surface border border-surface-2">
                    <div className="min-w-0">
                      <div className="text-xs text-slate-200 truncate flex items-center gap-1"><FileText size={11} /> {d.title}</div>
                      <div className="text-[10px] font-mono text-slate-500">
                        {d.symbol || "—"} · {d.doc_type} · {d.chunk_count} chunks · <span className={d.indexing_status === "indexed" ? "text-bull" : "text-watch"}>{d.indexing_status}</span>
                      </div>
                      {d.error_detail && <div className="text-[10px] text-bear">{d.error_detail}</div>}
                    </div>
                    <button onClick={() => del.mutate(d.id)} data-testid="doc-delete-btn" className="text-slate-500 hover:text-bear shrink-0"><Trash2 size={13} /></button>
                  </div>
                ))}
            </div>
          </div>
        </Panel>

        {/* Research Q&A */}
        <Panel testid="research-qa" className="lg:col-span-2">
          <PanelHeader title="Ask a Question" />
          <div className="p-4 space-y-3">
            <div className="flex gap-2">
              <input value={qSymbol} onChange={(e) => setQSymbol(e.target.value)} placeholder="Symbol"
                data-testid="research-symbol-input"
                className="w-28 bg-surface px-2 py-2 text-xs font-mono rounded border border-surface-2 focus:border-cyan focus:outline-none" />
              <input value={query} onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && query.trim() && research.mutate({ query, symbol: qSymbol || null })}
                placeholder="e.g. What are the key risks and what does management say about margins?"
                data-testid="research-query-input"
                className="flex-1 bg-surface px-3 py-2 text-sm rounded border border-surface-2 focus:border-cyan focus:outline-none" />
              <button onClick={() => query.trim() && research.mutate({ query, symbol: qSymbol || null })}
                disabled={research.isPending} data-testid="research-run-btn"
                className="flex items-center gap-1.5 px-4 py-2 text-xs font-mono rounded bg-ai/20 text-ai border border-ai/40 hover:bg-ai/30 disabled:opacity-40">
                <Search size={13} /> {research.isPending ? "Researching…" : "Research"}
              </button>
            </div>

            {research.isPending ? <Spinner label="Retrieving evidence + synthesizing…" /> : answer && (
              <div data-testid="research-answer" className="space-y-3 pt-2">
                <div className="text-[10px] font-mono text-slate-500 uppercase">
                  Answer · provider {answer.provider} {answer.grounded ? "· grounded" : ""}
                </div>
                <div className="text-sm text-slate-200 leading-relaxed bg-surface p-3 rounded border border-surface-2">{answer.answer}</div>

                {answer.key_findings?.length > 0 && (
                  <div><div className="text-xs font-semibold text-slate-300 mb-1">Key Findings</div>
                    <ul className="text-xs text-slate-400 space-y-1 list-disc pl-4">{answer.key_findings.map((k, i) => <li key={i}>{k}</li>)}</ul></div>
                )}
                {answer.citations_resolved?.length > 0 && (
                  <div><div className="text-xs font-semibold text-slate-300 mb-1">Sources</div>
                    <div className="space-y-1.5">{answer.citations_resolved.map((c, i) => (
                      <details key={i} data-testid="citation" className="text-xs bg-surface rounded border border-surface-2 p-2">
                        <summary className="cursor-pointer text-cyan">{c.document_title}{c.page ? ` · p.${c.page}` : ""}{c.publication_date ? ` · ${c.publication_date}` : ""}</summary>
                        <div className="text-slate-400 mt-1.5 whitespace-pre-wrap">{c.excerpt}</div>
                      </details>
                    ))}</div></div>
                )}
                {(answer.missing_information?.length > 0 || answer.caveats?.length > 0) && (
                  <div className="text-[11px] text-watch flex items-start gap-1.5 bg-watch/10 border border-watch/30 rounded p-2">
                    <AlertTriangle size={13} className="shrink-0 mt-0.5" />
                    <div>{[...(answer.missing_information || []), ...(answer.caveats || [])].join(" · ")}</div>
                  </div>
                )}
              </div>
            )}
          </div>
        </Panel>
      </div>
    </div>
  );
}

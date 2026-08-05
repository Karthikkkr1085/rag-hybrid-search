import { Database, FileDown, FileText, KeyRound, Layers3, MessageSquareText, ScanSearch, ShieldCheck, Sparkles, Workflow } from "lucide-react";
import { motion } from "framer-motion";
import type { LucideIcon } from "lucide-react";

type Feature = { icon: LucideIcon; title: string; copy: string; detail: string };

const features: Feature[] = [
  { icon: FileText, title: "PDF Parsing", copy: "Make every page searchable.", detail: "Extracts structured text and page metadata so citations always lead back to the original source." },
  { icon: Layers3, title: "Smart Chunking", copy: "Keep important context intact.", detail: "Overlapping, document-aware chunks keep policies, clauses, and tables meaningful during retrieval." },
  { icon: ScanSearch, title: "Hybrid Search", copy: "Semantic and keyword precision.", detail: "Combines intent-aware vector retrieval with exact keyword matching for stronger recall on real business questions." },
  { icon: Workflow, title: "RRF Ranking", copy: "The best signal, fused.", detail: "Reciprocal Rank Fusion blends independent result lists into one balanced and resilient relevance signal." },
  { icon: Sparkles, title: "CrossEncoder", copy: "Relevance refined at every turn.", detail: "A second-pass model compares the question and each passage together, promoting the evidence that actually answers it." },
  { icon: Database, title: "ChromaDB", copy: "Fast memory for your knowledge.", detail: "Persistent embeddings make semantic lookup low-latency while preserving source, page, and chunk information." },
  { icon: KeyRound, title: "Provider Controls", copy: "Choose the model that fits.", detail: "Switch between Groq, OpenAI, Gemini, OpenRouter, or local Ollama without interrupting the conversation." },
  { icon: ShieldCheck, title: "Session-Only Keys", copy: "Credentials stay private.", detail: "API keys are tested on demand and held only in the active browser session—never shown back or stored in source." },
  { icon: FileDown, title: "Reliable PDF Export", copy: "Readable reports, every time.", detail: "Answers, tables, code, and citations export as validated selectable PDF text instead of a fragile screen capture." },
  { icon: MessageSquareText, title: "Natural Chat", copy: "A composer built for thinking.", detail: "A growing multiline input, keyboard shortcuts, streaming feedback, and cited sources make long questions effortless." },
];

export function FeatureGrid() {
  return <section className="section-shell feature-section"><div className="section-intro"><p className="kicker">Engineered for clarity</p><h2>Intelligence in every layer.</h2><p>Purpose-built retrieval components work together to make answers feel effortless, traceable, and grounded in the documents your team trusts.</p></div><div className="feature-grid">{features.map(({ icon: Icon, title, copy, detail }, index) => <motion.article className="glass-card feature-card" key={title} initial={{ opacity: 0, y: 24 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, amount: 0.25 }} transition={{ delay: index * 0.06 }} whileHover={{ y: -7, rotateX: 3, rotateY: -3 }}><div className="feature-icon"><Icon size={21} /></div><h3>{title}</h3><p>{copy}</p><span className="feature-detail">{detail}</span><span className="card-shine" /></motion.article>)}</div></section>;
}

import { jsPDF } from "jspdf";

type Citation = { source: string; page: number; id?: number; chunk_id?: string | number; content?: string; confidence?: number };
type PdfStyle = { size: number; weight?: "normal" | "bold"; indent?: number; color?: [number, number, number] };

const PAGE = { width: 210, height: 297, margin: 16 };
const TEXT: [number, number, number] = [17, 24, 39];

export function downloadMarkdown(answer: string) {
  downloadBlob(new Blob([answer], { type: "text/markdown;charset=utf-8" }), "hybrid-rag-answer.md");
}

/**
 * Export semantic DOM text as vector PDF text.  The former `pdf.html()` path
 * captured an off-screen React clone through html2canvas, so CSS/layout timing
 * could yield a blank raster page and the output was not selectable text.
 */
export function downloadPdf(element: HTMLElement, citations: Citation[] = []) {
  const report = element.cloneNode(true) as HTMLElement;
  appendSources(report, citations);
  const visibleText = (report.innerText || report.textContent || "").replace(/\s+/g, " ").trim();
  if (!visibleText) throw new Error("PDF export stopped: the answer contains no visible text.");

  const pdf = new jsPDF({ orientation: "p", unit: "mm", format: "a4", compress: true });
  let y = PAGE.margin;
  const write = (text: string, style: PdfStyle = { size: 10.5 }) => {
    const clean = text.replace(/\s+/g, " ").trim();
    if (!clean) return;
    const x = PAGE.margin + (style.indent ?? 0);
    const maxWidth = PAGE.width - PAGE.margin - x;
    pdf.setFont("helvetica", style.weight ?? "normal");
    pdf.setFontSize(style.size);
    pdf.setTextColor(...(style.color ?? TEXT));
    const lines = pdf.splitTextToSize(clean, maxWidth) as string[];
    const lineHeight = style.size * 0.43;
    for (const line of lines) {
      if (y + lineHeight > PAGE.height - PAGE.margin) { pdf.addPage(); y = PAGE.margin; }
      pdf.text(line, x, y);
      y += lineHeight;
    }
    y += Math.max(1.4, lineHeight * .35);
  };
  const walk = (node: Node, listDepth = 0) => {
    if (node.nodeType === Node.TEXT_NODE) return;
    if (!(node instanceof HTMLElement)) return;
    const tag = node.tagName.toLowerCase();
    if (["script", "style", "button", "svg"].includes(tag)) return;
    if (tag === "h1") return write(node.innerText, { size: 18, weight: "bold", color: [18, 59, 104] });
    if (tag === "h2") return write(node.innerText, { size: 14, weight: "bold", color: [18, 59, 104] });
    if (tag === "h3") return write(node.innerText, { size: 12, weight: "bold" });
    if (tag === "p" || tag === "blockquote" || tag === "pre") return write(node.innerText, { size: tag === "pre" ? 9 : 10.5, indent: tag === "blockquote" ? 4 : 0 });
    if (tag === "li") return write(`• ${node.innerText}`, { size: 10.5, indent: 4 + listDepth * 4 });
    if (tag === "table") {
      node.querySelectorAll("tr").forEach(row => write(Array.from(row.querySelectorAll("th, td")).map(cell => cell.textContent?.trim() ?? "").filter(Boolean).join("  |  "), { size: 9.5, weight: row.querySelector("th") ? "bold" : "normal" }));
      return;
    }
    if (["ul", "ol"].includes(tag)) { Array.from(node.children).forEach(child => walk(child, listDepth + 1)); return; }
    Array.from(node.children).forEach(child => walk(child, listDepth));
  };

  walk(report);
  const pageCount = pdf.getNumberOfPages();
  const pdfBytes = pdf.output("arraybuffer");
  // A generated document must have pages and a non-trivial byte stream. Text is
  // emitted with `pdf.text`, making it selectable in standard PDF viewers.
  if (!pageCount || pdfBytes.byteLength < 800) throw new Error("PDF export stopped: the document could not be rendered.");
  pdf.save("hybrid-rag-answer.pdf");
}

function appendSources(report: HTMLElement, citations: Citation[]) {
  const grouped = new Map<string, number[]>();
  citations.forEach(({ source, page }) => grouped.set(source, [...new Set([...(grouped.get(source) ?? []), page])].sort((a, b) => a - b)));
  if (!grouped.size) return;
  const sources = document.createElement("section");
  sources.innerHTML = "<h2>Sources</h2>";
  grouped.forEach((pages, source) => { const item = document.createElement("p"); item.textContent = `${source}: ${pages.map(page => `Page ${page}`).join(", ")}`; sources.appendChild(item); });
  report.appendChild(sources);
}

function downloadBlob(blob: Blob, filename: string) { const url = URL.createObjectURL(blob); const anchor = document.createElement("a"); anchor.href = url; anchor.download = filename; anchor.click(); URL.revokeObjectURL(url); }

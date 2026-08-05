/**
 * Performs only safe Markdown normalization.  In particular, it never folds
 * paragraphs or invents report sections: the answer must keep the structure
 * supplied by the model and the retrieved documents.
 */
export function formatAnswerMarkdown(answer: string): string {
  return answer
    .replace(/\r\n?/g, "\n")
    .replace(/\[(\d+)\](?!\()/g, "[$1](citation:$1)")
    .replace(/^\s*[•▪‣]\s*/gm, "- ")
    .replace(/^(#{1,6})\s*([^\n]+?)\s*$/gm, (_, hashes: string, title: string) => `${hashes} ${title.trim()}`)
    // A common model pattern is a standalone section label without Markdown.
    .replace(/^(Overview|Key Information|Details|Important Notes|Summary|Conclusion|Requirements|Restrictions|Procedures|Benefits|Exceptions)\s*:\s*$/gim, "## $1")
    // Ensure a heading cannot visually merge with surrounding prose.
    .replace(/([^\n])\n(#{1,6}\s+)/g, "$1\n\n$2")
    .replace(/(#{1,6}\s+[^\n]+)\n([^\n#>\-*+\d])/g, "$1\n\n$2")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

import { ArrowDown, Bot, FileDown, FileUp, KeyRound, Scissors, Search, Sparkle } from "lucide-react";
import { motion } from "framer-motion";

const steps = [[FileUp, "PDF"], [Scissors, "Chunking"], [Sparkle, "Embeddings"], [Search, "Hybrid Search"], [Sparkle, "RRF"], [Search, "CrossEncoder"], [KeyRound, "Provider Settings"], [Bot, "Selected LLM"], [Sparkle, "Cited Answer"], [FileDown, "PDF Export"]];

export function Pipeline() {
  return <section className="section-shell pipeline-section"><div className="section-intro centered"><p className="kicker">One elegant flow</p><h2>From source to certainty.</h2></div><div className="pipeline">{steps.map(([Icon, label], index) => <div className="pipeline-item" key={label as string}><motion.div className="glass-card pipeline-node" whileHover={{ scale: 1.06 }}><Icon size={19} /><span>{label as string}</span></motion.div>{index < steps.length - 1 && <div className="pipeline-link"><ArrowDown size={15} /></div>}</div>)}</div></section>;
}

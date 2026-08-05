import { ArrowRight, Github, Play, Sparkles } from "lucide-react";
import { motion, useMotionValue, useSpring, useTransform } from "framer-motion";

export function Hero() {
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const rotateX = useSpring(useTransform(y, [-0.5, 0.5], [7, -7]), { stiffness: 120, damping: 18 });
  const rotateY = useSpring(useTransform(x, [-0.5, 0.5], [-7, 7]), { stiffness: 120, damping: 18 });

  return (
    <section className="hero section-shell" onPointerMove={(event) => {
      const rect = event.currentTarget.getBoundingClientRect();
      x.set((event.clientX - rect.left) / rect.width - 0.5);
      y.set((event.clientY - rect.top) / rect.height - 0.5);
    }}>
      <motion.div className="hero-copy" initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7 }}>
        <div className="eyebrow"><Sparkles size={14} /> Document intelligence, elevated</div>
        <h1>Every document.<br /><span>Instantly understood.</span></h1>
        <p>Hybrid RAG combines semantic search, precision retrieval, and Groq-powered reasoning into one calm, brilliant workspace.</p>
        <div className="hero-actions">
          <a className="button button-primary" href="#experience">
            Get started <ArrowRight size={17} />
          </a>

          <a
            className="button button-secondary"
            href="/analytics"
          >
            📊 Analytics
          </a>

          <a
            className="button button-secondary"
            href="https://github.com/Karthikkkr1085"
            target="_blank"
            rel="noreferrer"
          >
            <Github size={18} /> GitHub
          </a>
        </div>
        <div className="trust-row"><span><i /> Hybrid retrieval</span><span><i /> Grounded answers</span><span><i /> Built for your data</span></div>
      </motion.div>

      <motion.div className="hologram-wrap" style={{ rotateX, rotateY, transformPerspective: 1000 }} initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.15, duration: 0.8 }}>
        <div className="hologram-ring ring-a" /><div className="hologram-ring ring-b" />
        <div className="hologram-core"><div className="core-head"><span className="status-dot" /> Retrieval live <Play size={12} fill="currentColor" /></div><div className="document-lines"><b /><b /><b /><b /><b /></div><div className="document-chip">LeavePolicy.pdf <span>98.7%</span></div></div>
        <div className="floating-tag tag-search">Vector search</div><div className="floating-tag tag-rank">RRF ranked</div><div className="floating-tag tag-groq">Groq response</div>
      </motion.div>
    </section>
  );
}

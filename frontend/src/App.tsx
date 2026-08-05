import { Github, Menu, Sparkles } from "lucide-react";
import { useEffect } from "react";
import {
  Routes,
  Route,
  Link,
  Navigate,
} from "react-router-dom";

import Analytics from "./pages/Analytics";

import { Background } from "./components/Background";
import { ChatPreview } from "./components/ChatPreview";
import { FeatureGrid } from "./components/FeatureGrid";
import { Footer } from "./components/Footer";
import { Hero } from "./components/Hero";
import { Pipeline } from "./components/Pipeline";

function Home() {
  return (
    <main>
      <Background />

      <header className="nav section-shell">
        <a className="brand" href="#top">
          <span>✦</span>
          Hybrid RAG
        </a>

        <nav>
          <a href="#architecture">Architecture</a>

          <a href="#experience">Experience</a>

          <Link to="/analytics">
            Analytics
          </Link>

          <a
            href="https://github.com/Karthikkkr1085"
            target="_blank"
            rel="noreferrer"
          >
            <Github size={16} />
            {" "}
            GitHub
          </a>
        </nav>

        <button
          className="menu-button"
          aria-label="Open menu"
        >
          <Menu size={20} />
        </button>
      </header>

      <div id="top">
        <Hero />
      </div>

      <ChatPreview />

      <FeatureGrid />

      <div id="architecture">
        <Pipeline />
      </div>

      <section className="section-shell closing">
        <div className="glass-card closing-card">
          <Sparkles size={22} />

          <h2>
            Your knowledge,
            <span> in focus.</span>
          </h2>

          <p>
            Give your team answers that are fast,
            grounded, and ready to act on.
          </p>

          <Link
            className="button button-primary"
            to="/analytics"
          >
            Open Analytics Dashboard
          </Link>
        </div>
      </section>

      <Footer />
    </main>
  );
}

export default function App() {
  useEffect(() => {
    if ("scrollRestoration" in history)
      history.scrollRestoration = "manual";

    window.scrollTo({
      top: 0,
      left: 0,
      behavior: "auto",
    });
  }, []);

  return (
    <Routes>
      <Route
        path="/"
        element={<Home />}
      />

      <Route
        path="/analytics"
        element={<Analytics />}
      />

      <Route
        path="*"
        element={<Navigate to="/" />}
      />
    </Routes>
  );
}
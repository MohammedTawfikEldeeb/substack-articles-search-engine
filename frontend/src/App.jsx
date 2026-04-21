import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const API_BASE = (import.meta.env.VITE_API_BASE || "http://localhost:8080").replace(/\/$/, "");
const FEEDS = [
  { name: "Decoding ML", author: "Paul Iusztin" },
  { name: "The Neural Maze", author: "Miguel Otero" },
  { name: "The Machine Learning Engineer", author: "Alejandro Saucedo" },
  { name: "Data Science Weekly", author: "Hannah & Sebastian" },
  { name: "Machine Learning Pills", author: "David Andres" },
  { name: "Ahead of AI", author: "Sebastian Raschka" },
  { name: "One Useful Thing", author: "Ethan Mollick" },
  { name: "Last Week in AI", author: "Davis Blalock" },
  { name: "Import AI", author: "Jack Clark" },
  { name: "Applied ML", author: "Gaurav Chakravorty" },
  { name: "MLOps Newsletter", author: "Bugra Akyildiz" }
];
const FEED_AUTHORS = [...new Set(FEEDS.map((feed) => feed.author).filter(Boolean))].sort();
const FEED_NAMES = [...new Set(FEEDS.map((feed) => feed.name).filter(Boolean))].sort();

function noneIfEmpty(value) {
  const trimmed = value.trim();
  return trimmed.length ? trimmed : null;
}

function buildAskPayload(state) {
  return {
    query_text: state.queryText,
    feed_author: noneIfEmpty(state.feedAuthor),
    feed_name: noneIfEmpty(state.feedName),
    title_keywords: noneIfEmpty(state.titleKeywords),
    limit: Number(state.limit),
    provider: "openrouter"
  };
}

export default function App() {
  const [tab, setTab] = useState("ask");
  const [askView, setAskView] = useState("none");

  const [queryText, setQueryText] = useState("RAG and agentic applications");
  const [feedAuthor, setFeedAuthor] = useState("");
  const [feedName, setFeedName] = useState("");
  const [titleKeywords, setTitleKeywords] = useState("");
  const [limit, setLimit] = useState(5);

  const [titlesResult, setTitlesResult] = useState(null);
  const [askResult, setAskResult] = useState("");
  const [streamResult, setStreamResult] = useState("");
  const [statusMessage, setStatusMessage] = useState("Idle");
  const [busy, setBusy] = useState(false);

  async function searchTitles() {
    setBusy(true);
    setStatusMessage("Searching unique article titles...");
    const payload = {
      query_text: queryText,
      feed_author: noneIfEmpty(feedAuthor),
      feed_name: noneIfEmpty(feedName),
      title_keywords: noneIfEmpty(titleKeywords),
      limit: Number(limit)
    };

    try {
      const response = await fetch(`${API_BASE}/search/unique-titles`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await response.json();
      setTitlesResult(data);
      setStatusMessage("Unique titles loaded");
    } catch (err) {
      setTitlesResult({ error: String(err), payload });
      setStatusMessage("Unique title search failed");
    } finally {
      setBusy(false);
    }
  }

  async function askNonStreaming() {
    setAskView("non-streaming");
    setBusy(true);
    setStatusMessage("Generating non-streaming answer...");
    const payload = buildAskPayload({
      queryText,
      feedAuthor,
      feedName,
      titleKeywords,
      limit
    });

    try {
      const response = await fetch(`${API_BASE}/search/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await response.json();
      setAskResult(data.answer || "");
      setStatusMessage(`Done | model: ${data.model || "automatic"}`);
    } catch (err) {
      setAskResult(`Request failed: ${String(err)}`);
      setStatusMessage("Non-streaming request failed");
    } finally {
      setBusy(false);
    }
  }

  async function askStreaming() {
    setAskView("streaming");
    setBusy(true);
    setStatusMessage("Streaming response...");
    setStreamResult("");

    const payload = buildAskPayload({
      queryText,
      feedAuthor,
      feedName,
      titleKeywords,
      limit
    });

    try {
      const response = await fetch(`${API_BASE}/search/ask/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!response.ok || !response.body) {
        throw new Error(`HTTP ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let fullText = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) {
          break;
        }

        const chunk = decoder.decode(value, { stream: true });

        if (chunk.includes("__error__")) {
          setStatusMessage("Stream returned an error marker");
          continue;
        }

        if (chunk.includes("__truncated__")) {
          setStatusMessage("Stream truncated by token limit");
          continue;
        }

        if (chunk.startsWith("__model_used__:")) {
          const modelName = chunk.replace("__model_used__:", "").trim();
          setStatusMessage(`Streaming | model: ${modelName}`);
          continue;
        }

        fullText += chunk;
        setStreamResult(fullText);
      }

      setStatusMessage((prev) => (prev.startsWith("Streaming") ? "Streaming completed" : prev));
    } catch (err) {
      setStatusMessage("Streaming failed");
      setStreamResult(`Request failed: ${String(err)}`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page-shell">
      <header className="hero">
        <p className="eyebrow">Substack Search Engine</p>
        <h1>Research Console</h1>
        <p className="subtitle">
          Explore search, ask non-streaming, and watch streaming answers in one focused interface.
        </p>
      </header>

      <section className="tab-strip">
        <button className={tab === "ask" ? "active" : ""} onClick={() => setTab("ask")}>Ask</button>
        <button className={tab === "titles" ? "active" : ""} onClick={() => setTab("titles")}>Unique Titles</button>
      </section>

      <section className="workspace-grid">
        <article className="panel input-panel">
          <h2>Inputs</h2>
          <div className="input-stack">
            <div>
              <label>Query</label>
              <textarea value={queryText} onChange={(e) => setQueryText(e.target.value)} rows={4} />
            </div>

            <div className="filters-grid">
              <div>
                <label>Feed author</label>
                <select value={feedAuthor} onChange={(e) => setFeedAuthor(e.target.value)}>
                  <option value="">All feed authors</option>
                  {FEED_AUTHORS.map((author) => (
                    <option key={author} value={author}>{author}</option>
                  ))}
                </select>
              </div>
              <div>
                <label>Feed name</label>
                <select value={feedName} onChange={(e) => setFeedName(e.target.value)}>
                  <option value="">All feed names</option>
                  {FEED_NAMES.map((name) => (
                    <option key={name} value={name}>{name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label>Title keywords</label>
                <input value={titleKeywords} onChange={(e) => setTitleKeywords(e.target.value)} />
              </div>
              <div>
                <label>Limit</label>
                <input
                  type="number"
                  min="1"
                  max="50"
                  value={limit}
                  onChange={(e) => setLimit(Number(e.target.value || 1))}
                />
              </div>
            </div>

            {tab === "ask" && (
              <div className="button-row">
                <button
                  className={askView === "non-streaming" ? "active-action" : ""}
                  onClick={askNonStreaming}
                  disabled={busy}
                >
                  Run Non-Streaming
                </button>
                <button
                  className={askView === "streaming" ? "active-action" : ""}
                  onClick={askStreaming}
                  disabled={busy}
                >
                  Run Streaming
                </button>
              </div>
            )}

            {tab === "titles" && (
              <div className="button-row">
                <button onClick={searchTitles} disabled={busy}>Search Unique Titles</button>
              </div>
            )}

          </div>
        </article>

        <article className="panel output-panel">
          <h2>Output</h2>
          {tab === "ask" && (
            <>
              {askView === "none" && (
                <p className="muted-message">Choose Run Non-Streaming or Run Streaming to display output.</p>
              )}

              {askView === "non-streaming" && (
                <>
                  <h3>Non-Streaming Answer</h3>
                  <article className="markdown-output">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{askResult || "_No response yet._"}</ReactMarkdown>
                  </article>
                </>
              )}

              {askView === "streaming" && (
                <>
                  <h3>Streaming Answer</h3>
                  <article className="markdown-output">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{streamResult || "_No streaming chunks yet._"}</ReactMarkdown>
                  </article>
                </>
              )}
            </>
          )}

          {tab === "titles" && (
            <div className="titles-output">
              {titlesResult?.error && (
                <pre>{JSON.stringify(titlesResult, null, 2)}</pre>
              )}

              {!titlesResult && <p className="muted-message">No results yet.</p>}

              {titlesResult?.results?.length > 0 && (
                <>
                  <p className="result-count">Found {titlesResult.results.length} matching titles</p>
                  <div className="titles-list">
                    {titlesResult.results.map((item, index) => (
                      <article className="title-card" key={`${item.url || item.title}-${index}`}>
                        <h4>{item.title || "Untitled"}</h4>
                        <p className="title-meta">
                          Feed: {item.feed_name || "N/A"} | Author: {item.feed_author || "N/A"}
                        </p>
                        {item.article_author?.length > 0 && (
                          <p className="title-meta">Article authors: {item.article_author.join(", ")}</p>
                        )}
                        {typeof item.score === "number" && (
                          <p className="title-score">Score: {item.score.toFixed(4)}</p>
                        )}
                        {item.url && (
                          <a className="title-link" href={item.url} target="_blank" rel="noreferrer">
                            Open article
                          </a>
                        )}
                      </article>
                    ))}
                  </div>
                </>
              )}

              {titlesResult?.results && titlesResult.results.length === 0 && (
                <p className="muted-message">No matching titles found for this query.</p>
              )}
            </div>
          )}
        </article>
      </section>

      <footer className="status-bar">Status: {statusMessage}</footer>
    </div>
  );
}

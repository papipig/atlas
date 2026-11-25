import { useState, useMemo } from "react";
import { Plus, Trash2, Copy, Check, ExternalLink, Download, ChevronDown, ChevronUp, Search, Rss, AlertTriangle, XCircle, CheckCircle, Globe } from "lucide-react";

const INITIAL_SOURCES = {
  "Think Tanks — France & Europe": [
    { id: 1,  name: "FRS",                               url: "https://www.frstrategie.org/fr/rss.xml",                    status: "uncertain" },
    { id: 3,  name: "IRIS",                              url: "https://www.iris-france.org/feed/",                         status: "ok" },
    { id: 5,  name: "Institut Montaigne",                url: "https://www.institutmontaigne.org/rss.xml",                 status: "uncertain" },
    { id: 7,  name: "Jancovici",                         url: "https://jancovici.com/feed/",                               status: "ok" },
    { id: 11, name: "Fondation Jean Jaurès",             url: "https://www.jean-jaures.org/publications/",                 status: "web",  note: "Pas de flux RSS — surveillance de la page publications" },
    { id: 12, name: "FONDAPOL",                          url: "https://www.fondapol.org/",                                 status: "web",  note: "Pas de flux RSS — surveillance du site" },
    { id: 13, name: "Institut Thomas More",              url: "https://institut-thomas-more.org/",                         status: "web",  note: "Pas de flux RSS — surveillance du site" },
    { id: 14, name: "IFRAP",                             url: "https://www.ifrap.org/",                                    status: "web",  note: "Pas de flux RSS — surveillance du site" },
  ],
  "Think Tanks — International": [
    { id: 21, name: "IISS",                              url: "https://www.iiss.org/",                                     status: "web",  note: "Pas de flux RSS — surveillance du site + newsletter (Proton)" },
    { id: 24, name: "Atlantic Council",                  url: "https://www.atlanticcouncil.org/feed/",                     status: "ok" },
    { id: 26, name: "Hudson Institute — National Security", url: "https://www.hudson.org/national-security-defense",      status: "web",  note: "Surveillance section" },
    { id: 27, name: "Hudson Institute — Domestic Policy",   url: "https://www.hudson.org/domestic-policy",                status: "web",  note: "Surveillance section" },
    { id: 28, name: "Hudson Institute — Trade",             url: "https://www.hudson.org/trade",                          status: "web",  note: "Surveillance section" },
    { id: 29, name: "Hudson Institute — Technology",        url: "https://www.hudson.org/technology",                     status: "web",  note: "Surveillance section" },
    { id: 30, name: "Hudson Institute — Foreign Policy",    url: "https://www.hudson.org/foreign-policy",                 status: "web",  note: "Surveillance section" },
    { id: 31, name: "Hudson Institute — Energy",            url: "https://www.hudson.org/energy",                         status: "web",  note: "Surveillance section" },
    { id: 32, name: "Hudson Institute — Economics",         url: "https://www.hudson.org/economics",                      status: "web",  note: "Surveillance section" },
    { id: 33, name: "Heritage — Defense",                   url: "https://www.heritage.org/defense",                      status: "web",  note: "Surveillance section" },
    { id: 34, name: "Heritage — Cybersecurity",             url: "https://www.heritage.org/cybersecurity",                status: "web",  note: "Surveillance section" },
    { id: 35, name: "Heritage — Global Politics",           url: "https://www.heritage.org/global-politics",              status: "web",  note: "Surveillance section" },
    { id: 36, name: "Heritage — Europe",                    url: "https://www.heritage.org/europe",                       status: "web",  note: "Surveillance section" },
    { id: 37, name: "Heritage — Budget & Spending",         url: "https://www.heritage.org/budget-and-spending",          status: "web",  note: "Surveillance section" },
    { id: 38, name: "Heritage — Conservatism",              url: "https://www.heritage.org/conservatism",                 status: "web",  note: "Surveillance section" },
    { id: 39, name: "Heritage — International Economies",   url: "https://www.heritage.org/international-economies",      status: "web",  note: "Surveillance section" },
    { id: 40, name: "Cato Institute",                       url: "https://www.cato.org/ecommunity/rss",                   status: "web",  note: "Index RSS disponible — plusieurs flux à sélectionner sur la page" },
    { id: 41, name: "German Marshall Fund",                 url: "https://www.gmfus.org/",                                status: "web",  note: "Pas de flux RSS — surveillance du site" },
    { id: 42, name: "Defence Priorities",                   url: "https://www.defensepriorities.org/",                    status: "web",  note: "Pas de flux RSS — surveillance du site" },
    { id: 43, name: "The Marathon Initiative",              url: "https://themarathoninitiative.org/our-work/",           status: "web",  note: "Surveillance de la page travaux" },
    { id: 44, name: "Roosevelt Institute",                  url: "https://rooseveltinstitute.org/publications/",          status: "web",  note: "Surveillance de la page publications" },
    { id: 45, name: "American Compass",                     url: "https://americancompass.org/feed/",                     status: "uncertain" },
    { id: 46, name: "American Moment",                      url: "https://americanmoment.org/the-latest/",                status: "web",  note: "Surveillance de la page actualités" },
    { id: 47, name: "American Mind (Claremont)",            url: "https://americanmind.org/",                             status: "web",  note: "Publication principale du Claremont Institute" },
    { id: 48, name: "Claremont DC — Provocations",         url: "https://dc.claremont.org/provocations/",                status: "web",  note: "Surveillance section" },
    { id: 49, name: "Claremont DC — Media",                url: "https://dc.claremont.org/media/",                       status: "web",  note: "Surveillance section" },
  ],
  "Presse — France": [
    { id: 60, name: "Le Monde",                          url: "https://www.lemonde.fr/rss/une.xml",                        status: "ok" },
    { id: 61, name: "Le Figaro",                         url: "https://www.lefigaro.fr/rss/figaro_actualites.xml",         status: "ok" },
    { id: 62, name: "Le Grand Continent",                url: "https://legrandcontinent.eu/fr/feed/",                      status: "ok" },
    { id: 63, name: "Courrier International",            url: "https://www.courrierinternational.com/feed/all/rss.xml",    status: "ok" },
    { id: 64, name: "Le Monde Diplomatique",             url: "https://www.monde-diplomatique.fr/",                        status: "web",  note: "Pas de flux RSS confirmé — surveillance du site" },
    { id: 65, name: "Marianne",                          url: "https://marianne.net/rss.xml",                              status: "ok" },
    { id: 66, name: "CNews — Général",                   url: "https://www.cnews.fr/rss.xml",                              status: "ok" },
    { id: 67, name: "CNews — France",                    url: "https://www.cnews.fr/rss/categorie/france",                 status: "ok" },
    { id: 68, name: "CNews — Monde",                     url: "https://www.cnews.fr/rss/categorie/monde",                  status: "ok" },
    { id: 69, name: "CNews — Ukraine",                   url: "https://www.cnews.fr/rss/tag/guerre%20en%20ukraine",        status: "ok" },
    { id: 70, name: "France 24 (FR)",                    url: "https://www.france24.com/fr/rss",                           status: "ok" },
    { id: 72, name: "Challenges",                        url: "https://www.challenges.fr/rss.xml",                         status: "uncertain" },
    { id: 73, name: "Newsmap",                           url: "",                                                           status: "unavailable", note: "Agrégateur — pas de flux RSS propre" },
  ],
  "Presse — Internationale": [
    { id: 80, name: "Foreign Policy",                    url: "https://foreignpolicy.com/feed/",                           status: "ok" },
    { id: 81, name: "Washington Post (World)",           url: "https://feeds.washingtonpost.com/rss/world",                status: "ok" },
    { id: 82, name: "Financial Times — Global Economy",  url: "https://www.ft.com/global-economy?format=rss",             status: "ok" },
    { id: 83, name: "Financial Times — Emerging Markets",url: "https://www.ft.com/emerging-markets?format=rss",           status: "ok" },
    { id: 84, name: "Financial Times — Opinion",         url: "https://www.ft.com/opinion?format=rss",                    status: "ok" },
    { id: 85, name: "Financial Times — World",           url: "https://www.ft.com/world?format=rss",                      status: "ok" },
    { id: 86, name: "Financial Times — Energy",          url: "https://www.ft.com/energy?format=rss",                     status: "ok" },
    { id: 87, name: "Financial Times — China",           url: "https://www.ft.com/china?format=rss",                      status: "ok" },
    { id: 88, name: "Financial Times — Africa",          url: "https://www.ft.com/africa?format=rss",                     status: "ok" },
    { id: 89, name: "Boston Globe",                      url: "https://www.bostonglobe.com/",                              status: "web",  note: "Pas de flux RSS confirmé — surveillance du site" },
    { id: 90, name: "BBC News",                          url: "https://feeds.bbci.co.uk/news/rss.xml",                    status: "ok" },
    { id: 91, name: "BBC Global News Podcast",           url: "https://podcasts.files.bbci.co.uk/p02nq0gn.rss",           status: "ok" },
    { id: 93, name: "Daily Mirror",                      url: "https://www.mirror.co.uk/rss.xml",                         status: "uncertain" },
    { id: 94, name: "The Sun",                           url: "https://www.thesun.co.uk/feed/",                           status: "uncertain" },
    { id: 95, name: "The Guardian (World)",              url: "https://www.theguardian.com/world/rss",                    status: "ok" },
    { id: 96, name: "NPR News",                          url: "https://feeds.npr.org/1001/rss.xml",                       status: "ok" },
    { id: 97, name: "NPR Politics Podcast",              url: "https://feeds.npr.org/510310/podcast.xml",                 status: "ok" },
  ],
  "Médias de défense": [
    { id: 110, name: "Defense News — Index RSS",         url: "https://www.defensenews.com/m/rss/",                        status: "web",  note: "Index de tous les flux RSS du site — plusieurs flux thématiques disponibles" },
    { id: 111, name: "Defense News — Land",              url: "https://www.defensenews.com/arc/outboundfeeds/rss/category/land/",   status: "uncertain" },
    { id: 112, name: "Defense News — Air",               url: "https://www.defensenews.com/arc/outboundfeeds/rss/category/air/",    status: "uncertain" },
    { id: 113, name: "Defense News — Naval",             url: "https://www.defensenews.com/arc/outboundfeeds/rss/category/naval/",  status: "uncertain" },
    { id: 114, name: "Defense News — Space",             url: "https://www.defensenews.com/arc/outboundfeeds/rss/category/space/",  status: "uncertain" },
    { id: 115, name: "Defense News — Cyber",             url: "https://www.defensenews.com/arc/outboundfeeds/rss/category/cyber/",  status: "uncertain" },
    { id: 116, name: "Military Times",                   url: "https://www.militarytimes.com/news/",                       status: "web",  note: "Pas de flux RSS confirmé — surveillance de la section news" },
  ],
  "Personnalités politiques — Substituts RSS": [
    { id: 121, name: "Jean-Luc Mélenchon (blog)",        url: "https://melenchon.fr/feed/",                                status: "uncertain", note: "Alternative personnelle à son compte X" },
    { id: 122, name: "Emmanuel Macron (X)",              url: "", status: "unavailable", note: "API X payante (~100$/mois) — remplacé par flux Élysée" },
    { id: 123, name: "Edouard Philippe (X)",             url: "", status: "unavailable", note: "API X payante" },
    { id: 124, name: "Marine Le Pen (X)",                url: "", status: "unavailable", note: "API X payante" },
    { id: 125, name: "Sébastien Lecornu (X)",            url: "", status: "unavailable", note: "API X payante" },
    { id: 126, name: "Catherine Vautrin (X)",            url: "", status: "unavailable", note: "API X payante" },
    { id: 127, name: "Alice Rufo (X)",                   url: "", status: "unavailable", note: "API X payante" },
    { id: 128, name: "Donald Trump (X + Truth Social)",  url: "", status: "unavailable", note: "API X payante. Truth Social : plateforme fermée, pas de RSS" },
    { id: 129, name: "Marco Rubio (X)",                  url: "", status: "unavailable", note: "API X payante" },
    { id: 130, name: "Keir Starmer (X)",                 url: "", status: "unavailable", note: "API X payante" },
    { id: 131, name: "Giorgia Meloni (X)",               url: "", status: "unavailable", note: "API X payante" },
    { id: 132, name: "Pete Hegseth (X)",                 url: "", status: "unavailable", note: "API X payante" },
    { id: 133, name: "JD Vance (X)",                     url: "", status: "unavailable", note: "API X payante" },
  ],
  "Blogs militaires": [
    { id: 140, name: "La Voie de l'Épée",                url: "https://lavoiedelepee.blogspot.com/feeds/posts/default",   status: "ok" },
    { id: 141, name: "Small Wars Journal",               url: "https://smallwarsjournal.com/feed",                        status: "ok" },
  ],
};

const STATUS = {
  ok:          { label: "Flux RSS confirmé",     bg: "#d1fae5", color: "#065f46", Icon: CheckCircle },
  uncertain:   { label: "RSS à vérifier",         bg: "#fef3c7", color: "#92400e", Icon: AlertTriangle },
  web:         { label: "Surveillance site web",  bg: "#dbeafe", color: "#1e40af", Icon: Globe },
  unavailable: { label: "Non disponible",          bg: "#fee2e2", color: "#991b1b", Icon: XCircle },
};

let nextId = 300;

export default function App() {
  const [sources, setSources] = useState(INITIAL_SOURCES);
  const [collapsed, setCollapsed] = useState({});
  const [copied, setCopied]       = useState(null);
  const [addingTo, setAddingTo]   = useState(null);
  const [newName, setNewName]     = useState("");
  const [newUrl, setNewUrl]       = useState("");
  const [newNote, setNewNote]     = useState("");
  const [search, setSearch]       = useState("");
  const [filter, setFilter]       = useState("all");

  const toggle = (cat) => setCollapsed(p => ({ ...p, [cat]: !p[cat] }));

  const copyUrl = (url, id) => {
    navigator.clipboard.writeText(url).then(() => {
      setCopied(id); setTimeout(() => setCopied(null), 2000);
    });
  };

  const remove = (cat, id) =>
    setSources(p => ({ ...p, [cat]: p[cat].filter(s => s.id !== id) }));

  const add = (cat) => {
    if (!newName.trim()) return;
    const s = {
      id: nextId++,
      name: newName.trim(),
      url: newUrl.trim(),
      status: newUrl.trim() ? "uncertain" : "unavailable",
      note: newNote.trim() || undefined,
    };
    setSources(p => ({ ...p, [cat]: [...p[cat], s] }));
    setNewName(""); setNewUrl(""); setNewNote(""); setAddingTo(null);
  };

  const exportCSV = () => {
    const rows = [["Catégorie","Nom","URL","Statut","Note"]];
    Object.entries(sources).forEach(([cat, items]) =>
      items.forEach(s => rows.push([cat, s.name, s.url || "", s.status, s.note || ""]))
    );
    const csv = rows.map(r => r.map(c => `"${c}"`).join(",")).join("\n");
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob(["\uFEFF"+csv], { type: "text/csv;charset=utf-8" }));
    a.download = "flux_rss.csv"; a.click();
  };

  const exportJSON = () => {
    const flat = Object.entries(sources).flatMap(([cat, items]) =>
      items.filter(s => s.url).map(s => ({ category: cat, name: s.name, url: s.url, status: s.status }))
    );
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([JSON.stringify(flat, null, 2)], { type: "application/json" }));
    a.download = "flux_rss_n8n.json"; a.click();
  };

  const stats = useMemo(() => {
    const all = Object.values(sources).flat();
    return {
      total: all.length,
      ok:          all.filter(s => s.status === "ok").length,
      uncertain:   all.filter(s => s.status === "uncertain").length,
      web:         all.filter(s => s.status === "web").length,
      unavailable: all.filter(s => s.status === "unavailable").length,
    };
  }, [sources]);

  const matchesFilters = (s) => {
    const q = search.toLowerCase();
    const nameMatch = !q || s.name.toLowerCase().includes(q) || (s.url||"").toLowerCase().includes(q);
    const statusMatch = filter === "all" || s.status === filter;
    return nameMatch && statusMatch;
  };

  return (
    <div style={{ fontFamily: "'Georgia', 'Times New Roman', serif", background: "#f8f7f4", minHeight: "100vh", color: "#1a1a2e" }}>
      {/* Header */}
      <div style={{ background: "#1a1a2e", color: "white", padding: "24px 20px 20px" }}>
        <div style={{ maxWidth: 740, margin: "0 auto" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
            <div style={{ background: "#c9a84c", borderRadius: 8, padding: 8, display: "flex" }}>
              <Rss size={20} color="white" />
            </div>
            <div>
              <h1 style={{ margin: 0, fontSize: 20, fontWeight: 700, letterSpacing: "-0.3px" }}>Veille stratégique</h1>
              <p style={{ margin: 0, fontSize: 12, color: "#9ca3b0", marginTop: 2 }}>Gestionnaire de sources — Newsletter personnalisée</p>
            </div>
          </div>

          {/* Stats */}
          <div style={{ display: "flex", gap: 16, marginBottom: 16, flexWrap: "wrap" }}>
            {[
              { label: "sources total",     val: stats.total,       c: "#9ca3b0" },
              { label: "flux RSS actifs",   val: stats.ok,          c: "#6ee7b7" },
              { label: "à vérifier",        val: stats.uncertain,   c: "#fcd34d" },
              { label: "surveillance web",  val: stats.web,         c: "#93c5fd" },
              { label: "indisponibles",     val: stats.unavailable, c: "#fca5a5" },
            ].map(({ label, val, c }) => (
              <div key={label} style={{ textAlign: "center" }}>
                <div style={{ fontSize: 22, fontWeight: 700, color: c }}>{val}</div>
                <div style={{ fontSize: 10, color: "#9ca3b0" }}>{label}</div>
              </div>
            ))}
          </div>

          {/* Search + Filter */}
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 10 }}>
            <div style={{ position: "relative", flex: 1, minWidth: 160 }}>
              <Search size={14} style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", color: "#9ca3b0" }} />
              <input
                value={search} onChange={e => setSearch(e.target.value)}
                placeholder="Rechercher une source…"
                style={{ width: "100%", padding: "8px 12px 8px 30px", borderRadius: 8, border: "none", background: "rgba(255,255,255,0.1)", color: "white", fontSize: 13, outline: "none", boxSizing: "border-box" }}
              />
            </div>
            <select
              value={filter} onChange={e => setFilter(e.target.value)}
              style={{ padding: "8px 12px", borderRadius: 8, border: "none", background: "rgba(255,255,255,0.1)", color: "white", fontSize: 13, outline: "none" }}
            >
              <option value="all"        style={{ color: "#000" }}>Tous les statuts</option>
              <option value="ok"         style={{ color: "#000" }}>Flux RSS confirmés</option>
              <option value="uncertain"  style={{ color: "#000" }}>RSS à vérifier</option>
              <option value="web"        style={{ color: "#000" }}>Surveillance web</option>
              <option value="unavailable" style={{ color: "#000" }}>Non disponibles</option>
            </select>
          </div>

          {/* Export */}
          <div style={{ display: "flex", gap: 8 }}>
            <button onClick={exportJSON}
              style={{ flex: 1, background: "#c9a84c", color: "#1a1a2e", border: "none", padding: "9px 0", borderRadius: 8, fontSize: 12, fontWeight: 700, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: 6 }}>
              <Download size={13} /> Export JSON (n8n)
            </button>
            <button onClick={exportCSV}
              style={{ flex: 1, background: "rgba(255,255,255,0.12)", color: "white", border: "none", padding: "9px 0", borderRadius: 8, fontSize: 12, fontWeight: 600, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: 6 }}>
              <Download size={13} /> Export CSV
            </button>
          </div>
        </div>
      </div>

      {/* Légende */}
      <div style={{ maxWidth: 740, margin: "0 auto", padding: "12px 20px 4px", display: "flex", gap: 8, flexWrap: "wrap" }}>
        {Object.entries(STATUS).map(([key, { label, bg, color, Icon }]) => (
          <span key={key} style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 11, background: bg, color, padding: "4px 10px", borderRadius: 20, fontWeight: 600 }}>
            <Icon size={11} /> {label}
          </span>
        ))}
      </div>

      {/* Categories */}
      <div style={{ maxWidth: 740, margin: "0 auto", padding: "8px 20px 40px" }}>
        {Object.entries(sources).map(([cat, items]) => {
          const visible = items.filter(matchesFilters);
          if (visible.length === 0 && (search || filter !== "all")) return null;
          const isOpen = !collapsed[cat];

          return (
            <div key={cat} style={{ background: "white", borderRadius: 12, marginBottom: 10, overflow: "hidden", boxShadow: "0 1px 3px rgba(0,0,0,0.07)" }}>
              <button
                onClick={() => toggle(cat)}
                style={{ width: "100%", display: "flex", alignItems: "center", justifyContent: "space-between", padding: "14px 16px", background: "none", border: "none", cursor: "pointer", textAlign: "left" }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  {isOpen ? <ChevronUp size={15} color="#9ca3b0" /> : <ChevronDown size={15} color="#9ca3b0" />}
                  <span style={{ fontWeight: 700, fontSize: 13, color: "#1a1a2e" }}>{cat}</span>
                  <span style={{ fontSize: 11, background: "#f3f4f6", color: "#6b7280", padding: "2px 8px", borderRadius: 20 }}>
                    {visible.length}{visible.length !== items.length ? `/${items.length}` : ""}
                  </span>
                </div>
              </button>

              {isOpen && (
                <div style={{ borderTop: "1px solid #f3f4f6" }}>
                  {visible.map((s, i) => {
                    const cfg = STATUS[s.status];
                    const IconComp = cfg.Icon;
                    return (
                      <div key={s.id} style={{ display: "flex", alignItems: "flex-start", gap: 10, padding: "10px 16px", borderBottom: i < visible.length - 1 ? "1px solid #f9fafb" : "none", background: i % 2 === 0 ? "white" : "#fafafa" }}>
                        <div style={{ paddingTop: 2, flexShrink: 0 }}>
                          <IconComp size={14} color={cfg.color} />
                        </div>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ fontWeight: 600, fontSize: 13, color: "#1a1a2e" }}>{s.name}</div>
                          {s.url && (
                            <div style={{ fontSize: 11, color: "#9ca3b0", marginTop: 2, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                              {s.url}
                            </div>
                          )}
                          {s.note && (
                            <div style={{ fontSize: 11, color: "#c9a84c", marginTop: 2, fontStyle: "italic" }}>{s.note}</div>
                          )}
                        </div>
                        <div style={{ display: "flex", gap: 4, alignItems: "center", flexShrink: 0 }}>
                          {s.url && (
                            <>
                              <button onClick={() => copyUrl(s.url, s.id)} title="Copier l'URL"
                                style={{ background: "none", border: "none", cursor: "pointer", padding: 5, borderRadius: 6, color: copied === s.id ? "#065f46" : "#9ca3b0", display: "flex" }}>
                                {copied === s.id ? <Check size={14} /> : <Copy size={14} />}
                              </button>
                              <a href={s.url} target="_blank" rel="noopener noreferrer"
                                style={{ padding: 5, borderRadius: 6, color: "#9ca3b0", display: "flex" }} title="Ouvrir">
                                <ExternalLink size={14} />
                              </a>
                            </>
                          )}
                          <button onClick={() => remove(cat, s.id)} title="Supprimer"
                            style={{ background: "none", border: "none", cursor: "pointer", padding: 5, borderRadius: 6, color: "#e5c5c5", display: "flex" }}>
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </div>
                    );
                  })}

                  {addingTo === cat ? (
                    <div style={{ padding: 14, background: "#f0f9ff", borderTop: "1px solid #e0f2fe" }}>
                      <input value={newName} onChange={e => setNewName(e.target.value)} placeholder="Nom de la source *"
                        style={{ width: "100%", padding: "8px 12px", borderRadius: 8, border: "1px solid #bae6fd", fontSize: 13, marginBottom: 8, boxSizing: "border-box", outline: "none" }} />
                      <input value={newUrl} onChange={e => setNewUrl(e.target.value)} placeholder="URL (flux RSS ou site web)"
                        style={{ width: "100%", padding: "8px 12px", borderRadius: 8, border: "1px solid #bae6fd", fontSize: 13, marginBottom: 8, boxSizing: "border-box", outline: "none" }} />
                      <input value={newNote} onChange={e => setNewNote(e.target.value)} placeholder="Note (optionnel)"
                        style={{ width: "100%", padding: "8px 12px", borderRadius: 8, border: "1px solid #bae6fd", fontSize: 13, marginBottom: 10, boxSizing: "border-box", outline: "none" }} />
                      <div style={{ display: "flex", gap: 8 }}>
                        <button onClick={() => add(cat)}
                          style={{ flex: 1, background: "#1a1a2e", color: "white", border: "none", padding: "9px 0", borderRadius: 8, fontSize: 13, fontWeight: 600, cursor: "pointer" }}>
                          Ajouter
                        </button>
                        <button onClick={() => { setAddingTo(null); setNewName(""); setNewUrl(""); setNewNote(""); }}
                          style={{ flex: 1, background: "#e5e7eb", color: "#374151", border: "none", padding: "9px 0", borderRadius: 8, fontSize: 13, cursor: "pointer" }}>
                          Annuler
                        </button>
                      </div>
                    </div>
                  ) : (
                    <button onClick={() => setAddingTo(cat)}
                      style={{ width: "100%", display: "flex", alignItems: "center", gap: 8, padding: "10px 16px", background: "none", border: "none", cursor: "pointer", color: "#9ca3b0", fontSize: 12, borderTop: "1px solid #f3f4f6" }}>
                      <Plus size={13} /> Ajouter une source dans cette catégorie
                    </button>
                  )}
                </div>
              )}
            </div>
          );
        })}

        <div style={{ background: "#fff8e1", border: "1px solid #fcd34d", borderRadius: 12, padding: 16, marginTop: 8 }}>
          <div style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
            <AlertTriangle size={16} color="#92400e" style={{ flexShrink: 0, marginTop: 2 }} />
            <div style={{ fontSize: 12, color: "#78350f", lineHeight: 1.6 }}>
              <strong>Comptes X / Truth Social :</strong> Ces plateformes ne fournissent pas de flux RSS gratuits. L'API X coûte ~100$/mois. La meilleure stratégie pour les personnalités politiques est de suivre leurs sites officiels ou communications de presse via RSS.
              <br /><br />
              <strong>Sources "Surveillance site web" :</strong> Ces sites seront interrogés directement par n8n via un scraping léger de leur page de publications. Les nouvelles parutions seront comparées à la veille pour identifier les nouveautés.
              <br /><br />
              <strong>Newsletters :</strong> Les newsletters auxquelles vous êtes abonné seront intégrées via n8n — les identifiants email doivent être configurés dans le gestionnaire de credentials sécurisé de n8n, jamais dans cette application.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

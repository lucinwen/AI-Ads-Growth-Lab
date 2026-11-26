import { useEffect, useState, type ReactNode } from "react";
import {
  Activity, ArrowUpRight, BarChart3, Bell, Bot, Check,
  ChevronDown, CircleHelp, Clock3, CloudUpload, FileCheck2, FlaskConical,
  Gauge, Image, LayoutDashboard, Layers3, Menu,
  MoreHorizontal, Plus, Search, ShieldCheck, Sparkles, Target, WandSparkles,
  X, Zap
} from "lucide-react";
import {
  Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";

type MetricSet = {
  ctr: number | null; cpc_usd: number | null; lpv_rate: number | null;
  atc_rate: number | null; cvr_click_to_purchase: number | null;
  cpa_usd: number | null; aov_usd: number | null; roas: number | null;
  refund_rate: number | null;
};
type Totals = {
  impressions: number; clicks: number; landing_page_views: number;
  add_to_cart: number; purchases: number; refunded_orders: number;
  spend_usd: number; attributed_revenue_usd: number;
};
type CreativeRow = { creative_id: string; concept: string; variant: string; totals: Totals; metrics: MetricSet };
type DailyRow = { date: string; spend_usd: number; revenue_usd: number; impressions: number; clicks: number; purchases: number; roas: number | null; ctr: number | null };
type Overview = {
  experiment_id: string; workspace_id: string; product_id: string; workspace: string; data_mode: "SIMULATED" | "REAL";
  source: string; date_range: { start: string; end: string }; row_count: number;
  creative_count: number; summary: { totals: Totals; metrics: MetricSet };
  daily: DailyRow[]; creatives: CreativeRow[];
  funnel: { stage: string; value: number }[]; limitations: string[];
};

const API = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const money = (n?: number | null) => n == null ? "—" : new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: n < 10 ? 2 : 0 }).format(n);
const number = (n?: number | null) => n == null ? "—" : new Intl.NumberFormat("en-US", { notation: n > 9999 ? "compact" : "standard", maximumFractionDigits: 1 }).format(n);
const percent = (n?: number | null) => n == null ? "—" : (n * 100).toFixed(2) + "%";
const conceptName: Record<string, string> = {
  "C-A": "Everyday ritual", "C-B": "Texture study", "C-C": "Ingredient education", "C-D": "Creator walkthrough"
};
const nav = [
  { id: "overview", label: "Overview", icon: LayoutDashboard, group: "WORKSPACE" },
  { id: "creative", label: "Creative studio", icon: WandSparkles, group: "WORKSPACE" },
  { id: "experiments", label: "Experiments", icon: FlaskConical, group: "MEASUREMENT" },
  { id: "insights", label: "Growth insights", icon: BarChart3, group: "MEASUREMENT" },
  { id: "agents", label: "Agent activity", icon: Bot, group: "SYSTEM" },
];

function Pill({ children, tone = "neutral" }: { children: ReactNode; tone?: "neutral" | "green" | "amber" | "blue" }) {
  return <span className={`pill pill-${tone}`}>{children}</span>;
}
function MetricCard({ label, value, hint, icon, accent }: { label: string; value: string; hint: string; icon: ReactNode; accent?: string }) {
  return <div className="metric-card">
    <div className="metric-top"><span>{label}</span><span className={`metric-icon ${accent || ""}`}>{icon}</span></div>
    <div className="metric-value">{value}</div><div className="metric-hint">{hint}</div>
  </div>;
}
function SectionTitle({ title, desc, action }: { title: string; desc?: string; action?: ReactNode }) {
  return <div className="section-title"><div><h2>{title}</h2>{desc && <p>{desc}</p>}</div>{action}</div>;
}

export default function App() {
  const [page, setPage] = useState("overview");
  const [overview, setOverview] = useState<Overview | null>(null);
  const [loading, setLoading] = useState(true);
  const [apiError, setApiError] = useState("");
  const [refresh, setRefresh] = useState(0);
  const [mobileNav, setMobileNav] = useState(false);
  const [search, setSearch] = useState("");
  const [toast, setToast] = useState("");
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<string>("");
  const [drafts, setDrafts] = useState<{id:string;title:string;angle:string;hook:string;hypothesis:string;format:string;status:string}[]>([]);
  const [newHook, setNewHook] = useState("");

  useEffect(() => {
    let active = true;
    setLoading(true);
    fetch(`${API}/v1/demo/overview`)
      .then(r => { if (!r.ok) throw new Error(`API returned ${r.status}`); return r.json(); })
      .then(data => { if (active) { setOverview(data); setApiError(""); } })
      .catch(err => { if (active) setApiError(String(err.message || err)); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [refresh]);

  useEffect(() => {
    if (!overview?.workspace_id) return;
    fetch(`${API}/v1/workspaces/${overview.workspace_id}/creatives`)
      .then(r => { if (!r.ok) throw new Error("Could not load saved creative hypotheses"); return r.json(); })
      .then(rows => setDrafts(rows.map((row: any) => ({
        id: row.id, title: row.concept_name, angle: row.angle || "Unspecified angle",
        hook: row.hook || "Hook not drafted", hypothesis: row.hypothesis || "Hypothesis to be defined.",
        format: row.format || "Format not specified", status: "Saved in workspace"
      }))))
      .catch(err => setApiError(String(err.message || err)));
  }, [overview?.workspace_id]);

  const notify = (message: string) => {
    setToast(message);
    window.setTimeout(() => setToast(""), 3000);
  };

  async function importCsv(file?: File) {
    if (!file) return;
    setImporting(true); setImportResult("");
    const form = new FormData(); form.append("file", file);
    try {
      const res = await fetch(`${API}/v1/import/csv/validate?data_mode=SIMULATED`, { method: "POST", body: form });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Import validation failed");
      setImportResult(`Validated ${data.validated_rows} rows · ${data.data_mode} · ROAS ${data.aggregate.metrics.roas?.toFixed(2) ?? "N/A"}x`);
      notify("CSV validation complete");
    } catch (err) {
      setImportResult(String((err as Error).message));
    } finally { setImporting(false); }
  }

  const pageTitle = nav.find(n => n.id === page)?.label || "Overview";

  return <div className="app-shell">
    <aside className={`sidebar ${mobileNav ? "sidebar-open" : ""}`}>
      <div className="brand-lockup">
        <div className="brand-mark"><Sparkles size={18} /></div>
        <div><strong>growthlab</strong><small>AI CREATIVE INTELLIGENCE</small></div>
        <button className="mobile-close" onClick={() => setMobileNav(false)}><X size={18}/></button>
      </div>
      <div className="workspace-switch"><div className="workspace-avatar">LD</div><div className="workspace-copy"><strong>Luma Dew</strong><span>US Beauty Demo</span></div><ChevronDown size={15}/></div>
      {["WORKSPACE", "MEASUREMENT", "SYSTEM"].map(group => <div className="nav-group" key={group}>
        <div className="nav-label">{group}</div>
        {nav.filter(n => n.group === group).map(item => {
          const Icon = item.icon;
          return <button key={item.id} className={`nav-item ${page === item.id ? "active" : ""}`} onClick={() => { setPage(item.id); setMobileNav(false); }}>
            <Icon size={17}/><span>{item.label}</span>{item.id === "agents" && <i className="nav-dot"/>}
          </button>;
        })}
      </div>)}
      <div className="sidebar-bottom">
        <div className="help-card"><CircleHelp size={17}/><div><strong>Need a hand?</strong><span>Explore the project guide</span></div></div>
        <div className="user-row"><div className="user-avatar">文</div><div><strong>文欣璐</strong><span>Project owner</span></div><MoreHorizontal size={17}/></div>
      </div>
    </aside>
    {mobileNav && <div className="scrim" onClick={() => setMobileNav(false)} />}
    <main className="main-area">
      <header className="topbar">
        <button className="mobile-menu" onClick={() => setMobileNav(true)}><Menu size={19}/></button>
        <div className="breadcrumbs">Workspace <span>/</span> <strong>{pageTitle}</strong></div>
        <div className="top-actions"><div className="search-box"><Search size={15}/><input placeholder="Search creatives..." value={search} onChange={e=>setSearch(e.target.value)}/><kbd>⌘ K</kbd></div><button className="icon-button"><Bell size={17}/><i/></button><div className="top-avatar">文</div></div>
      </header>
      <div className="content">
        <div className="page-heading">
          <div><div className="eyebrow">AI ADS GROWTH LAB <span>·</span> US BEAUTY & SKINCARE</div><h1>{page === "overview" ? "Creative performance" : pageTitle}</h1><p>{page === "overview" ? "A clearer view from creative hypotheses to measurable outcomes." : page === "creative" ? "Shape, compare and prepare creative concepts for controlled testing." : page === "experiments" ? "Pre-register hypotheses, isolate variables and understand what changed." : page === "insights" ? "Turn funnel signals into the next creative and growth decisions." : "Trace each workflow run, approval and system decision."}</p></div>
          <div className="heading-actions"><Pill tone="green"><span className="status-dot"/> Demo workspace</Pill><button className="button button-primary" onClick={()=>setPage("creative")}><Plus size={16}/> New brief</button></div>
        </div>

        {apiError && <div className="api-alert"><div><strong>API connection unavailable</strong><span>Start the FastAPI service to load live demo metrics. The interface is running, but no numbers are being invented.</span></div><button onClick={()=>setRefresh(v=>v+1)}>Retry connection</button></div>}
        {page === "overview" && <OverviewPage overview={overview} loading={loading} search={search} onImport={importCsv} importing={importing} importResult={importResult} onRefresh={()=>setRefresh(v=>v+1)} />}
        {page === "creative" && <CreativePage drafts={drafts} setDrafts={setDrafts} newHook={newHook} setNewHook={setNewHook} notify={notify} workspaceId={overview?.workspace_id || ""} productId={overview?.product_id || ""}/>}
        {page === "experiments" && <ExperimentsPage overview={overview} loading={loading}/>}
        {page === "insights" && <InsightsPage overview={overview} loading={loading}/>}
        {page === "agents" && <AgentsPage/>}
        <footer className="footer"><span>AI Ads Growth Lab <b>V1.1</b></span><span>SIMULATED DATA · NOT LIVE MEDIA PERFORMANCE</span></footer>
      </div>
    </main>
    {toast && <div className="toast"><Check size={16}/>{toast}</div>}
  </div>;
}

function OverviewPage({overview,loading,search,onImport,importing,importResult,onRefresh}:{
  overview:Overview|null;loading:boolean;search:string;onImport:(f?:File)=>void;importing:boolean;importResult:string;onRefresh:()=>void;
}) {
  const m=overview?.summary.metrics; const t=overview?.summary.totals;
  const visibleCreatives=(overview?.creatives||[]).filter(c=>[c.creative_id,conceptName[c.concept]||c.concept].join(" ").toLowerCase().includes(search.toLowerCase()));
  return <>
    <div className="data-banner"><div className="banner-left"><span className="banner-icon"><Activity size={17}/></span><div><strong>SIMULATED DATASET</strong><span>84 synthetic daily records · 12 creative variants · Dec 01–07, 2026</span></div></div><div className="banner-right"><span>Source: bundled demo CSV</span><button onClick={onRefresh}>Refresh <Activity size={13}/></button></div></div>
    <div className="metric-grid">
      <MetricCard label="Ad spend" value={loading?"…":money(t?.spend_usd)} hint="Synthetic spend · USD" icon={<Gauge size={17}/>} />
      <MetricCard label="Attributed revenue" value={loading?"…":money(t?.attributed_revenue_usd)} hint="Synthetic attributed revenue" icon={<BarChart3 size={17}/>} accent="teal"/>
      <MetricCard label="ROAS" value={loading?"…":m?.roas==null?"—":m.roas.toFixed(2)+"x"} hint="Revenue / ad spend · not ROI" icon={<Target size={17}/>} accent="purple"/>
      <MetricCard label="CTR" value={loading?"…":percent(m?.ctr)} hint={`${number(t?.clicks)} clicks / ${number(t?.impressions)} impressions`} icon={<Zap size={17}/>} accent="orange"/>
      <MetricCard label="Click → purchase CVR" value={loading?"…":percent(m?.cvr_click_to_purchase)} hint={`${number(t?.purchases)} attributed purchases`} icon={<ArrowUpRight size={17}/>} accent="blue"/>
    </div>
    <div className="two-col main-charts">
      <div className="panel chart-panel">
        <div className="panel-head"><div><h3>Spend & attributed revenue</h3><p>Daily trend · USD</p></div><Pill>7-day view</Pill></div>
        {overview ? <div className="chart-wrap"><ResponsiveContainer width="100%" height={245}><AreaChart data={overview.daily} margin={{top:10,right:8,left:-16,bottom:0}}>
          <defs><linearGradient id="revFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#16a394" stopOpacity={.2}/><stop offset="95%" stopColor="#16a394" stopOpacity={0}/></linearGradient><linearGradient id="spendFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#8b9aaa" stopOpacity={.16}/><stop offset="95%" stopColor="#8b9aaa" stopOpacity={0}/></linearGradient></defs>
          <CartesianGrid stroke="#edf0f3" vertical={false}/><XAxis dataKey="date" tickFormatter={v=>v.slice(5)} tickLine={false} axisLine={false} tick={{fontSize:11,fill:"#87929c"}}/><YAxis tickLine={false} axisLine={false} tick={{fontSize:11,fill:"#87929c"}} tickFormatter={v=>"$"+Math.round(v/100)/10+"k"}/><Tooltip formatter={(v:any)=>money(Number(v))} labelFormatter={v=>String(v)}/><Area type="monotone" dataKey="revenue_usd" name="Attributed revenue" stroke="#159c8d" strokeWidth={2.5} fill="url(#revFill)"/><Area type="monotone" dataKey="spend_usd" name="Ad spend" stroke="#94a3b8" strokeWidth={2} fill="url(#spendFill)"/>
        </AreaChart></ResponsiveContainer></div> : <ChartSkeleton/>}
        <div className="chart-legend"><span><i className="legend-dot revenue"/>Attributed revenue</span><span><i className="legend-dot spend"/>Ad spend</span></div>
      </div>
      <div className="panel funnel-panel">
        <div className="panel-head"><div><h3>Conversion funnel</h3><p>From impression to purchase</p></div><MoreHorizontal size={18}/></div>
        {overview ? <div className="funnel-list">{overview.funnel.map((f,i)=>{
          const max=overview.funnel[0]?.value||1;
          return <div className="funnel-row" key={f.stage}><div className="funnel-meta"><span>{f.stage}</span><strong>{number(f.value)}</strong></div><div className="funnel-track"><div style={{width:`${Math.max(3,f.value/max*100)}%`}} className={`funnel-fill funnel-${i}`}/></div>{i>0&&<div className="funnel-rate">{percent(f.value/(overview.funnel[i-1]?.value||1))} from previous step</div>}</div>;
        })}</div> : <ChartSkeleton/>}
        <div className="funnel-note"><ShieldCheck size={15}/> Rates use aggregated event counts. Attribution definitions remain demo assumptions.</div>
      </div>
    </div>
    <div className="panel table-panel">
      <div className="panel-head"><div><h3>Creative performance</h3><p>Compare creative hypotheses across 12 variants</p></div><Pill tone="blue">12 variants</Pill></div>
      {overview ? <div className="table-scroll"><table><thead><tr><th>CREATIVE</th><th>IMPRESSIONS</th><th>CTR</th><th>CVR</th><th>SPEND</th><th>CPA</th><th>ROAS</th><th>STATUS</th></tr></thead><tbody>{visibleCreatives.sort((a,b)=>(b.metrics.roas||0)-(a.metrics.roas||0)).slice(0,8).map((c,i)=><tr key={c.creative_id}><td><div className="creative-cell"><div className={`creative-thumb thumb-${c.concept.toLowerCase()}`}>{c.concept.slice(-1)}</div><div><strong>{conceptName[c.concept]||c.concept}</strong><span>{c.creative_id}</span></div></div></td><td>{number(c.totals.impressions)}</td><td>{percent(c.metrics.ctr)}</td><td>{percent(c.metrics.cvr_click_to_purchase)}</td><td>{money(c.totals.spend_usd)}</td><td>{money(c.metrics.cpa_usd)}</td><td><strong>{c.metrics.roas?.toFixed(2)}x</strong></td><td><Pill tone={i===0?"green":"neutral"}>{i===0?"Top demo ROAS":"Synthetic"}</Pill></td></tr>)}</tbody></table></div> : <ChartSkeleton/>}
      <div className="table-foot"><span>Showing {Math.min(8,visibleCreatives.length)} of {visibleCreatives.length} matching variants</span><span>Ranked by synthetic ROAS · descriptive only</span></div>
    </div>
    <div className="bottom-grid">
      <div className="panel upload-panel"><div className="panel-head"><div><h3>Import experiment data</h3><p>Validate a CSV against the current schema</p></div><CloudUpload size={18}/></div><label className="upload-zone"><input type="file" accept=".csv" onChange={e=>onImport(e.target.files?.[0])}/><CloudUpload size={22}/><strong>{importing?"Validating…":"Drop a CSV or browse files"}</strong><span>SIMULATED mode only in this demo flow</span></label>{importResult&&<div className="import-result">{importResult}</div>}</div>
      <div className="panel callout-panel"><div className="callout-icon"><Sparkles size={18}/></div><div><h3>What this data can tell you</h3><p>Use this demo to test metric calculation, funnel diagnosis and creative comparison. It cannot prove real market lift or causal impact.</p><span>Next milestone · Persistent experiment workspace</span></div></div>
    </div>
  </>;
}
function ChartSkeleton(){return <div className="skeleton-chart"><div/><div/><div/><div/><div/><div/><div/></div>}

function CreativePage({drafts,setDrafts,newHook,setNewHook,notify,workspaceId,productId}:{
  drafts:{id:string;title:string;angle:string;hook:string;hypothesis:string;format:string;status:string}[];
  setDrafts:(v:any)=>void;newHook:string;setNewHook:(v:string)=>void;notify:(s:string)=>void;workspaceId:string;productId:string;
}) {
  async function saveCreativeDraft() {
    if (!newHook.trim() || !workspaceId || !productId) return;
    try {
      const response = await fetch(`${API}/v1/creatives`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          workspace_id: workspaceId, product_id: productId,
          concept_name: "Custom concept", angle: "Custom hypothesis",
          hook: newHook.trim(), hypothesis: "Hypothesis to be defined and reviewed.",
          format: "Draft · not generated", language: "en-US"
        })
      });
      const row = await response.json();
      if (!response.ok) throw new Error(row.detail || "Could not save creative draft");
      setDrafts((old:any)=>[{id:row.id,title:row.concept_name,angle:row.angle,hook:row.hook,hypothesis:row.hypothesis,format:row.format,status:"Saved in workspace"},...old]);
      setNewHook("");
      notify("Creative hypothesis saved to workspace.");
    } catch (err) {
      notify(String((err as Error).message || err));
    }
  }
  return <div className="page-stack">
    <div className="creative-intro panel"><div className="intro-symbol"><WandSparkles size={24}/></div><div><h3>From product facts to testable creative hypotheses</h3><p>Draft distinct creative routes before generating assets. Every objective claim must be linked to evidence before an asset can enter review.</p></div><Pill tone="amber">Strategy workspace</Pill></div>
    <SectionTitle title="Creative routes" desc="Four differentiated directions for the fictional Luma Dew moisturizer." action={<Pill tone="green">4 concepts</Pill>}/>
    <div className="concept-grid">{drafts.map((d,i)=><div className="concept-card" key={d.id}><div className="concept-top"><span className={`concept-number n-${i}`}>0{i+1}</span><Pill tone={d.status.includes("Needs")?"amber":"neutral"}>{d.status}</Pill></div><div className={`concept-art art-${i}`}><div className="art-bottle"/><span>{["DAILY RITUAL","TEXTURE NOTES","FORMULA / FACTS","REAL-LIFE ROUTINE"][i]}</span></div><div className="concept-body"><span className="concept-angle">{d.angle}</span><h3>{d.title}</h3><blockquote>“{d.hook}”</blockquote><p>{d.hypothesis}</p><div className="concept-foot"><span><Image size={14}/>{d.format}</span><button onClick={()=>notify("Concept detail editor is queued for the next milestone.")}>View brief <ArrowUpRight size={14}/></button></div></div></div>)}</div>
    <div className="panel quick-draft"><div><h3><Plus size={17}/> Add a creative hypothesis</h3><p>Save a new hook as a local draft. This does not call a generation model.</p></div><div className="draft-form"><input value={newHook} onChange={e=>setNewHook(e.target.value)} placeholder="Write an English hook or creative angle…"/><button className="button button-primary" disabled={!newHook.trim() || !workspaceId} onClick={saveCreativeDraft}><Plus size={15}/> Save draft</button></div></div>
    <div className="compliance-inline"><ShieldCheck size={17}/><div><strong>Claim evidence gate</strong><span>“Clinically proven”, acne-treatment and unsupported before/after claims remain blocked until evidence and regulatory review are attached.</span></div><Pill tone="amber">Human review required</Pill></div>
  </div>;
}

function ExperimentsPage({overview,loading}:{overview:Overview|null;loading:boolean}) {
  const [experiments,setExperiments] = useState<any[]>([]);
  const [name,setName] = useState("US skincare creative angle test");
  const [hypothesis,setHypothesis] = useState("Different creative framing will produce different attention and click-to-purchase patterns.");
  const [saving,setSaving] = useState(false);
  const [message,setMessage] = useState("");
  useEffect(() => {
    if (!overview?.workspace_id) return;
    fetch(`${API}/v1/workspaces/${overview.workspace_id}/experiments`)
      .then(r => { if (!r.ok) throw new Error("Could not load experiments"); return r.json(); })
      .then(setExperiments)
      .catch(err => setMessage(String(err.message || err)));
  }, [overview?.workspace_id]);
  async function createExperiment() {
    if (!overview?.workspace_id || !name.trim() || !hypothesis.trim()) return;
    setSaving(true); setMessage("");
    try {
      const response = await fetch(`${API}/v1/experiments`, {
        method:"POST", headers:{"Content-Type":"application/json"},
        body:JSON.stringify({
          workspace_id:overview.workspace_id, name:name.trim(), hypothesis:hypothesis.trim(),
          channel:"TikTok", data_mode:"SIMULATED", attribution_window:"7-day click",
          timezone:"America/Los_Angeles", budget_cap_cents:120000, currency:"USD"
        })
      });
      const created = await response.json();
      if (!response.ok) throw new Error(created.detail || "Could not create experiment");
      const creatives = await fetch(`${API}/v1/workspaces/${overview.workspace_id}/creatives`).then(r=>r.json());
      const selected = creatives.slice(0,4);
      for (let i=0;i<selected.length;i++) {
        const variantResponse = await fetch(`${API}/v1/experiments/${created.id}/variants`, {
          method:"POST", headers:{"Content-Type":"application/json"},
          body:JSON.stringify({creative_id:selected[i].id,allocation_pct:100/selected.length,role:i===0?"CONTROL":"TREATMENT"})
        });
        if (!variantResponse.ok) throw new Error("Experiment created, but a creative variant could not be attached.");
      }
      const variants = await fetch(`${API}/v1/experiments/${created.id}/variants`).then(r=>r.json());
      setExperiments(old=>[{...created,variant_count:variants.length},...old]);
      setMessage("Experiment saved with " + variants.length + " creative variants. This is a configuration record, not a live ad campaign.");
    } catch (err) {
      setMessage(String((err as Error).message || err));
    } finally { setSaving(false); }
  }
  return <div className="page-stack">
    <div className="panel experiment-hero"><div><Pill tone="green">EXP-US-BEAUTY-001</Pill><h2>Creative angle exploration</h2><p>Compare four creative hypotheses using a fixed fictional product and a synthetic seven-day dataset.</p><div className="hero-meta"><span><Clock3 size={14}/> Dec 01–07, 2026</span><span><Layers3 size={14}/> 4 concepts / 12 variants</span><span><FlaskConical size={14}/> Descriptive demo</span></div></div><div className="hero-stamp">SIM<br/>DATA</div></div>
    <div className="metric-grid compact">
      <MetricCard label="Creative variants" value="12" hint="4 concepts × 3 versions" icon={<Layers3 size={17}/>}/>
      <MetricCard label="Daily records" value={overview?String(overview.row_count):"—"} hint="Synthetic metric rows" icon={<Activity size={17}/>} accent="teal"/>
      <MetricCard label="Impressions" value={loading?"…":number(overview?.summary.totals.impressions)} hint="Aggregated across variants" icon={<Image size={17}/>} accent="purple"/>
      <MetricCard label="Purchases" value={loading?"…":number(overview?.summary.totals.purchases)} hint="Synthetic attributed events" icon={<Target size={17}/>} accent="blue"/>
    </div>
    <div className="panel">
      <SectionTitle title="Create an experiment" desc="Save an experiment definition and attach the four seeded creative hypotheses."/>
      <div className="experiment-form">
        <label>Experiment name<input value={name} onChange={e=>setName(e.target.value)} /></label>
        <label>Hypothesis<textarea value={hypothesis} onChange={e=>setHypothesis(e.target.value)} rows={2}/></label>
        <div className="form-actions"><span>Mode: SIMULATED · Channel: TikTok · Budget cap: $1,200 (not spent)</span><button className="button button-primary" disabled={saving||!overview?.workspace_id} onClick={createExperiment}><Plus size={15}/>{saving?"Saving…":"Create experiment"}</button></div>
        {message&&<div className="import-result">{message}</div>}
      </div>
    </div>
    <div className="panel"><SectionTitle title="Saved experiment records" desc="Persistent local records. These do not launch ads or spend budget."/>
      {experiments.length ? <div className="saved-experiments">{experiments.map((e:any)=><div className="saved-experiment" key={e.id}><div className="experiment-icon"><FlaskConical size={17}/></div><div className="saved-exp-copy"><strong>{e.name}</strong><span>{e.hypothesis}</span><small>{e.channel} · {e.data_mode} · {e.status}</small></div><Pill tone="blue">{e.variant_count ?? "Saved" } variants</Pill></div>)}</div> : <div className="empty-state-inline">{loading?"Loading workspace…":"No saved experiments yet. Create one above to persist the hypothesis and variants."}</div>}
    </div>
    <div className="panel"><SectionTitle title="Experiment design" desc="Pre-registration framework for a future real test."/><div className="design-grid"><div><span>PRIMARY QUESTION</span><strong>Which creative framing earns qualified attention without weakening downstream conversion?</strong></div><div><span>PRIMARY METRICS</span><strong>CTR and click-to-purchase CVR, reported separately</strong></div><div><span>CONTROL VARIABLES</span><strong>Product, offer, landing page, audience, placement, schedule</strong></div><div><span>GUARDRAILS</span><strong>Claim risk, landing-page mismatch, tracking quality, refunds</strong></div></div></div>
    <div className="panel"><SectionTitle title="Creative hypothesis matrix" desc="The hypotheses are not conclusions; the data is synthetic."/><div className="hypothesis-list">{["Routine framing may fit naturally into daily use.","Texture demonstration may improve qualified curiosity.","Fact-based education may improve product understanding.","Creator-style delivery may improve attention and comprehension."].map((v,i)=><div className="hypothesis-row" key={v}><span className={`concept-number n-${i}`}>0{i+1}</span><div><strong>{["Everyday ritual","Texture study","Ingredient education","Creator walkthrough"][i]}</strong><p>{v}</p></div><Pill>To validate</Pill></div>)}</div></div>
    <div className="notice-box"><ShieldCheck size={17}/><span>Real A/B tests require baseline rates, a defined minimum detectable effect, sample-size and power calculations, platform randomization where available, and a pre-registered stopping rule. Synthetic observations cannot establish statistical market lift.</span></div>
  </div>;
}

function InsightsPage({overview,loading}:{overview:Overview|null;loading:boolean}) {
  const creatives=overview?.creatives||[];
  const bestCtr=[...creatives].sort((a,b)=>(b.metrics.ctr||0)-(a.metrics.ctr||0))[0];
  const bestCvr=[...creatives].sort((a,b)=>(b.metrics.cvr_click_to_purchase||0)-(a.metrics.cvr_click_to_purchase||0))[0];
  const bestRoas=[...creatives].sort((a,b)=>(b.metrics.roas||0)-(a.metrics.roas||0))[0];
  return <div className="page-stack">
    <div className="insight-hero"><div className="insight-orb"><Sparkles size={22}/></div><div><span>ANALYSIS MODE · SIMULATED</span><h2>Signals, not verdicts.</h2><p>These observations summarize the bundled synthetic dataset. They are useful for testing the analysis workflow, not for claiming actual ad performance.</p></div></div>
    <SectionTitle title="Descriptive signals" desc="Top variants by separate metric dimensions. These are not statistically validated winners."/>
    <div className="signal-grid">
      <div className="panel signal-card"><span>HIGHEST SYNTHETIC CTR</span><strong>{loading?"…":bestCtr?.creative_id||"—"}</strong><p>{bestCtr?conceptName[bestCtr.concept]:"Awaiting data"}</p><b>{percent(bestCtr?.metrics.ctr)}</b><small>Attention proxy · not a causal result</small></div>
      <div className="panel signal-card"><span>HIGHEST SYNTHETIC CVR</span><strong>{loading?"…":bestCvr?.creative_id||"—"}</strong><p>{bestCvr?conceptName[bestCvr.concept]:"Awaiting data"}</p><b>{percent(bestCvr?.metrics.cvr_click_to_purchase)}</b><small>Click-to-purchase · attribution assumption</small></div>
      <div className="panel signal-card"><span>HIGHEST SYNTHETIC ROAS</span><strong>{loading?"…":bestRoas?.creative_id||"—"}</strong><p>{bestRoas?conceptName[bestRoas.concept]:"Awaiting data"}</p><b>{bestRoas?.metrics.roas?.toFixed(2)||"—"}x</b><small>Attributed revenue / spend · not ROI</small></div>
    </div>
    <div className="panel"><SectionTitle title="Recommended next checks" desc="Hypotheses to investigate before changing creative or media strategy."/>
      <div className="recommendation-list">
        <div><span className="rec-index">01</span><div><strong>Inspect message-to-landing-page continuity</strong><p>Compare the promise in the first three seconds with the product facts, offer and landing-page content.</p></div><Pill tone="blue">Creative QA</Pill></div>
        <div><span className="rec-index">02</span><div><strong>Separate attention from purchase intent</strong><p>Review CTR and click-to-purchase CVR together; do not select a creative on CTR alone.</p></div><Pill tone="blue">Funnel</Pill></div>
        <div><span className="rec-index">03</span><div><strong>Check sample sufficiency and tracking</strong><p>Validate event definitions, attribution windows, deduplication and power before any winner declaration.</p></div><Pill tone="amber">Measurement</Pill></div>
      </div>
    </div>
  </div>;
}

function AgentsPage() {
  const agents=[
    ["Strategy Agent","Creative angles, hooks and testable hypotheses","SPEC DEFINED","blue"],
    ["Creative Production Agent","Scripts, storyboards, prompts and asset manifests","SPEC DEFINED","blue"],
    ["Compliance Agent","Claims, evidence, rights and policy precheck","HUMAN GATE","amber"],
    ["Asset QA Agent","Technical specs, brand consistency and review","SPEC DEFINED","blue"],
    ["Analytics Agent","Metric snapshots, funnel diagnostics and limitations","API FOUNDATION","green"],
    ["Growth Advisor","Prioritized next creative and media experiments","SPEC DEFINED","blue"]
  ];
  return <div className="page-stack">
    <div className="agent-hero panel"><div className="agent-orb"><Bot size={24}/></div><div><Pill tone="amber">Orchestration not connected yet</Pill><h2>Specialist agents, one auditable workflow.</h2><p>Agent roles and Skills are specified in the repository. The current running slice includes deterministic analytics; LLM execution, tool routing and persistent run logs are future implementation work.</p></div></div>
    <SectionTitle title="Agent registry" desc="Capability specifications and implementation status — not simulated run history."/>
    <div className="agent-grid">{agents.map(([name,desc,status,tone])=><div className="panel agent-card" key={name}><div className="agent-card-icon"><Bot size={18}/></div><div><h3>{name}</h3><p>{desc}</p></div><Pill tone={tone as any}>{status}</Pill></div>)}</div>
    <div className="panel"><SectionTitle title="Workflow governance" desc="The system must keep human decisions and evidence visible."/><div className="governance-grid"><div><ShieldCheck size={18}/><strong>Claim evidence</strong><span>Unverified objective claims cannot pass to test-ready.</span></div><div><FileCheck2 size={18}/><strong>Human approval</strong><span>Creative, compliance and campaign decisions remain reviewable.</span></div><div><Activity size={18}/><strong>Traceability</strong><span>Inputs, versions, tool calls and outputs will be linked to each run.</span></div></div></div>
  </div>;
}

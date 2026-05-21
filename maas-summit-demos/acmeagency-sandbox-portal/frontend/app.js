// AcmeAgency Self-Serve Reporting — no-build React app
// React + Recharts loaded via importmap (see index.html), htm provides JSX-ish tagged templates.
//
// File layout: single ES module. Split into sections:
//   1. API client
//   2. Reusable widgets (Kpi, PacingPill, Skeleton, fmt$)
//   3. Dashboard tab
//   4. CostPanel tab
//   5. BranchesPanel tab + OnboardModal
//   6. App shell + boot

import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import htm from "https://esm.sh/htm@3";
import {
  Bar, BarChart, CartesianGrid, Legend, Line, LineChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";

const html = htm.bind(React.createElement);

// ---------- 1. API client --------------------------------------------------

let _override = null;
const setOverride = (id) => { _override = id; };

async function req(path, init) {
  const headers = { "Content-Type": "application/json", ...(init && init.headers) };
  if (_override) headers["X-Advertiser-Override"] = _override;
  const r = await fetch(path, { ...init, headers });
  if (!r.ok) throw new Error(`${r.status}: ${(await r.text()).slice(0, 200)}`);
  return r.json();
}

const api = {
  me:               () => req("/api/me"),
  advertisers:      () => req("/api/advertisers"),
  perfByCampaign:   () => req("/api/perf/by-campaign"),
  perfDaily:        () => req("/api/perf/daily"),
  perfByChannel:    () => req("/api/perf/by-channel"),
  audiences:        () => req("/api/audiences"),
  pacing:           () => req("/api/pacing"),
  pacingSummary:    () => req("/api/pacing/summary"),
  branches:         () => req("/api/branches"),
  createBranch:     (name, advertiser_id, purpose = "sandbox") =>
                     req("/api/branches", { method: "POST", body: JSON.stringify({ name, advertiser_id, purpose }) }),
  deleteBranch:     (name) => req(`/api/branches/${name}`, { method: "DELETE" }),
  costSummary:      () => req("/api/cost/summary"),
};

// ---------- 2. Widgets -----------------------------------------------------

const fmt$ = (v) => {
  if (v == null || isNaN(v)) return "—";
  if (v >= 1_000_000) return `$${(v / 1_000_000).toFixed(2)}M`;
  if (v >= 1_000)     return `$${(v / 1_000).toFixed(1)}k`;
  return `$${Math.round(v)}`;
};

const Kpi = ({ label, value, sub, highlight }) => html`
  <div className=${"kpi" + (highlight ? " highlight" : "")}>
    <div className="kpi-label">${label}</div>
    <div className="kpi-value">${value}</div>
    ${sub && html`<div className="kpi-sub">${sub}</div>`}
  </div>
`;

const PacingPill = ({ health }) => {
  const klass = health === "on_pace" ? "good" : health === "underpacing" ? "warn" : "bad";
  return html`<span className=${`pill ${klass}`}>${health.replace("_", " ")}</span>`;
};

const TierPill = ({ tier }) => {
  const klass = tier === "enterprise" ? "neutral" : tier === "growth" ? "warn" : "good";
  return html`<span className=${`pill ${klass}`}>${tier}</span>`;
};

const Skeleton = ({ height = 200 }) => html`<div className="skeleton" style=${{ height }} />`;

const tooltipStyle = { background: "#121833", border: "1px solid #2a3463", borderRadius: 6, fontSize: 12 };

// ---------- 3. Dashboard ---------------------------------------------------

function Dashboard({ advertiser }) {
  const [campaigns, setCampaigns] = useState([]);
  const [daily, setDaily] = useState([]);
  const [channels, setChannels] = useState([]);
  const [pacing, setPacing] = useState([]);
  const [pacingSummary, setPacingSummary] = useState(null);
  const [audiences, setAudiences] = useState([]);
  const [loading, setLoading] = useState(true);
  const [queryMs, setQueryMs] = useState(null);

  useEffect(() => {
    setLoading(true);
    const t0 = performance.now();
    Promise.all([
      api.perfByCampaign(), api.perfDaily(), api.perfByChannel(),
      api.pacing(), api.pacingSummary(), api.audiences(),
    ]).then(([c, d, ch, p, ps, au]) => {
      setCampaigns(c); setDaily(d); setChannels(ch);
      setPacing(p); setPacingSummary(ps); setAudiences(au);
      setQueryMs(Math.round(performance.now() - t0));
      setLoading(false);
    }).catch(e => { console.error(e); setLoading(false); });
  }, [advertiser ? advertiser.advertiser_id : null]);

  if (loading) return html`<div className="panel"><${Skeleton} height=${400} /></div>`;

  const totalSpend   = campaigns.reduce((s, c) => s + c.spend, 0);
  const totalRevenue = campaigns.reduce((s, c) => s + c.revenue, 0);
  const totalConv    = campaigns.reduce((s, c) => s + c.conversions, 0);
  const blendedRoas  = totalSpend ? totalRevenue / totalSpend : 0;
  const brand = (advertiser && advertiser.brand_color) || "#60a5fa";

  return html`
    <div>
      <div className="kpi-row">
        <${Kpi} label="12-week spend"   value=${fmt$(totalSpend)}   sub=${`${campaigns.length} campaigns`} />
        <${Kpi} label="12-week revenue" value=${fmt$(totalRevenue)} sub=${`${totalConv.toLocaleString()} conversions`} />
        <${Kpi} label="Blended ROAS"    value=${`${blendedRoas.toFixed(2)}x`} sub=${blendedRoas >= 1 ? "above breakeven" : "below breakeven"} />
        <${Kpi} label="Lakebase query"  value=${queryMs ? `${queryMs} ms` : "—"} sub="6 parallel reads" />
      </div>

      <div className="panels">
        <div className="panel">
          <h3>Spend & Revenue (daily)</h3>
          <${ResponsiveContainer} width="100%" height=${260}>
            <${LineChart} data=${daily}>
              <${CartesianGrid} stroke="#2a3463" strokeDasharray="3 3" vertical=${false} />
              <${XAxis} dataKey="date" stroke="#8da0d0" tick=${{ fontSize: 11 }} tickFormatter=${d => (d || "").slice(5, 10)} interval=${6} />
              <${YAxis} stroke="#8da0d0" tick=${{ fontSize: 11 }} tickFormatter=${fmt$} />
              <${Tooltip} contentStyle=${tooltipStyle} formatter=${v => fmt$(v)} />
              <${Line} type="monotone" dataKey="spend"   stroke="#60a5fa" dot=${false} strokeWidth=${2} />
              <${Line} type="monotone" dataKey="revenue" stroke="#34d399" dot=${false} strokeWidth=${2} />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div className="panel">
          <h3>Channel mix</h3>
          <${ResponsiveContainer} width="100%" height=${260}>
            <${BarChart} data=${channels} layout="vertical" margin=${{ left: 24 }}>
              <${CartesianGrid} stroke="#2a3463" strokeDasharray="3 3" horizontal=${false} />
              <${XAxis} type="number" stroke="#8da0d0" tick=${{ fontSize: 11 }} tickFormatter=${fmt$} />
              <${YAxis} dataKey="channel" type="category" stroke="#8da0d0" width=${90} tick=${{ fontSize: 12 }} />
              <${Tooltip} contentStyle=${tooltipStyle} formatter=${v => fmt$(v)} />
              <${Bar} dataKey="spend" fill=${brand} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="panel" style=${{ marginBottom: 16 }}>
        <h3>Campaigns — spend, ROAS, CPA</h3>
        <table>
          <thead>
            <tr>
              <th>Campaign</th><th>Channel</th>
              <th className="num">Spend</th><th className="num">Revenue</th>
              <th className="num">Conv</th><th className="num">ROAS</th><th className="num">CPA</th>
            </tr>
          </thead>
          <tbody>
            ${campaigns.map(c => html`
              <tr key=${c.campaign_id}>
                <td>${c.name}</td>
                <td><span className="pill neutral">${c.channel}</span></td>
                <td className="num">${fmt$(c.spend)}</td>
                <td className="num">${fmt$(c.revenue)}</td>
                <td className="num">${c.conversions.toLocaleString()}</td>
                <td className="num">
                  <span className=${`pill ${c.roas >= 1.5 ? "good" : c.roas >= 1 ? "neutral" : "bad"}`}>${c.roas.toFixed(2)}x</span>
                </td>
                <td className="num">${c.cpa ? fmt$(c.cpa) : "—"}</td>
              </tr>
            `)}
          </tbody>
        </table>
      </div>

      <div className="panels">
        <div className="panel">
          <h3>
            Pacing this month
            ${pacingSummary && html`<span style=${{ color: "var(--text-dim)", fontSize: 12, fontWeight: "normal", marginLeft: 8 }}>
              ${pacingSummary.on_pace} on pace · ${pacingSummary.underpacing} under · ${pacingSummary.overpacing} over
            </span>`}
          </h3>
          <table>
            <thead><tr>
              <th>Campaign</th><th>Channel</th>
              <th className="num">Budget</th><th className="num">FTD</th><th className="num">% spent</th>
              <th>Health</th>
            </tr></thead>
            <tbody>
              ${pacing.map(p => html`
                <tr key=${p.campaign_id}>
                  <td>${p.campaign_name}</td>
                  <td><span className="pill neutral">${p.channel}</span></td>
                  <td className="num">${fmt$(p.monthly_budget)}</td>
                  <td className="num">${fmt$(p.ftd_spend)}</td>
                  <td className="num">${(p.actual_pace * 100).toFixed(0)}%</td>
                  <td><${PacingPill} health=${p.health} /></td>
                </tr>
              `)}
            </tbody>
          </table>
        </div>
        <div className="panel">
          <h3>Audience segments</h3>
          <table>
            <thead><tr>
              <th>Segment</th><th className="num">Size</th><th className="num">Overlap</th>
            </tr></thead>
            <tbody>
              ${audiences.map(a => html`
                <tr key=${a.segment_id}>
                  <td>${a.name}</td>
                  <td className="num">${a.size.toLocaleString()}</td>
                  <td className="num">${(a.overlap_score * 100).toFixed(0)}%</td>
                </tr>
              `)}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  `;
}

// ---------- 4. Cost panel --------------------------------------------------

function CostPanel() {
  const [data, setData] = useState(null);
  useEffect(() => { api.costSummary().then(setData); }, []);
  if (!data) return html`<div className="panel"><${Skeleton} height=${400} /></div>`;

  const chartData = data.per_tenant.map(t => ({
    name: t.name, saved: t.saved_usd, actual: t.actual_usd, tier: t.tier,
  }));

  return html`
    <div>
      <div className="kpi-row">
        <${Kpi} label="Saved this month"   value=${`$${data.saved_usd.toLocaleString()}`} sub=${`${data.savings_pct}% vs always-on`} highlight=${true} />
        <${Kpi} label="Always-on baseline" value=${`$${data.always_on_usd.toLocaleString()}`} sub=${`${data.tenant_count} tenants × 720 hrs`} />
        <${Kpi} label="With scale-to-zero" value=${`$${data.actual_usd.toLocaleString()}`} sub=${`@ $${data.rate_per_hour_usd}/hr · CU_1`} />
        <${Kpi} label="Live branches"      value=${`${data.live_branch_count}`} sub=${`$${data.live_branch_cost_usd_per_hour}/hr extra`} />
      </div>

      <div className="panel" style=${{ marginBottom: 16 }}>
        <h3>Monthly cost — actual vs always-on baseline</h3>
        <${ResponsiveContainer} width="100%" height=${280}>
          <${BarChart} data=${chartData}>
            <${CartesianGrid} stroke="#2a3463" strokeDasharray="3 3" vertical=${false} />
            <${XAxis} dataKey="name" stroke="#8da0d0" tick=${{ fontSize: 11 }} />
            <${YAxis} stroke="#8da0d0" tick=${{ fontSize: 11 }} tickFormatter=${v => `$${v}`} />
            <${Tooltip} contentStyle=${tooltipStyle} formatter=${v => `$${v.toLocaleString()}`} />
            <${Legend} wrapperStyle=${{ fontSize: 12 }} />
            <${Bar} dataKey="actual" stackId="a" fill="#60a5fa" name="actual (scale-to-zero)" />
            <${Bar} dataKey="saved"  stackId="a" fill="#34d399" name="saved (idle hours)" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="panel">
        <h3>By tenant</h3>
        <table>
          <thead><tr>
            <th>Advertiser</th><th>Tier</th>
            <th className="num">Active hrs</th><th className="num">Idle hrs saved</th>
            <th className="num">Always-on $</th><th className="num">Actual $</th><th className="num">Saved $</th>
          </tr></thead>
          <tbody>
            ${data.per_tenant.map(t => html`
              <tr key=${t.advertiser_id}>
                <td>${t.name}</td>
                <td><${TierPill} tier=${t.tier} /></td>
                <td className="num">${t.active_hours_this_month}</td>
                <td className="num">${t.idle_hours_saved.toFixed(0)}</td>
                <td className="num">$${t.always_on_usd.toLocaleString()}</td>
                <td className="num">$${t.actual_usd.toLocaleString()}</td>
                <td className="num" style=${{ color: t.saved_usd > 0 ? "var(--good)" : "var(--text-dim)" }}>
                  $${t.saved_usd.toLocaleString()}
                </td>
              </tr>
            `)}
          </tbody>
        </table>
        <p style=${{ fontSize: 11, color: "var(--text-dim)", marginTop: 12 }}>
          Per-tier behavior: enterprise = always-on, growth = business-hours warm, starter = scale-to-zero on logout.
          Real Lakebase billing reads from <code>system.billing.usage</code>.
        </p>
      </div>
    </div>
  `;
}

// ---------- 5. Branches panel + Onboard modal -----------------------------

function BranchesPanel({ advertisers, onAdvertisersChanged }) {
  const [branches, setBranches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showOnboard, setShowOnboard] = useState(false);
  const [busy, setBusy] = useState(null);
  const [error, setError] = useState(null);

  const refresh = async () => {
    setLoading(true);
    try { setBranches(await api.branches()); }
    catch (e) { setError(String(e.message || e)); }
    setLoading(false);
  };
  useEffect(() => { refresh(); }, []);

  const sandbox = async (advertiserId) => {
    setBusy(advertiserId); setError(null);
    try {
      const name = `maas-team8-${advertiserId.replace("adv_", "")}-sandbox-${Math.floor(Date.now() / 1000) % 100000}`;
      await api.createBranch(name, advertiserId, "sandbox");
      await refresh();
    } catch (e) { setError(String(e.message || e)); }
    finally { setBusy(null); }
  };

  const removeBranch = async (name) => {
    if (!confirm(`Delete branch ${name}?`)) return;
    setBusy(name); setError(null);
    try { await api.deleteBranch(name); await refresh(); }
    catch (e) { setError(String(e.message || e)); }
    finally { setBusy(null); }
  };

  return html`
    <div>
      ${error && html`<div className="error">⚠ ${error}</div>`}

      <div className="panel" style=${{ marginBottom: 16 }}>
        <div className="panel-head">
          <h3 style=${{ margin: 0 }}>Active tenants</h3>
          <button onClick=${() => setShowOnboard(true)}>+ Onboard new advertiser</button>
        </div>
        <table>
          <thead><tr>
            <th>Advertiser</th><th>Tier</th><th className="num">Monthly budget</th>
            <th>Brand</th><th>Sandbox</th>
          </tr></thead>
          <tbody>
            ${advertisers.map(a => html`
              <tr key=${a.advertiser_id}>
                <td>${a.name}</td>
                <td><${TierPill} tier=${a.tier} /></td>
                <td className="num">$${a.monthly_budget_usd.toLocaleString()}</td>
                <td><span className="brand-dot" style=${{ background: a.brand_color, width: 14, height: 14, borderRadius: 3 }} /></td>
                <td>
                  <button className="secondary" disabled=${busy === a.advertiser_id} onClick=${() => sandbox(a.advertiser_id)}>
                    ${busy === a.advertiser_id
                      ? html`<span className="spinner" />creating...`
                      : "Sandbox this advertiser"}
                  </button>
                </td>
              </tr>
            `)}
          </tbody>
        </table>
      </div>

      <div className="panel">
        <h3>Lakebase branches off <code>maas-team8</code></h3>
        ${loading ? html`<${Skeleton} height=${80} />`
          : branches.length === 0 ? html`
            <p style=${{ color: "var(--text-dim)", fontSize: 13 }}>
              No active branches. Click "Sandbox this advertiser" above or onboard a new advertiser to spawn one.
            </p>
          ` : html`
            <table>
              <thead><tr>
                <th>Branch name</th><th>State</th><th>Capacity</th>
                <th>Branched at</th><th>Created</th><th></th>
              </tr></thead>
              <tbody>
                ${branches.map(b => html`
                  <tr key=${b.name}>
                    <td><code>${b.name}</code></td>
                    <td><span className=${`pill ${b.state === "AVAILABLE" ? "good" : "warn"}`}>${b.state}</span></td>
                    <td>${b.capacity}</td>
                    <td>${(b.branch_time || "").slice(0, 19).replace("T", " ")}</td>
                    <td>${(b.created || "").slice(0, 19).replace("T", " ")}</td>
                    <td><button className="danger" disabled=${busy === b.name} onClick=${() => removeBranch(b.name)}>delete</button></td>
                  </tr>
                `)}
              </tbody>
            </table>
          `}
        <p style=${{ fontSize: 11, color: "var(--text-dim)", marginTop: 12 }}>
          Branches are copy-on-write forks. Spawn one for tenant onboarding, sandbox a what-if change against it, then drop it.
        </p>
      </div>

      ${showOnboard && html`
        <${OnboardModal}
          onClose=${() => setShowOnboard(false)}
          onCreated=${async () => { setShowOnboard(false); await refresh(); await onAdvertisersChanged(); }}
        />
      `}
    </div>
  `;
}

function OnboardModal({ onClose, onCreated }) {
  const [name, setName] = useState("");
  const [tier, setTier] = useState("growth");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState(null);
  const [step, setStep] = useState("");

  const submit = async () => {
    setCreating(true); setError(null);
    try {
      const advId = "adv_" + name.toLowerCase().replace(/[^a-z0-9]/g, "");
      const branchName = `maas-team8-${advId.replace("adv_", "")}-onboard`;
      setStep(`Spawning Lakebase branch "${branchName}" off maas-team8...`);
      await api.createBranch(branchName, advId, "onboarding");
      setStep("Branch created. New advertiser is queryable.");
      await new Promise(r => setTimeout(r, 600));
      await onCreated();
    } catch (e) {
      setError(String(e.message || e));
      setCreating(false);
    }
  };

  return html`
    <div className="modal-backdrop" onClick=${creating ? undefined : onClose}>
      <div className="modal" onClick=${e => e.stopPropagation()}>
        <h3>Onboard new advertiser</h3>
        <p style=${{ color: "var(--text-dim)", fontSize: 13, marginTop: -8 }}>
          Spawns a Lakebase branch off the parent instance — the new tenant gets their own isolated workspace
          for setup, production data untouched.
        </p>
        ${error && html`<div className="error">⚠ ${error}</div>`}
        <div className="row">
          <label>Advertiser name</label>
          <input value=${name} onChange=${e => setName(e.target.value)} placeholder="e.g. Faherty" disabled=${creating} />
        </div>
        <div className="row">
          <label>Tier</label>
          <select value=${tier} onChange=${e => setTier(e.target.value)} disabled=${creating}>
            <option value="enterprise">enterprise (always-on)</option>
            <option value="growth">growth (business-hours)</option>
            <option value="starter">starter (scale-to-zero)</option>
          </select>
        </div>
        ${creating && step && html`<div className="progress-box"><span className="spinner" />${step}</div>`}
        <div className="actions">
          <button className="secondary" onClick=${onClose} disabled=${creating}>cancel</button>
          <button onClick=${submit} disabled=${!name || creating}>
            ${creating ? "spawning branch..." : "Onboard + spawn branch"}
          </button>
        </div>
      </div>
    </div>
  `;
}

// ---------- 6. App shell ---------------------------------------------------

function App() {
  const [me, setMe] = useState(null);
  const [advertisers, setAdvertisers] = useState([]);
  const [currentAdv, setCurrentAdv] = useState(null);
  const [tab, setTab] = useState("dashboard");
  const [error, setError] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const m = await api.me();
        setMe(m);
        const as = await api.advertisers();
        setAdvertisers(as);
        setCurrentAdv(m.advertiser_id);
      } catch (e) { setError(String(e.message || e)); }
    })();
  }, []);

  const advertiser = advertisers.find(a => a.advertiser_id === currentAdv);

  const switchTo = (id) => {
    setOverride(me && me.is_agency_admin && id !== me.advertiser_id ? id : null);
    setCurrentAdv(id);
  };

  const reloadAdvertisers = async () => setAdvertisers(await api.advertisers());

  return html`
    <div className="app">
      <aside className="sidebar">
        <div>
          <h1>AcmeAgency</h1>
          <div className="tagline">Self-serve reporting</div>
          <nav>
            <a className=${tab === "dashboard" ? "active" : ""} onClick=${() => setTab("dashboard")}>Dashboard</a>
            ${me && me.is_agency_admin && html`
              <a className=${tab === "cost" ? "active" : ""}     onClick=${() => setTab("cost")}>Lakebase Cost</a>
              <a className=${tab === "branches" ? "active" : ""} onClick=${() => setTab("branches")}>Tenants & Branches</a>
            `}
          </nav>
        </div>
        <div className="user">
          ${me ? html`
            ${me.email}
            <br />
            <span style=${{ color: me.is_agency_admin ? "var(--accent-warm)" : "var(--text-dim)" }}>
              ${me.is_agency_admin ? "Agency admin" : "Advertiser viewer"}
            </span>
          ` : "loading..."}
        </div>
      </aside>

      <main className="main">
        ${error && html`<div className="error">⚠ ${error}</div>`}

        <div className="topbar">
          <h2>
            <span className="brand-dot" style=${{ background: (advertiser && advertiser.brand_color) || "#60a5fa" }}></span>
            ${(advertiser && advertiser.name) || "(no advertiser)"}
          </h2>
          ${me && me.is_agency_admin && advertisers.length > 0 && html`
            <div>
              <span style=${{ color: "var(--text-dim)", fontSize: 12, marginRight: 8 }}>VIEW AS:</span>
              <select value=${currentAdv || ""} onChange=${e => switchTo(e.target.value)}>
                ${advertisers.map(a => html`<option key=${a.advertiser_id} value=${a.advertiser_id}>${a.name} · ${a.tier}</option>`)}
              </select>
            </div>
          `}
        </div>

        ${tab === "dashboard" && currentAdv && html`<${Dashboard} key=${currentAdv} advertiser=${advertiser} />`}
        ${tab === "cost" && html`<${CostPanel} />`}
        ${tab === "branches" && html`<${BranchesPanel} advertisers=${advertisers} onAdvertisersChanged=${reloadAdvertisers} />`}
      </main>
    </div>
  `;
}

createRoot(document.getElementById("root")).render(html`<${App} />`);

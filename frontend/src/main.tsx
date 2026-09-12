import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, NavLink, Route, Routes, useNavigate } from 'react-router-dom';
import './styles.css';
import AIResponseRenderer from './components/AIResponseRenderer';

const API = import.meta.env.VITE_GATEWAY_URL || 'http://localhost:3000';
type User = { username: string; role: string; subsidiary: string | null };
type Session = { token: string; user: User };
const Auth = createContext<{ session: Session | null; login: (s: Session) => void; logout: () => void }>({ session: null, login: () => {}, logout: () => {} });

function request(path: string, token?: string, options: RequestInit = {}) {
  return fetch(`${API}${path}`, {
    ...options,
    headers: {
      ...(options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
  }).then(async r => {
    const d = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(d.message || d.detail || 'Request failed.');
    return d;
  });
}

/* ─── Sidebar (hoisted outside Layout to avoid recreation on every render) ─── */
function Sidebar({ session, logout, onClose }: { session: Session | null; logout: () => void; onClose?: () => void }) {
  const navCls = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-[10px] text-[#dce1da] no-underline rounded-[5px] px-[12px] py-[10px] text-[13px] font-[500] transition-colors duration-150 hover:bg-[#40554a] hover:text-white${isActive ? ' bg-[#40554a] text-white' : ''}`;

  return (
    <aside className="h-dvh w-full flex flex-col bg-[#26332e] text-[#ecede7] overflow-hidden select-none">
      {/* Header */}
      <div className="flex-shrink-0 flex items-start justify-between px-[18px] pt-[24px] pb-[8px]">
        <div className="leading-tight">
          <div className="text-[21px] font-[800] tracking-[.5px]">
            KOHA<span className="text-[#cab77f]">-CIL</span>
          </div>
          <small className="block text-[11px] font-[500] tracking-[.8px] text-[#a8b5a5] mt-[3px]">
            Enterprise Intelligence
          </small>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="flex-shrink-0 ml-[8px] w-[32px] h-[32px] flex items-center justify-center bg-transparent border-0 text-[#a8b5a5] text-[18px] cursor-pointer rounded-[4px] hover:bg-[#40554a] hover:text-white transition-colors duration-150"
            aria-label="Close menu"
          >
            ✕
          </button>
        )}
      </div>

      {/* Divider */}
      <div className="mx-[18px] my-[12px] border-t border-[#3a4a43]" />

      {/* Scrollable nav */}
      <nav className="flex-1 min-h-0 overflow-y-auto px-[10px] flex flex-col gap-[2px]">
        <NavLink className={navCls} to="/" onClick={onClose} end>Dashboard</NavLink>
        <NavLink className={navCls} to="/query" onClick={onClose}>Query Console</NavLink>
        {session?.user.role !== 'SUBSIDIARY_OFFICER' && (
          <NavLink className={navCls} to="/ingestion" onClick={onClose}>Ingestion</NavLink>
        )}
        <NavLink className={navCls} to="/conflicts" onClick={onClose}>Conflicts</NavLink>
        <NavLink className={navCls} to="/audit" onClick={onClose}>Audit Log</NavLink>
      </nav>

      {/* Pinned footer */}
      <div className="flex-shrink-0 border-t border-[#3a4a43] px-[18px] py-[16px]">
        <div className="text-[13px] font-[600] text-[#ecede7] truncate">{session?.user.username}</div>
        <div className="text-[11px] text-[#a8b5a5] mt-[2px] truncate">
          {session?.user.role.replace('_', ' ')} · {session?.user.subsidiary || 'GLOBAL'}
        </div>
        <button
          className="mt-[10px] py-[6px] px-0 bg-transparent border-0 text-[#c8d0c7] underline cursor-pointer text-[12px] hover:text-white transition-colors duration-150"
          onClick={logout}
        >
          Sign out
        </button>
      </div>
    </aside>
  );
}

/* ─── Layout ─── */
function Layout() {
  const { session, logout } = useContext(Auth);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const drawerRef = useRef<HTMLDivElement>(null);

  const openDrawer = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    setDrawerOpen(true);
  }, []);
  const closeDrawer = useCallback(() => setDrawerOpen(false), []);

  // Lock body scroll while drawer is open
  useEffect(() => {
    if (drawerOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => { document.body.style.overflow = ''; };
  }, [drawerOpen]);

  return (
    <div className="flex h-dvh flex-col overflow-hidden">
      <div className="flex h-[26px] flex-shrink-0 items-center border-b border-[#d5d8d2] bg-[#eef0eb] px-[16px] text-[10px] font-[600] tracking-[.15px] text-[#4f5d54] min-[651px]:px-[28px] min-[651px]:text-[11px]">
        Official IT Portal of Ministry of Coal, Government of India
      </div>

      <div className="flex min-h-0 flex-1 overflow-hidden">
        {/* Desktop / tablet sidebar */}
        <div className="hidden min-[651px]:flex flex-col flex-shrink-0 w-[190px] min-[901px]:w-[245px]">
          <Sidebar session={session} logout={logout} />
        </div>

        {/* Mobile drawer overlay */}
        {drawerOpen && (
          <div
            className="fixed inset-0 z-50 min-[651px]:hidden"
            role="dialog"
            aria-modal="true"
            aria-label="Navigation menu"
          >
            <div
              className="absolute inset-0 bg-black/60 backdrop-blur-[1px] transition-opacity duration-200"
              onClick={closeDrawer}
            />
            <div
              ref={drawerRef}
              className="absolute left-0 top-0 bottom-0 w-[272px] max-w-[88vw] shadow-2xl"
              onClick={e => e.stopPropagation()}
            >
              <Sidebar session={session} logout={logout} onClose={closeDrawer} />
            </div>
          </div>
        )}

        {/* Main content area */}
        <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
          <header className="flex-shrink-0 h-[64px] min-[651px]:h-[72px] bg-white border-b border-[#dddcd6] px-[12px] min-[651px]:px-[28px] flex items-center justify-between gap-[10px]">
            <div className="flex items-center gap-[8px] min-w-0 flex-shrink-0">
              <button
                className="min-[651px]:hidden flex flex-col justify-center items-center gap-[5px] w-[36px] h-[36px] bg-transparent border border-[#dddcd6] rounded-[6px] cursor-pointer text-[#58615b] hover:bg-[#f4f2ed] transition-colors duration-150 flex-shrink-0"
                onClick={openDrawer}
                aria-label="Open navigation menu"
                aria-expanded={drawerOpen}
              >
                <span className="block w-[16px] h-[1.5px] bg-current rounded-full" />
                <span className="block w-[16px] h-[1.5px] bg-current rounded-full" />
                <span className="block w-[16px] h-[1.5px] bg-current rounded-full" />
              </button>
              <img src="/branding/ashoka-emblem.png" alt="Satyameva Jayate — Government of India" className="h-[42px] w-[34px] object-contain min-[651px]:h-[54px] min-[651px]:w-[44px]" />
            </div>

            <div className="min-w-0 flex-1 text-center">
              <p className="m-0 truncate text-[12px] font-[700] tracking-[.25px] text-[#293d34] min-[651px]:text-[14px]">KOHA-CIL / Operations</p>
              <p className="m-0 mt-[2px] hidden text-[10px] tracking-[.45px] text-[#697069] min-[901px]:block">Enterprise Intelligence &amp; Reporting Platform</p>
            </div>

            <div className="flex items-center justify-end gap-[10px] flex-shrink-0">
              <span className="hidden min-[901px]:flex text-[12px] font-[600] text-[#317148] items-center gap-[5px] whitespace-nowrap">
                <span className="text-[8px]">●</span> Secure session
              </span>
              <img src="/branding/coal-india-logo.png" alt="Coal India Limited" className="h-[44px] w-[34px] object-contain min-[651px]:h-[54px] min-[651px]:w-[42px]" />
            </div>
          </header>

          <main className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden bg-[#f4f2ed]">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/query" element={<Query />} />
              <Route path="/ingestion" element={<Ingestion />} />
              <Route path="/conflicts" element={<Conflicts />} />
              <Route path="/audit" element={<Audit />} />
            </Routes>
          </main>
        </div>
      </div>
    </div>
  );
}

/* ─── Auth hook ─── */
function useApi() {
  const { session, logout } = useContext(Auth);
  return (path: string, options?: RequestInit) =>
    request(path, session?.token, options).catch(e => {
      if (String(e.message).includes('session')) logout();
      throw e;
    });
}

/* ─── Login ─── */
function Login() {
  const { login } = useContext(Auth);
  const nav = useNavigate();
  const [username, setUsername] = useState('hq.admin');
  const [password, setPassword] = useState('demo123');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      const d = await request('/api/auth/login', undefined, { method: 'POST', body: JSON.stringify({ username, password }) });
      login({ token: d.token, user: d.user });
      nav('/');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Login failed.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="min-h-screen grid min-[901px]:grid-cols-[1fr_420px] gap-[40px] min-[901px]:gap-[80px] items-center px-[24px] py-[48px] min-[901px]:px-[10vw] min-[901px]:py-[9vw] bg-[linear-gradient(135deg,#e8e5dd,#f8f7f3)]">
      <section className="max-w-[520px]">
        <div className="flex items-center gap-[16px] mb-[20px]">
          <img src="/branding/ashoka-emblem.png" alt="Government of India" className="h-[54px] w-auto object-contain" />
          <div className="h-[36px] w-[1px] bg-[#3d5245]/20" />
          <img src="/branding/coal-india-logo.png" alt="Coal India Limited" className="h-[54px] w-auto object-contain" />
        </div>

        <p className="text-[11px] font-[700] tracking-[1.5px] text-[#617069] uppercase mb-[8px]">Ministry / PSU Information System</p>
        <h1 className="text-[36px] min-[901px]:text-[48px] font-[800] my-[8px] text-[#293d34] leading-[1.1]">KOHA-CIL</h1>
        <p className="text-[20px] text-[#3d5245] font-[500] mt-0 mb-[16px]">Enterprise Intelligence &amp; Reporting Platform</p>
        <p className="text-[#5d665e] leading-[1.65] text-[15px]">Evidence-led operational intelligence for Coal India Limited and its subsidiaries.</p>
      </section>

      <form onSubmit={submit} className="bg-white border border-[#deddd7] rounded-[10px] p-[28px] shadow-[0_2px_8px_rgba(0,0,0,0.08)] m-0 w-full">
        <h2 className="text-[20px] font-[700] mb-[4px] mt-0 text-[#27312b]">Sign in</h2>
        <p className="text-[#697069] text-[13px] mb-[20px]">Use a synthetic demo account for this development environment.</p>

        <div className="flex flex-col gap-[16px]">
          <label className="block">
            <span className="block text-[13px] font-[650] text-[#3a4541] mb-[6px]">Username</span>
            <input
              className="font-[inherit] border border-[#b9b8b1] rounded-[6px] py-[9px] px-[12px] w-full bg-white text-[14px] focus:outline-none focus:border-[#2d4a3e] focus:ring-[2px] focus:ring-[#2d4a3e]/20 transition-colors"
              value={username}
              onChange={e => setUsername(e.target.value)}
              autoComplete="username"
            />
          </label>
          <label className="block">
            <span className="block text-[13px] font-[650] text-[#3a4541] mb-[6px]">Password</span>
            <input
              className="font-[inherit] border border-[#b9b8b1] rounded-[6px] py-[9px] px-[12px] w-full bg-white text-[14px] focus:outline-none focus:border-[#2d4a3e] focus:ring-[2px] focus:ring-[#2d4a3e]/20 transition-colors"
              value={password}
              onChange={e => setPassword(e.target.value)}
              type="password"
              autoComplete="current-password"
            />
          </label>
        </div>

        {error && <p className="text-[#9f362b] text-[13px] mt-[12px] mb-0">{error}</p>}

        <button
          className="mt-[20px] w-full bg-[#2d4a3e] text-white rounded-[6px] py-[11px] px-[16px] text-[14px] font-[650] cursor-pointer border-0 disabled:opacity-60 disabled:cursor-wait hover:bg-[#3a5a4e] transition-colors duration-150"
          disabled={busy}
        >
          {busy ? 'Signing in…' : 'Sign in'}
        </button>
        <p className="text-[11px] text-[#8a9189] mt-[16px] leading-[1.6] text-center">
          hq.admin · ccl.officer · secl.officer · ecl.officer · mcl.officer — password: demo123
        </p>
      </form>
    </main>
  );
}

/* ─── Dashboard ─── */
function Dashboard() {
  const api = useApi();
  const [d, setD] = useState<any>();
  const [err, setErr] = useState('');

  useEffect(() => {
    api('/api/dashboard/stats').then(setD).catch(e => setErr(e.message));
  }, []);

  if (err) return <Message title="Dashboard unavailable" text={err} />;
  if (!d) return <Loading />;

  const rows = d.latest_year_production || [];
  const production = rows.reduce((n: number, r: any) => n + Number(r.production_mt || 0), 0);
  const target = rows.reduce((n: number, r: any) => n + Number(r.target_mt || 0), 0);

  const wordCloudTopics = [
    { text: 'Production (MT)', className: 'text-[24px] text-[#2d4a3e]' },
    { text: 'Overburden Removal (OBR)', className: 'text-[18px] text-[#40554a]' },
    { text: 'SECL Opencast', className: 'text-[22px] text-[#2d4a3e]' },
    { text: 'Safety & DGMS', className: 'text-[20px] text-[#825b10]' },
    { text: 'CCL Underground', className: 'text-[16px] text-[#58615b]' },
    { text: 'Mined Reclamation', className: 'text-[15px] text-[#317148]' },
    { text: 'Jharia Coking Coal', className: 'text-[19px] text-[#26332e]' },
    { text: 'Quarantine Conflicts', className: 'text-[17px] text-[#9f362b]' },
    { text: 'Vision 2030', className: 'text-[21px] text-[#2d4a3e]' },
    { text: 'Dispatch (Rakes)', className: 'text-[14px] text-[#697069]' },
  ];

  return (
    <Page title="Operational dashboard" caption="Latest available reporting period. Records marked as demo data are synthetic.">
      {/* Metrics grid */}
      <div className="grid grid-cols-2 min-[901px]:grid-cols-4 gap-[14px] mb-[20px]">
        <Metric name="Production (MT)" value={`${production.toFixed(2)} MT`} />
        <Metric name="Target" value={`${target.toFixed(2)} MT`} />
        <Metric name="Active conflicts" value={d.active_conflicts} />
        <Metric name="Queries, last 7 days" value={d.recent_queries} />
      </div>

      {/* Subsidiary table */}
      <Card title="Subsidiary overview">
        <Table
          columns={['Subsidiary', 'Financial year', 'Production (MT)', 'Target (MT)', 'Achievement']}
          rows={rows.map((r: any) => [r.subsidiary, r.financial_year, r.production_mt, r.target_mt, `${r.achievement_percentage}%`])}
        />
      </Card>

      {/* Word cloud */}
      <Card title="Trending Mining & Policy Topics">
        <p className="text-[#697069] text-[13px] mb-[14px] mt-[-4px]">Semantic term density extracted across CIL subsidiaries and CMPDI geological reports.</p>
        <div className="flex flex-wrap items-center justify-center gap-[14px] rounded-[6px] border border-dashed border-[#cfceca] bg-[#f9f8f5] p-[18px]">
          {wordCloudTopics.map((item, idx) => (
            <span key={idx} className={`${item.className} cursor-pointer px-[6px] py-[2px] font-bold transition-transform duration-200 ease-in hover:scale-110 hover:underline`}>
              {item.text}
            </span>
          ))}
        </div>
      </Card>

      {/* Status row */}
      <div className="grid grid-cols-1 min-[651px]:grid-cols-2 gap-[14px]">
        <Card title="System status">
          <div className="flex flex-col gap-[8px] text-[14px]">
            <div className="flex justify-between"><span className="text-[#697069]">Database</span><b className="text-[#27312b]">{d.system_health.database}</b></div>
            <div className="flex justify-between"><span className="text-[#697069]">Local AI</span><b className="text-[#27312b]">{d.system_health.ollama}</b></div>
          </div>
        </Card>
        <Card title="Ingestion activity">
          <p className="text-[14px] mb-[6px]"><b className="text-[#26332e]">{d.recent_ingestions}</b> recent submissions</p>
          <p className="text-[#697069] text-[13px] m-0">Document processing and conflict checks are recorded in the audit trail.</p>
        </Card>
      </div>
    </Page>
  );
}

/* ─── Query ─── */
function Query() {
  const api = useApi();
  const [q, setQ] = useState('Show production statistics for opencast and underground mines across subsidiaries');
  const [r, setR] = useState<any>();
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function ask(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError('');
    setR(undefined);
    try {
      setR(await api('/api/query', { method: 'POST', body: JSON.stringify({ query: q }) }));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unable to process question.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <Page title="Query Console" caption="Answers are only shown when supporting evidence is available.">
      <Card>
        <form onSubmit={ask} className="flex flex-col min-[651px]:flex-row gap-[10px]">
          <textarea
            className="flex-1 min-h-[88px] resize-y font-[inherit] border border-[#b9b8b1] rounded-[6px] p-[10px] bg-white text-[14px] focus:outline-none focus:border-[#2d4a3e] focus:ring-[2px] focus:ring-[#2d4a3e]/20 transition-colors"
            value={q}
            onChange={e => setQ(e.target.value)}
            placeholder="Ask a reporting or policy question…"
          />
          <button
            className="min-[651px]:self-end bg-[#2d4a3e] text-white rounded-[6px] py-[10px] px-[18px] text-[13px] font-[650] cursor-pointer border-0 disabled:opacity-60 disabled:cursor-wait whitespace-nowrap hover:bg-[#3a5a4e] transition-colors duration-150"
            disabled={busy}
          >
            {busy ? 'Searching…' : 'Ask question'}
          </button>
        </form>
      </Card>

      {error && <Message title="Query unavailable" text={error} />}

      {r && (
        <Card>
          <div className="flex items-center gap-[10px] mb-[16px] flex-wrap">
            <span className={`text-[11px] rounded-full px-[9px] py-[4px] font-[700] ${r.success ? 'bg-[#e3f0e6] text-[#23633b]' : 'bg-[#f9e9c9] text-[#825b10]'}`}>
              {r.intent} · {r.processing_path}
            </span>
          </div>
          <h2 className="text-[17px] font-[700] mb-[10px] mt-0 text-[#27312b]">Response</h2>
          <AIResponseRenderer content={r.answer} />
          {r.data_label && <p className="inline-block text-[12px] font-[700] bg-[#eee8d9] px-[8px] py-[4px] rounded-[3px] mb-[16px]">{r.data_label}</p>}
          <h3 className="text-[14px] font-[700] text-[#596259] mt-[20px] mb-[10px] uppercase tracking-[.6px]">Evidence &amp; Citations</h3>
          {r.evidence?.length
            ? <Table columns={['Source', 'Page', 'Location', 'Evidence']} rows={r.evidence.map((x: any) => [x.source_document || '—', x.source_page || '—', x.source_cell || x.source_section || '—', x.content || `${x.subsidiary || ''} ${x.financial_year || ''}: ${x.production_mt ?? ''} MT`])} />
            : <p className="text-[#697069] text-[13px]">No supporting evidence was returned; no factual assertion has been made.</p>}
        </Card>
      )}
    </Page>
  );
}

/* ─── Ingestion ─── */
function Ingestion() {
  const api = useApi();
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<any>();
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);

  async function upload(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    setBusy(true);
    setErr('');
    const f = new FormData();
    f.append('file', file);
    try {
      setResult(await api('/api/ingest', { method: 'POST', body: f }));
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Upload failed.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <Page title="Document ingestion" caption="Submitted material is extracted, validated, indexed and checked for conflicts.">
      <Card>
        <form onSubmit={upload} className="flex flex-col gap-[16px]">
          <label className="block">
            <span className="block text-[13px] font-[650] text-[#3a4541] mb-[6px]">Source document</span>
            <input
              className="font-[inherit] border border-[#b9b8b1] rounded-[6px] py-[9px] px-[12px] w-full bg-white text-[14px]"
              type="file"
              onChange={e => setFile(e.target.files?.[0] || null)}
            />
          </label>
          {file && <p className="text-[13px] text-[#3a4541] m-0">Selected: <b>{file.name}</b></p>}
          <div>
            <button
              className="bg-[#2d4a3e] text-white rounded-[6px] py-[10px] px-[18px] text-[13px] font-[650] cursor-pointer border-0 disabled:opacity-60 disabled:cursor-wait hover:bg-[#3a5a4e] transition-colors duration-150"
              disabled={!file || busy}
            >
              {busy ? 'Processing document…' : 'Submit for ingestion'}
            </button>
          </div>
        </form>
        {err && <p className="text-[#9f362b] text-[13px] mt-[12px]">{err}</p>}
        {result && (
          <div className="mt-[16px] p-[14px] bg-[#e9f1e9] border-l-[4px] border-[#37734a] rounded-r-[5px]">
            <b className="block text-[13px] text-[#23633b] mb-[4px]">Completed</b>
            <p className="text-[13px] m-0">{result.filename}: {result.ocr_pages} pages, {result.records_inserted} records, {result.conflicts_found} conflicts found.</p>
          </div>
        )}
      </Card>
    </Page>
  );
}

/* ─── Conflicts ─── */
function Conflicts() {
  const api = useApi();
  const { session } = useContext(Auth);
  const [d, setD] = useState<any>();
  const [err, setErr] = useState('');
  const refresh = () => api('/api/conflicts').then(setD).catch(e => setErr(e.message));
  useEffect(() => { void refresh(); }, []);

  async function review(id: number, action: string) {
    try {
      await api(`/api/conflicts/${id}/review`, { method: 'POST', body: JSON.stringify({ action }) });
      refresh();
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Review failed.');
    }
  }

  return (
    <Page title="Conflict management" caption="Conflicting authoritative values remain quarantined until human review.">
      {err && <p className="text-[#9f362b] text-[13px] mb-[12px]">{err}</p>}
      {!d ? <Loading /> : (
        <Card>
          <Table
            columns={['ID', 'Source', 'Field', 'Existing / incoming', 'Status', 'Action']}
            rows={d.conflicts.map((x: any) => [
              x.id,
              x.source_document,
              x.field_name,
              `${x.existing_value} / ${x.incoming_value}`,
              <span className="text-[11px] rounded-full px-[8px] py-[3px] font-[700] bg-[#f9e9c9] text-[#825b10]">{x.status}</span>,
              session?.user.role !== 'SUBSIDIARY_OFFICER' && x.status === 'PENDING_REVIEW'
                ? <span className="flex gap-[6px] flex-wrap">
                    <button className="bg-[#2d4a3e] text-white rounded-[5px] font-[650] cursor-pointer border-0 px-[8px] py-[4px] text-[11px] hover:bg-[#3a5a4e] transition-colors" onClick={() => review(x.id, 'APPROVED')}>Approve</button>
                    <button className="bg-[#86514b] text-white rounded-[5px] font-[650] cursor-pointer border-0 px-[8px] py-[4px] text-[11px] hover:bg-[#9a5e57] transition-colors" onClick={() => review(x.id, 'REJECTED')}>Reject</button>
                  </span>
                : '—',
            ])}
          />
        </Card>
      )}
    </Page>
  );
}

/* ─── Audit ─── */
function Audit() {
  const api = useApi();
  const [d, setD] = useState<any>();
  const [err, setErr] = useState('');
  useEffect(() => { api('/api/audit?limit=100').then(setD).catch(e => setErr(e.message)); }, []);
  return (
    <Page title="Audit log" caption="Recorded security and information actions for the active access scope.">
      {err && <p className="text-[#9f362b] text-[13px] mb-[12px]">{err}</p>}
      {!d ? <Loading /> : (
        <Card>
          <Table
            columns={['Timestamp', 'User', 'Role', 'Action', 'Context', 'Status']}
            rows={d.audit_log.map((x: any) => [x.timestamp, x.username, x.role, x.action, x.query || x.result_summary || '—', x.conflict_status || '—'])}
          />
        </Card>
      )}
    </Page>
  );
}

/* ─── Shared components ─── */
function Page({ title, caption, children }: { title: string; caption: string; children: React.ReactNode }) {
  return (
    <div className="p-[16px] min-[651px]:p-[28px] min-[901px]:p-[32px] max-w-[1440px] mx-auto">
      <div className="mb-[24px]">
        <h1 className="m-0 text-[24px] min-[651px]:text-[27px] font-[800] text-[#27312b] leading-tight">{title}</h1>
        <p className="text-[#697069] text-[13px] mt-[4px] mb-0">{caption}</p>
      </div>
      <div className="flex flex-col gap-[16px]">
        {children}
      </div>
    </div>
  );
}

function Card({ title, children }: { title?: string; children: React.ReactNode }) {
  return (
    <section className="bg-white border border-[#deddd7] rounded-[8px] p-[18px] min-[651px]:p-[22px] shadow-[0_1px_3px_rgba(0,0,0,0.07)]">
      {title && <h2 className="text-[16px] font-[700] text-[#27312b] mb-[14px] mt-0">{title}</h2>}
      {children}
    </section>
  );
}

function Metric({ name, value }: { name: string; value: any }) {
  return (
    <section className="bg-white border border-[#deddd7] rounded-[8px] p-[16px] min-[651px]:p-[20px] shadow-[0_1px_3px_rgba(0,0,0,0.07)]">
      <span className="block text-[#697069] text-[12px] font-[600] uppercase tracking-[.4px]">{name}</span>
      <b className="block mt-[8px] text-[22px] min-[651px]:text-[25px] font-[800] text-[#26332e]">{value}</b>
    </section>
  );
}

function Loading() {
  return (
    <div className="flex items-center gap-[10px] text-[#657067] p-[32px] text-[14px]">
      <span className="animate-spin text-[18px]">⟳</span>
      Loading information…
    </div>
  );
}

function Message({ title, text }: { title: string; text: string }) {
  return (
    <section className="bg-white border border-[#deddd7] border-l-[4px] border-l-[#9f362b] rounded-[8px] p-[18px] min-[651px]:p-[22px] shadow-[0_1px_3px_rgba(0,0,0,0.07)]">
      <h2 className="text-[16px] font-[700] mb-[8px] mt-0 text-[#7a2920]">{title}</h2>
      <p className="text-[14px] text-[#5a3030] m-0">{text}</p>
    </section>
  );
}

function Table({ columns, rows }: { columns: string[]; rows: any[][] }) {
  return (
    <div className="overflow-x-auto -mx-[18px] min-[651px]:-mx-[22px]">
      <table className="w-full border-collapse text-[13px] min-w-[500px]">
        <thead>
          <tr>
            {columns.map(c => (
              <th key={c} className="bg-[#f4f3ef] px-[14px] py-[10px] text-left text-[12px] font-[700] text-[#596259] uppercase tracking-[.4px] border-b border-[#e5e3dc] whitespace-nowrap">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.length
            ? rows.map((r, i) => (
                <tr key={i} className="hover:bg-[#fafaf8] transition-colors">
                  {r.map((v, j) => (
                    <td key={j} className="px-[14px] py-[10px] border-b border-[#e5e3dc] align-top text-[#3a4541]">
                      {v}
                    </td>
                  ))}
                </tr>
              ))
            : <tr><td colSpan={columns.length} className="px-[14px] py-[16px] text-[#697069] text-center">No records in the current scope.</td></tr>}
        </tbody>
      </table>
    </div>
  );
}

/* ─── App root ─── */
function App() {
  const [session, setSession] = useState<Session | null>(() => {
    try { return JSON.parse(localStorage.getItem('koha-session') || 'null'); } catch { return null; }
  });
  const value = {
    session,
    login: (s: Session) => { localStorage.setItem('koha-session', JSON.stringify(s)); setSession(s); },
    logout: () => { localStorage.removeItem('koha-session'); setSession(null); },
  };
  return (
    <Auth.Provider value={value}>
      <BrowserRouter>
        {session ? <Layout /> : <Routes><Route path="*" element={<Login />} /></Routes>}
      </BrowserRouter>
    </Auth.Provider>
  );
}

createRoot(document.getElementById('root')!).render(<App />);

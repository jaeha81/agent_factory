import { useState, useReducer, useEffect, useRef } from "react";

/* ═══════════════════════════════════════════════════════
   JH AGENT FACTORY — COMMAND CENTER DASHBOARD
   산업형 미래주의 커맨드센터 UI
   "에이전트를 개발이 아니라 생산한다"
═══════════════════════════════════════════════════════ */

// ─── SKILL CATALOG ──────────────────────────────────
const SKILLS = {
  log_analyzer:      { id:"log_analyzer",      name:"로그 분석기",    desc:"에이전트 로그를 분석하여 패턴·이상 감지",      cat:"monitoring",  ic:"◉" },
  api_reconnector:   { id:"api_reconnector",    name:"API 재연결기",   desc:"API 연결 실패 시 자동 재시도·복구",          cat:"network",     ic:"⟳" },
  agent_builder:     { id:"agent_builder",      name:"에이전트 빌더",  desc:"새로운 에이전트를 생성하는 핵심 스킬",        cat:"factory",     ic:"⬡" },
  resource_monitor:  { id:"resource_monitor",   name:"리소스 모니터",  desc:"CPU, 메모리, 스토리지 사용량 추적",          cat:"monitoring",  ic:"▦" },
  data_processor:    { id:"data_processor",     name:"데이터 처리기",  desc:"CSV, JSON, 텍스트 파싱·변환",              cat:"data",        ic:"⟐" },
  nlp_basic:         { id:"nlp_basic",          name:"자연어 처리",    desc:"텍스트 분석, 키워드 추출, 감정 분석",         cat:"ai",          ic:"◬" },
  scheduler:         { id:"scheduler",          name:"작업 스케줄러",  desc:"주기적 작업 예약·실행 관리",                cat:"automation",  ic:"◷" },
  memory_compressor: { id:"memory_compressor",  name:"메모리 압축기",  desc:"메모리 데이터를 요약·압축·구조화 저장",       cat:"memory",      ic:"◈" },
};

const ROLES = [
  { v:"general",         l:"범용 에이전트",   ic:"◇", color:"#64748B" },
  { v:"data_analyst",    l:"데이터 분석",     ic:"▦", color:"#06B6D4" },
  { v:"content_creator", l:"콘텐츠 생성",     ic:"◬", color:"#F472B6" },
  { v:"monitor",         l:"모니터링",        ic:"◉", color:"#34D399" },
  { v:"trader",          l:"트레이딩",        ic:"△", color:"#FBBF24" },
  { v:"researcher",      l:"리서치",          ic:"⟐", color:"#A78BFA" },
  { v:"automation",      l:"자동화",          ic:"⟳", color:"#FB923C" },
  { v:"security",        l:"보안",            ic:"⬡", color:"#EF4444" },
];

const AGENT_ICONS = ["◇","◈","◉","◬","▦","△","⬡","⟐","⟳","◷","⊕","⊗"];

// ─── ID GEN ─────────────────────────────────────────
let _seq = 0;
const uid = () => `ag_${Date.now().toString(36)}_${(++_seq).toString(36)}`;

// ─── AGENT FACTORY ──────────────────────────────────
function birthAgent(name, role, icon, desc, parentId, isMaster) {
  const roleObj = ROLES.find(r => r.v === role) || ROLES[0];
  const masterSkills = isMaster
    ? [SKILLS.agent_builder, SKILLS.resource_monitor, SKILLS.log_analyzer].map(s => ({...s, at: Date.now()}))
    : [];
  return {
    id: uid(), name, role, icon: isMaster ? "★" : icon,
    color: isMaster ? "#F59E0B" : roleObj.color,
    level: isMaster ? 5 : 1, xp: 0, maxXp: 100,
    status: "online", desc: desc || roleObj.l,
    skills: masterSkills,
    stats: {
      INT: isMaster ? 5 : 1, MEM: isMaster ? 5 : 1,
      SPD: isMaster ? 3 : 1, REL: isMaster ? 5 : 1
    },
    conns: [], parentId, born: Date.now(),
  };
}

// ─── STATE ───────────────────────────────────────────
function reducer(st, a) {
  const now = Date.now();
  const sysLog = (msg, lv="info") => ({ t: now, msg, lv });
  switch (a.type) {
    case "ADD": {
      const ag = a.payload;
      return { ...st, agents: [...st.agents, ag], sysLogs: [...st.sysLogs, sysLog(`에이전트 「${ag.name}」 생산 완료 — Lv.${ag.level}`, "ok")] };
    }
    case "EQUIP": {
      const sk = SKILLS[a.skillId];
      return {
        ...st,
        agents: st.agents.map(x => x.id === a.agentId ? { ...x, skills: [...x.skills, { ...sk, at: now }] } : x),
        sysLogs: [...st.sysLogs, sysLog(`스킬 [${sk.name}] 장착됨`, "ok")]
      };
    }
    case "UNEQUIP": {
      const sk = SKILLS[a.skillId];
      return {
        ...st,
        agents: st.agents.map(x => x.id === a.agentId ? { ...x, skills: x.skills.filter(s => s.id !== a.skillId) } : x),
        sysLogs: [...st.sysLogs, sysLog(`스킬 [${sk?.name}] 해제됨`)]
      };
    }
    case "CONNECT":
      return {
        ...st,
        agents: st.agents.map(x => x.id === a.from && !x.conns.includes(a.to) ? { ...x, conns: [...x.conns, a.to] } : x),
        sysLogs: [...st.sysLogs, sysLog(`노드 연결 수립`, "ok")]
      };
    case "DISCONNECT":
      return {
        ...st,
        agents: st.agents.map(x => x.id === a.from ? { ...x, conns: x.conns.filter(c => c !== a.to) } : x),
        sysLogs: [...st.sysLogs, sysLog(`노드 연결 해제`)]
      };
    case "SYSLOG":
      return { ...st, sysLogs: [...st.sysLogs, sysLog(a.msg, a.lv)] };
    default: return st;
  }
}

// ─── ANIMATION HOOK ─────────────────────────────────
function useFadeIn(delay = 0) {
  const [vis, setVis] = useState(false);
  useEffect(() => { const t = setTimeout(() => setVis(true), delay); return () => clearTimeout(t); }, [delay]);
  return { opacity: vis ? 1 : 0, transform: vis ? "translateY(0)" : "translateY(12px)", transition: `all 0.5s cubic-bezier(.16,1,.3,1) ${delay}ms` };
}

// ─── MICRO COMPONENTS ───────────────────────────────
const Glow = ({ color, size = 200, top, left, right, bottom }) => (
  <div style={{ position:"absolute", width:size, height:size, borderRadius:"50%",
    background:`radial-gradient(circle, ${color}15 0%, transparent 70%)`,
    top, left, right, bottom, pointerEvents:"none", filter:"blur(40px)" }} />
);

const StatBar = ({ label, value, max = 10, color }) => (
  <div style={{ display:"flex", alignItems:"center", gap:10, marginBottom:8 }}>
    <span style={{ width:32, fontSize:10, color:"#6B7A90", fontWeight:600, letterSpacing:"0.08em" }}>{label}</span>
    <div style={{ flex:1, height:6, borderRadius:3, background:"#1A2030", overflow:"hidden" }}>
      <div style={{ width:`${(value/max)*100}%`, height:"100%", borderRadius:3,
        background:`linear-gradient(90deg, ${color}, ${color}88)`,
        transition:"width 0.8s cubic-bezier(.16,1,.3,1)",
        boxShadow:`0 0 8px ${color}44` }} />
    </div>
    <span style={{ width:20, fontSize:11, fontWeight:700, textAlign:"right", color }}>{value}</span>
  </div>
);

const Badge = ({ children, color = "#6B7A90" }) => (
  <span style={{ display:"inline-flex", alignItems:"center", gap:3, padding:"3px 10px", borderRadius:6,
    fontSize:10, fontWeight:600, letterSpacing:"0.04em",
    background: color + "14", border:`1px solid ${color}33`, color }}>
    {children}
  </span>
);

const IconBtn = ({ children, onClick, active, color = "#6B7A90" }) => (
  <button onClick={onClick}
    style={{ padding:"6px 14px", borderRadius:8,
      border: active ? `1.5px solid ${color}` : "1.5px solid #1E2A3A",
      background: active ? color + "14" : "transparent",
      color: active ? color : "#6B7A90",
      cursor:"pointer", fontSize:12, fontFamily:"inherit",
      display:"flex", alignItems:"center", gap:5,
      transition:"all 0.2s" }}>
    {children}
  </button>
);

// ─── MAIN APP ───────────────────────────────────────
export default function AgentFactory() {
  const [st, dispatch] = useReducer(reducer, {
    agents: [],
    sysLogs: [{ t: Date.now(), msg: "시스템 부팅 — JH Agent Factory v1.0", lv: "sys" }]
  });
  const [view, setView] = useState("home");
  const [sel, setSel] = useState(null);
  const [form, setForm] = useState({ name:"", role:"general", icon:"◇", desc:"", master:false });
  const [logOpen, setLogOpen] = useState(true);
  const logRef = useRef(null);

  const master = st.agents.find(a => a.role === "master_controller");
  const hasMaster = !!master;

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [st.sysLogs]);

  const selAgent = sel ? st.agents.find(a => a.id === sel) : null;

  const doCreate = () => {
    if (!form.name.trim()) return;
    if (form.master && hasMaster) {
      dispatch({ type:"SYSLOG", msg:"마스터 에이전트는 1개만 허용됩니다", lv:"warn" });
      return;
    }
    const ag = birthAgent(
      form.name.trim(),
      form.master ? "master_controller" : form.role,
      form.icon, form.desc, master?.id || null, form.master
    );
    dispatch({ type:"ADD", payload: ag });
    setForm({ name:"", role:"general", icon:"◇", desc:"", master:false });
    setSel(ag.id);
    setView("detail");
  };

  const goDetail = (id) => { setSel(id); setView("detail"); };

  const tf = (t) => new Date(t).toLocaleTimeString("ko-KR", { hour:"2-digit", minute:"2-digit", second:"2-digit" });
  const logColor = { ok:"#34D399", warn:"#FBBF24", err:"#EF4444", info:"#64748B", sys:"#6366F1" };

  return (
    <div style={{
      background:"#080C14", color:"#CBD5E1", minHeight:"100vh",
      fontFamily:"'DM Mono', 'IBM Plex Mono', monospace", fontSize:13, position:"relative", overflow:"hidden"
    }}>
      <link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&family=Syne:wght@400;500;600;700;800&display=swap" rel="stylesheet"/>
      <style>{`
        @keyframes pulse { 0%,100%{opacity:0.4} 50%{opacity:1} }
        @keyframes scan { 0%{transform:translateY(-100%)} 100%{transform:translateY(100vh)} }
        @keyframes float { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-6px)} }
        @keyframes gridPulse { 0%,100%{opacity:0.03} 50%{opacity:0.06} }
        ::selection { background:#6366F133; color:#E2E8F0 }
        ::-webkit-scrollbar { width:4px }
        ::-webkit-scrollbar-track { background:transparent }
        ::-webkit-scrollbar-thumb { background:#1E2A3A; border-radius:2px }
        input:focus, textarea:focus { outline:none }
      `}</style>

      {/* BG */}
      <div style={{ position:"fixed", inset:0, pointerEvents:"none", zIndex:0 }}>
        <div style={{ position:"absolute", inset:0, backgroundImage:"radial-gradient(circle at 1px 1px, #1E2A3A22 1px, transparent 0)", backgroundSize:"32px 32px", animation:"gridPulse 8s ease infinite" }} />
        <Glow color="#6366F1" size={400} top="-100px" right="-100px" />
        <Glow color="#06B6D4" size={300} bottom="-50px" left="-50px" />
        <div style={{ position:"absolute", top:0, left:"50%", width:1, height:"100%", overflow:"hidden" }}>
          <div style={{ width:1, height:60, background:"linear-gradient(transparent, #6366F144, transparent)", animation:"scan 6s linear infinite" }} />
        </div>
      </div>

      {/* ─── HEADER ─── */}
      <header style={{
        position:"relative", zIndex:10, borderBottom:"1px solid #111827",
        padding:"0 24px", height:56, display:"flex", alignItems:"center", justifyContent:"space-between",
        background:"#080C14DD", backdropFilter:"blur(12px)"
      }}>
        <div style={{ display:"flex", alignItems:"center", gap:14 }}>
          <div style={{ position:"relative" }}>
            <div style={{
              width:32, height:32, borderRadius:8, border:"1.5px solid #6366F155",
              display:"flex", alignItems:"center", justifyContent:"center",
              fontSize:15, fontWeight:700, color:"#6366F1", fontFamily:"Syne", letterSpacing:"-0.02em"
            }}>JH</div>
            <div style={{ position:"absolute", top:-2, right:-2, width:6, height:6, borderRadius:3, background:"#34D399", animation:"pulse 2s ease infinite" }} />
          </div>
          <div>
            <div style={{ fontFamily:"Syne", fontWeight:700, fontSize:15, color:"#E2E8F0", letterSpacing:"-0.02em" }}>AGENT FACTORY</div>
            <div style={{ fontSize:9, color:"#475569", letterSpacing:"0.12em", marginTop:1 }}>{st.agents.length} UNITS DEPLOYED</div>
          </div>
        </div>
        <nav style={{ display:"flex", gap:4 }}>
          {[
            { k:"home", l:"OVERVIEW", s:"⬡" },
            { k:"create", l:"PRODUCE", s:"+" },
            { k:"nodes", l:"NETWORK", s:"◈" },
          ].map(n => (
            <button key={n.k} onClick={() => setView(n.k)}
              style={{
                padding:"7px 16px", borderRadius:6,
                border: view === n.k ? "1px solid #6366F155" : "1px solid transparent",
                background: view === n.k ? "#6366F10D" : "transparent",
                color: view === n.k ? "#A5B4FC" : "#475569",
                cursor:"pointer", fontSize:11, fontFamily:"inherit", letterSpacing:"0.06em", fontWeight:500,
                display:"flex", alignItems:"center", gap:6, transition:"all 0.2s"
              }}>
              <span style={{ fontSize:13, opacity:0.7 }}>{n.s}</span>{n.l}
            </button>
          ))}
          <button onClick={() => setLogOpen(o => !o)}
            style={{ padding:"7px 12px", borderRadius:6, border:"1px solid transparent",
              background: logOpen ? "#0F172A" : "transparent", color: logOpen ? "#34D399" : "#475569",
              cursor:"pointer", fontSize:11, fontFamily:"inherit", letterSpacing:"0.06em" }}>
            ◎ LOG
          </button>
        </nav>
      </header>

      <div style={{ display:"flex", position:"relative", zIndex:5, minHeight:"calc(100vh - 56px)" }}>
        {/* ═══ MAIN ═══ */}
        <main style={{ flex:1, padding:"28px 32px", overflowY:"auto", maxHeight:"calc(100vh - 56px)" }}>

          {/* HOME */}
          {view === "home" && (
            st.agents.length === 0 ? (
              <WelcomeScreen onStart={() => { setForm(f => ({...f, master:true})); setView("create"); }} />
            ) : (
              <div>
                <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fit, minmax(180px, 1fr))", gap:10, marginBottom:28 }}>
                  {[
                    { l:"TOTAL AGENTS", v:st.agents.length, c:"#6366F1", sub:"units" },
                    { l:"ACTIVE SKILLS", v:st.agents.reduce((s,a)=>s+a.skills.length,0), c:"#06B6D4", sub:"equipped" },
                    { l:"CONNECTIONS", v:st.agents.reduce((s,a)=>s+a.conns.length,0), c:"#FBBF24", sub:"nodes" },
                    { l:"AVG LEVEL", v:(st.agents.reduce((s,a)=>s+a.level,0)/st.agents.length).toFixed(1), c:"#34D399", sub:"power" },
                  ].map((m,i) => (
                    <div key={i} style={{ background:"#0D1117", borderRadius:12, padding:"16px 20px", border:"1px solid #111827", position:"relative", overflow:"hidden" }}>
                      <div style={{ position:"absolute", top:0, left:0, right:0, height:1, background:`linear-gradient(90deg, transparent, ${m.c}44, transparent)` }} />
                      <div style={{ fontSize:9, color:"#475569", letterSpacing:"0.1em", marginBottom:8, fontWeight:500 }}>{m.l}</div>
                      <div style={{ display:"flex", alignItems:"baseline", gap:6 }}>
                        <span style={{ fontSize:28, fontWeight:300, fontFamily:"Syne", color:m.c, letterSpacing:"-0.02em" }}>{m.v}</span>
                        <span style={{ fontSize:9, color:"#374151", letterSpacing:"0.08em" }}>{m.sub}</span>
                      </div>
                    </div>
                  ))}
                </div>

                <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:16 }}>
                  <div style={{ fontSize:10, color:"#475569", letterSpacing:"0.1em", fontWeight:600 }}>AGENT ROSTER</div>
                  <button onClick={() => setView("create")}
                    style={{ padding:"5px 14px", borderRadius:6, border:"1px solid #1E2A3A", background:"transparent", color:"#6366F1", cursor:"pointer", fontSize:11, fontFamily:"inherit", letterSpacing:"0.04em" }}>
                    + PRODUCE
                  </button>
                </div>

                <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill, minmax(280px, 1fr))", gap:10 }}>
                  {st.agents.map((a, idx) => (
                    <AgentCard key={a.id} agent={a} idx={idx} onClick={() => goDetail(a.id)} />
                  ))}
                </div>
              </div>
            )
          )}

          {/* CREATE */}
          {view === "create" && (
            <CreateScreen form={form} setForm={setForm} hasMaster={hasMaster} onCreate={doCreate} onCancel={() => setView("home")} />
          )}

          {/* DETAIL */}
          {view === "detail" && selAgent && (
            <DetailScreen agent={selAgent} allAgents={st.agents} onBack={() => setView("home")}
              onEquip={(sid) => dispatch({ type:"EQUIP", agentId:selAgent.id, skillId:sid })}
              onUnequip={(sid) => dispatch({ type:"UNEQUIP", agentId:selAgent.id, skillId:sid })}
              onConnect={(to) => dispatch({ type:"CONNECT", from:selAgent.id, to })} />
          )}

          {/* NODES */}
          {view === "nodes" && (
            <NodeScreen agents={st.agents}
              onConnect={(f,t) => dispatch({ type:"CONNECT", from:f, to:t })}
              onDisconnect={(f,t) => dispatch({ type:"DISCONNECT", from:f, to:t })}
              onSelect={(id) => goDetail(id)} />
          )}
        </main>

        {/* ═══ LOG PANEL ═══ */}
        {logOpen && (
          <aside style={{ width:260, borderLeft:"1px solid #111827", background:"#0A0E16EE", backdropFilter:"blur(8px)", display:"flex", flexDirection:"column", maxHeight:"calc(100vh - 56px)" }}>
            <div style={{ padding:"14px 16px 10px", borderBottom:"1px solid #111827", display:"flex", alignItems:"center", justifyContent:"space-between" }}>
              <div style={{ fontSize:9, color:"#475569", letterSpacing:"0.12em", fontWeight:600 }}>◎ SYSTEM LOG</div>
              <div style={{ width:6, height:6, borderRadius:3, background:"#34D399", animation:"pulse 2s ease infinite" }} />
            </div>
            <div ref={logRef} style={{ flex:1, overflowY:"auto", padding:"8px 12px" }}>
              {st.sysLogs.map((l,i) => (
                <div key={i} style={{ padding:"8px 10px", marginBottom:4, borderRadius:6, background:"#0D1117", border:"1px solid #11182766", fontSize:11, lineHeight:1.6 }}>
                  <span style={{ color: logColor[l.lv] || "#64748B", marginRight:6, fontSize:10 }}>
                    {l.lv === "ok" ? "✓" : l.lv === "warn" ? "△" : l.lv === "err" ? "✕" : l.lv === "sys" ? "◆" : "·"}
                  </span>
                  <span style={{ color:"#94A3B8" }}>{l.msg}</span>
                  <div style={{ fontSize:9, color:"#334155", marginTop:3 }}>{tf(l.t)}</div>
                </div>
              ))}
            </div>
            {master && (
              <div style={{ padding:12, borderTop:"1px solid #111827" }}>
                <div style={{ display:"flex", alignItems:"center", gap:8, padding:"10px 12px", borderRadius:8, background:"#F59E0B08", border:"1px solid #F59E0B22" }}>
                  <span style={{ fontSize:16 }}>★</span>
                  <div style={{ flex:1 }}>
                    <div style={{ fontSize:11, fontWeight:600, color:"#F59E0B" }}>{master.name}</div>
                    <div style={{ fontSize:9, color:"#92400E" }}>MASTER CONTROLLER</div>
                  </div>
                  <div style={{ width:6, height:6, borderRadius:3, background:"#34D399" }} />
                </div>
              </div>
            )}
          </aside>
        )}
      </div>
    </div>
  );
}

// ═════════════════════════════════════════════════════
function WelcomeScreen({ onStart }) {
  const fade1 = useFadeIn(100);
  const fade2 = useFadeIn(300);
  const fade3 = useFadeIn(500);

  return (
    <div style={{ display:"flex", flexDirection:"column", alignItems:"center", justifyContent:"center", minHeight:"70vh", textAlign:"center", position:"relative" }}>
      <Glow color="#6366F1" size={500} top="10%" left="30%" />
      <div style={fade1}>
        <div style={{ width:80, height:80, borderRadius:20, border:"1.5px solid #1E2A3A", display:"flex", alignItems:"center", justifyContent:"center", margin:"0 auto 28px", position:"relative", background:"#0D1117" }}>
          <span style={{ fontFamily:"Syne", fontSize:28, fontWeight:800, color:"#6366F1", letterSpacing:"-0.04em" }}>JH</span>
          <div style={{ position:"absolute", inset:-1, borderRadius:21, border:"1px solid #6366F122", animation:"pulse 3s ease infinite" }} />
        </div>
      </div>
      <div style={fade2}>
        <h1 style={{ fontFamily:"Syne", fontWeight:800, fontSize:36, color:"#E2E8F0", letterSpacing:"-0.03em", margin:"0 0 8px", lineHeight:1.2 }}>AGENT FACTORY</h1>
        <p style={{ color:"#475569", fontSize:13, lineHeight:1.8, maxWidth:380, margin:"0 auto 8px" }}>
          에이전트를 <span style={{ color:"#6366F1" }}>생산</span>하고, <span style={{ color:"#06B6D4" }}>장착</span>하고, <span style={{ color:"#FBBF24" }}>연결</span>하는 공장
        </p>
        <p style={{ color:"#334155", fontSize:11, letterSpacing:"0.06em", marginBottom:36 }}>첫 번째 마스터 에이전트를 생성하여 공장을 가동하세요</p>
      </div>
      <div style={fade3}>
        <button onClick={onStart}
          onMouseOver={e => { e.currentTarget.style.transform = "translateY(-2px)"; e.currentTarget.style.boxShadow = "0 8px 32px #6366F133"; }}
          onMouseOut={e => { e.currentTarget.style.transform = "none"; e.currentTarget.style.boxShadow = "0 4px 20px #6366F122"; }}
          style={{ padding:"14px 36px", borderRadius:10, border:"1px solid #6366F144", background:"linear-gradient(135deg, #6366F1, #4F46E5)", color:"#fff", cursor:"pointer", fontFamily:"Syne", fontWeight:700, fontSize:14, letterSpacing:"0.02em", boxShadow:"0 4px 20px #6366F122", transition:"all 0.2s" }}>
          ★ 마스터 에이전트 생성
        </button>
      </div>
      <div style={{ position:"absolute", bottom:40, left:"50%", transform:"translateX(-50%)", display:"flex", gap:16, opacity:0.15 }}>
        {Array.from({length:7}).map((_,i) => (
          <div key={i} style={{ width:8, height:8, borderRadius:2, border:"1px solid #6366F1", animation:`float ${2+i*0.3}s ease infinite`, animationDelay:`${i*0.15}s` }} />
        ))}
      </div>
    </div>
  );
}

// ═════════════════════════════════════════════════════
function AgentCard({ agent: a, idx, onClick }) {
  const [hov, setHov] = useState(false);
  const fade = useFadeIn(idx * 60);

  return (
    <div onClick={onClick} onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)}
      style={{ ...fade, background: hov ? "#0F1520" : "#0D1117", borderRadius:12, padding:"18px 20px", border: hov ? `1px solid ${a.color}33` : "1px solid #111827", cursor:"pointer", position:"relative", overflow:"hidden", transition:"all 0.25s" }}>
      <div style={{ position:"absolute", top:0, left:0, right:0, height:1, background:`linear-gradient(90deg, transparent, ${a.color}55, transparent)`, opacity: hov ? 1 : 0.4, transition:"opacity 0.3s" }} />
      <div style={{ display:"flex", alignItems:"center", gap:12, marginBottom:14 }}>
        <div style={{ width:44, height:44, borderRadius:12, border:`1.5px solid ${a.color}33`, background:`${a.color}0A`, display:"flex", alignItems:"center", justifyContent:"center", fontSize:20, fontWeight:700, color:a.color, fontFamily:"Syne", transition:"all 0.2s", transform: hov ? "scale(1.05)" : "none" }}>{a.icon}</div>
        <div style={{ flex:1 }}>
          <div style={{ fontFamily:"Syne", fontWeight:600, fontSize:15, color:"#E2E8F0", letterSpacing:"-0.01em" }}>{a.name}</div>
          <div style={{ fontSize:10, color:"#475569", marginTop:2, letterSpacing:"0.04em" }}>{a.role}</div>
        </div>
        <div style={{ padding:"4px 10px", borderRadius:6, background:"#6366F10D", border:"1px solid #6366F133", fontSize:11, fontFamily:"Syne", fontWeight:700, color:"#A5B4FC" }}>{a.level}</div>
      </div>
      {a.skills.length > 0 && (
        <div style={{ display:"flex", gap:4, flexWrap:"wrap", marginBottom:12 }}>
          {a.skills.slice(0,4).map(s => (
            <span key={s.id} style={{ fontSize:9, padding:"2px 8px", borderRadius:4, background:"#06B6D40A", border:"1px solid #06B6D422", color:"#06B6D4", letterSpacing:"0.02em" }}>{s.ic} {s.name}</span>
          ))}
          {a.skills.length > 4 && <span style={{ fontSize:9, color:"#374151", padding:"2px 4px" }}>+{a.skills.length-4}</span>}
        </div>
      )}
      <div style={{ display:"flex", gap:16, fontSize:10, color:"#334155" }}>
        <span>◈ {a.conns.length}</span>
        <span>⬡ {a.skills.length}</span>
        <span style={{ color:"#34D399", display:"flex", alignItems:"center", gap:3 }}>
          <span style={{ width:4, height:4, borderRadius:2, background:"#34D399", display:"inline-block" }} /> online
        </span>
      </div>
    </div>
  );
}

// ═════════════════════════════════════════════════════
function CreateScreen({ form, setForm, hasMaster, onCreate, onCancel }) {
  const upd = (k,v) => setForm(f => ({...f, [k]:v}));

  return (
    <div style={{ maxWidth:540, margin:"0 auto" }}>
      <button onClick={onCancel} style={{ background:"none", border:"none", color:"#475569", cursor:"pointer", fontSize:11, fontFamily:"inherit", marginBottom:20 }}>← BACK</button>
      <div style={{ marginBottom:32 }}>
        <h2 style={{ fontFamily:"Syne", fontWeight:800, fontSize:24, color:"#E2E8F0", margin:"0 0 6px", letterSpacing:"-0.02em" }}>
          {form.master ? "★ MASTER AGENT" : "NEW AGENT"}
        </h2>
        <p style={{ color:"#475569", fontSize:12, margin:0, lineHeight:1.6 }}>
          {form.master ? "시스템 총괄 에이전트. 모든 생산을 통제합니다." : "Level 1 초기 상태로 생산됩니다. 이후 스킬을 장착하세요."}
        </p>
      </div>

      <div style={{ marginBottom:24 }}>
        <label style={{ fontSize:9, color:"#475569", letterSpacing:"0.12em", fontWeight:600, display:"block", marginBottom:8 }}>AGENT NAME</label>
        <input value={form.name} onChange={e => upd("name", e.target.value)} placeholder="이름을 입력하세요" autoFocus
          style={{ width:"100%", padding:"14px 18px", borderRadius:10, border:"1.5px solid #1E2A3A", background:"#0D1117", color:"#E2E8F0", fontSize:16, fontFamily:"Syne", fontWeight:500, letterSpacing:"-0.01em", boxSizing:"border-box", transition:"border-color 0.2s" }}
          onFocus={e => e.target.style.borderColor = "#6366F155"} onBlur={e => e.target.style.borderColor = "#1E2A3A"} />
      </div>

      <div style={{ marginBottom:24 }}>
        <label style={{ fontSize:9, color:"#475569", letterSpacing:"0.12em", fontWeight:600, display:"block", marginBottom:8 }}>IDENTIFIER</label>
        <div style={{ display:"flex", gap:6, flexWrap:"wrap" }}>
          {AGENT_ICONS.map(ic => (
            <button key={ic} onClick={() => upd("icon", ic)}
              style={{ width:42, height:42, borderRadius:10, border: form.icon === ic ? "1.5px solid #6366F1" : "1.5px solid #1E2A3A", background: form.icon === ic ? "#6366F10D" : "#0D1117", color: form.icon === ic ? "#A5B4FC" : "#475569", cursor:"pointer", fontSize:16, fontFamily:"Syne", fontWeight:700, display:"flex", alignItems:"center", justifyContent:"center", transition:"all 0.15s" }}>{ic}</button>
          ))}
        </div>
      </div>

      {!form.master && (
        <div style={{ marginBottom:24 }}>
          <label style={{ fontSize:9, color:"#475569", letterSpacing:"0.12em", fontWeight:600, display:"block", marginBottom:8 }}>SPECIALIZATION</label>
          <div style={{ display:"grid", gridTemplateColumns:"repeat(4, 1fr)", gap:6 }}>
            {ROLES.map(r => (
              <button key={r.v} onClick={() => upd("role", r.v)}
                style={{ padding:"12px 6px", borderRadius:10, textAlign:"center", border: form.role === r.v ? `1.5px solid ${r.color}55` : "1.5px solid #1E2A3A", background: form.role === r.v ? `${r.color}0A` : "#0D1117", color: form.role === r.v ? r.color : "#475569", cursor:"pointer", fontSize:11, fontFamily:"inherit", transition:"all 0.15s" }}>
                <div style={{ fontSize:18, marginBottom:4, fontFamily:"Syne" }}>{r.ic}</div>
                <div style={{ fontSize:10, letterSpacing:"0.02em" }}>{r.l}</div>
              </button>
            ))}
          </div>
        </div>
      )}

      <div style={{ marginBottom:24 }}>
        <label style={{ fontSize:9, color:"#475569", letterSpacing:"0.12em", fontWeight:600, display:"block", marginBottom:8 }}>DESCRIPTION</label>
        <textarea value={form.desc} onChange={e => upd("desc", e.target.value)} placeholder="에이전트의 목적과 역할..." rows={3}
          style={{ width:"100%", padding:"12px 16px", borderRadius:10, border:"1.5px solid #1E2A3A", background:"#0D1117", color:"#CBD5E1", fontSize:12, fontFamily:"inherit", resize:"vertical", boxSizing:"border-box", lineHeight:1.7 }} />
      </div>

      {!hasMaster && (
        <div style={{ marginBottom:28 }}>
          <button onClick={() => upd("master", !form.master)}
            style={{ display:"flex", alignItems:"center", gap:12, width:"100%", padding:"14px 18px", borderRadius:10, border: form.master ? "1.5px solid #F59E0B33" : "1.5px solid #1E2A3A", background: form.master ? "#F59E0B08" : "#0D1117", cursor:"pointer", textAlign:"left", fontFamily:"inherit" }}>
            <div style={{ width:38, height:20, borderRadius:10, background: form.master ? "#F59E0B" : "#1E2A3A", position:"relative", transition:"background 0.2s" }}>
              <div style={{ width:16, height:16, borderRadius:8, background:"#fff", position:"absolute", top:2, left: form.master ? 20 : 2, transition:"left 0.2s", boxShadow:"0 1px 4px #00000033" }} />
            </div>
            <div>
              <div style={{ fontSize:12, color: form.master ? "#F59E0B" : "#64748B", fontWeight:600 }}>마스터 에이전트로 생성</div>
              <div style={{ fontSize:10, color:"#475569", marginTop:2 }}>시스템 총괄 · 최초 1회만 가능</div>
            </div>
          </button>
        </div>
      )}

      <div style={{ display:"flex", gap:10 }}>
        <button onClick={onCancel}
          style={{ flex:1, padding:"13px", borderRadius:10, border:"1.5px solid #1E2A3A", background:"transparent", color:"#475569", cursor:"pointer", fontFamily:"inherit", fontSize:12, letterSpacing:"0.04em" }}>CANCEL</button>
        <button onClick={onCreate} disabled={!form.name.trim()}
          style={{ flex:2, padding:"13px", borderRadius:10, border:"none",
            background: form.name.trim() ? (form.master ? "linear-gradient(135deg, #F59E0B, #D97706)" : "linear-gradient(135deg, #6366F1, #4F46E5)") : "#1E2A3A",
            color: form.name.trim() ? "#fff" : "#475569", cursor: form.name.trim() ? "pointer" : "not-allowed",
            fontFamily:"Syne", fontWeight:700, fontSize:13, letterSpacing:"0.02em", boxShadow: form.name.trim() ? "0 4px 20px #6366F122" : "none", transition:"all 0.2s" }}>
          {form.master ? "★ PRODUCE MASTER" : "⬡ PRODUCE AGENT"}
        </button>
      </div>
    </div>
  );
}

// ═════════════════════════════════════════════════════
function DetailScreen({ agent: a, allAgents, onBack, onEquip, onUnequip, onConnect }) {
  const [tab, setTab] = useState("skills");
  const unequipped = Object.values(SKILLS).filter(s => !a.skills.find(e => e.id === s.id));
  const connectable = allAgents.filter(x => x.id !== a.id && !a.conns.includes(x.id));
  const connected = allAgents.filter(x => a.conns.includes(x.id));

  return (
    <div>
      <button onClick={onBack} style={{ background:"none", border:"none", color:"#475569", cursor:"pointer", fontSize:11, fontFamily:"inherit", marginBottom:20 }}>← ROSTER</button>

      <div style={{ display:"flex", alignItems:"center", gap:18, marginBottom:32 }}>
        <div style={{ width:72, height:72, borderRadius:20, border:`2px solid ${a.color}33`, background:`${a.color}08`, display:"flex", alignItems:"center", justifyContent:"center", fontSize:32, fontFamily:"Syne", fontWeight:800, color:a.color }}>{a.icon}</div>
        <div style={{ flex:1 }}>
          <div style={{ fontFamily:"Syne", fontWeight:800, fontSize:26, color:"#E2E8F0", letterSpacing:"-0.02em" }}>{a.name}</div>
          <div style={{ fontSize:11, color:"#475569", marginTop:4, letterSpacing:"0.04em" }}>{a.role} · {a.id}</div>
          {a.desc && <div style={{ fontSize:11, color:"#64748B", marginTop:6, lineHeight:1.6 }}>{a.desc}</div>}
        </div>
        <div style={{ textAlign:"center", padding:"12px 22px", borderRadius:12, background:"#0D1117", border:"1px solid #111827" }}>
          <div style={{ fontSize:9, color:"#475569", letterSpacing:"0.1em", marginBottom:4 }}>LEVEL</div>
          <div style={{ fontSize:32, fontFamily:"Syne", fontWeight:700, color:"#A5B4FC", letterSpacing:"-0.02em" }}>{a.level}</div>
        </div>
      </div>

      <div style={{ background:"#0D1117", borderRadius:14, padding:"20px 24px", border:"1px solid #111827", marginBottom:20 }}>
        <div style={{ fontSize:9, color:"#475569", letterSpacing:"0.12em", fontWeight:600, marginBottom:14 }}>COMBAT STATS</div>
        <StatBar label="INT" value={a.stats.INT} color="#6366F1" />
        <StatBar label="MEM" value={a.stats.MEM} color="#06B6D4" />
        <StatBar label="SPD" value={a.stats.SPD} color="#FBBF24" />
        <StatBar label="REL" value={a.stats.REL} color="#34D399" />
      </div>

      <div style={{ display:"flex", gap:4, marginBottom:16 }}>
        <IconBtn onClick={() => setTab("skills")} active={tab==="skills"} color="#06B6D4">⬡ SKILLS ({a.skills.length})</IconBtn>
        <IconBtn onClick={() => setTab("connect")} active={tab==="connect"} color="#FBBF24">◈ NODES ({a.conns.length})</IconBtn>
      </div>

      {tab === "skills" && (
        <div style={{ background:"#0D1117", borderRadius:14, padding:"20px 24px", border:"1px solid #111827" }}>
          {a.skills.length > 0 && (
            <div style={{ marginBottom:20 }}>
              <div style={{ fontSize:9, color:"#475569", letterSpacing:"0.12em", fontWeight:600, marginBottom:10 }}>EQUIPPED</div>
              <div style={{ display:"flex", flexDirection:"column", gap:6 }}>
                {a.skills.map(s => (
                  <div key={s.id} style={{ display:"flex", alignItems:"center", gap:12, padding:"12px 16px", borderRadius:10, background:"#080C14", border:"1px solid #1E2A3A" }}>
                    <span style={{ fontSize:16, color:"#06B6D4", fontFamily:"Syne", fontWeight:700, width:24, textAlign:"center" }}>{s.ic}</span>
                    <div style={{ flex:1 }}>
                      <div style={{ fontSize:12, fontWeight:600, color:"#CBD5E1" }}>{s.name}</div>
                      <div style={{ fontSize:10, color:"#475569", marginTop:2 }}>{s.desc}</div>
                    </div>
                    <Badge color="#06B6D4">{s.cat}</Badge>
                    <button onClick={() => onUnequip(s.id)}
                      style={{ padding:"5px 10px", borderRadius:6, border:"1px solid #EF444433", background:"#EF44440A", color:"#EF4444", cursor:"pointer", fontSize:10, fontFamily:"inherit", letterSpacing:"0.04em" }}>REMOVE</button>
                  </div>
                ))}
              </div>
            </div>
          )}
          {unequipped.length > 0 && (
            <div>
              <div style={{ fontSize:9, color:"#475569", letterSpacing:"0.12em", fontWeight:600, marginBottom:10 }}>AVAILABLE</div>
              <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill, minmax(200px, 1fr))", gap:6 }}>
                {unequipped.map(s => (
                  <button key={s.id} onClick={() => onEquip(s.id)}
                    style={{ padding:"12px 14px", borderRadius:10, textAlign:"left", border:"1.5px solid #1E2A3A", background:"#080C14", cursor:"pointer", fontFamily:"inherit", transition:"all 0.15s", display:"flex", alignItems:"center", gap:10 }}
                    onMouseOver={e => e.currentTarget.style.borderColor = "#06B6D433"} onMouseOut={e => e.currentTarget.style.borderColor = "#1E2A3A"}>
                    <span style={{ fontSize:16, color:"#475569", fontFamily:"Syne" }}>{s.ic}</span>
                    <div>
                      <div style={{ fontSize:11, color:"#94A3B8", fontWeight:500 }}>{s.name}</div>
                      <div style={{ fontSize:9, color:"#334155", marginTop:2 }}>{s.cat}</div>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {tab === "connect" && (
        <div style={{ background:"#0D1117", borderRadius:14, padding:"20px 24px", border:"1px solid #111827" }}>
          {connected.length > 0 && (
            <div style={{ marginBottom:20 }}>
              <div style={{ fontSize:9, color:"#475569", letterSpacing:"0.12em", fontWeight:600, marginBottom:10 }}>LINKED NODES</div>
              {connected.map(c => (
                <div key={c.id} style={{ display:"flex", alignItems:"center", gap:12, padding:"12px 16px", borderRadius:10, background:"#080C14", border:"1px solid #FBBF2422", marginBottom:6 }}>
                  <span style={{ fontSize:18, color:c.color, fontFamily:"Syne", fontWeight:700 }}>{c.icon}</span>
                  <div style={{ flex:1 }}>
                    <div style={{ fontSize:12, fontWeight:600, color:"#CBD5E1" }}>{c.name}</div>
                    <div style={{ fontSize:10, color:"#475569" }}>Lv.{c.level} · {c.role}</div>
                  </div>
                  <span style={{ fontSize:10, color:"#FBBF24" }}>LINKED</span>
                </div>
              ))}
            </div>
          )}
          {connectable.length > 0 && (
            <div>
              <div style={{ fontSize:9, color:"#475569", letterSpacing:"0.12em", fontWeight:600, marginBottom:10 }}>AVAILABLE NODES</div>
              <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill, minmax(200px, 1fr))", gap:6 }}>
                {connectable.map(c => (
                  <button key={c.id} onClick={() => onConnect(c.id)}
                    style={{ padding:"12px 14px", borderRadius:10, textAlign:"left", border:"1.5px solid #1E2A3A", background:"#080C14", cursor:"pointer", fontFamily:"inherit", display:"flex", alignItems:"center", gap:10, transition:"all 0.15s" }}
                    onMouseOver={e => e.currentTarget.style.borderColor = "#FBBF2433"} onMouseOut={e => e.currentTarget.style.borderColor = "#1E2A3A"}>
                    <span style={{ fontSize:16, color:c.color, fontFamily:"Syne", fontWeight:700 }}>{c.icon}</span>
                    <div>
                      <div style={{ fontSize:11, color:"#94A3B8", fontWeight:500 }}>{c.name}</div>
                      <div style={{ fontSize:9, color:"#334155" }}>Lv.{c.level}</div>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}
          {allAgents.length < 2 && <div style={{ textAlign:"center", padding:32, color:"#334155", fontSize:12 }}>연결할 에이전트가 필요합니다.</div>}
        </div>
      )}
    </div>
  );
}

// ═════════════════════════════════════════════════════
function NodeScreen({ agents, onConnect, onDisconnect, onSelect }) {
  if (agents.length === 0) {
    return <div style={{ textAlign:"center", padding:"80px 20px", color:"#334155" }}><div style={{ fontSize:40, marginBottom:16, opacity:0.3 }}>◈</div><div style={{ fontSize:13 }}>에이전트를 먼저 생산하세요</div></div>;
  }

  const cx = 320, cy = 220, r = Math.min(160, 60 + agents.length * 20);
  const positions = agents.map((_, i) => {
    const angle = (i / agents.length) * Math.PI * 2 - Math.PI / 2;
    return { x: cx + Math.cos(angle) * r, y: cy + Math.sin(angle) * r };
  });

  return (
    <div>
      <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:20 }}>
        <div>
          <h2 style={{ fontFamily:"Syne", fontWeight:800, fontSize:22, color:"#E2E8F0", margin:"0 0 4px", letterSpacing:"-0.02em" }}>NETWORK MAP</h2>
          <p style={{ fontSize:11, color:"#475569", margin:0 }}>에이전트 간 통신 경로를 설정합니다</p>
        </div>
      </div>

      <div style={{ background:"#0D1117", borderRadius:16, border:"1px solid #111827", position:"relative", height:460, overflow:"hidden" }}>
        <svg style={{ position:"absolute", inset:0, width:"100%", height:"100%" }}>
          <defs>
            <pattern id="ngrid" width="32" height="32" patternUnits="userSpaceOnUse">
              <path d="M 32 0 L 0 0 0 32" fill="none" stroke="#1E2A3A" strokeWidth="0.3" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#ngrid)" opacity="0.4" />
          {agents.map((a, ai) =>
            a.conns.map(cid => {
              const ci = agents.findIndex(x => x.id === cid);
              if (ci === -1) return null;
              const p1 = positions[ai], p2 = positions[ci];
              const mx = (p1.x + p2.x) / 2, my = (p1.y + p2.y) / 2;
              return (
                <g key={`${a.id}-${cid}`}>
                  <line x1={p1.x} y1={p1.y} x2={p2.x} y2={p2.y} stroke="#FBBF24" strokeWidth="1.5" opacity="0.25" />
                  <line x1={p1.x} y1={p1.y} x2={p2.x} y2={p2.y} stroke="#FBBF24" strokeWidth="1" opacity="0.5" strokeDasharray="4,6">
                    <animate attributeName="stroke-dashoffset" from="0" to="-20" dur="2s" repeatCount="indefinite" />
                  </line>
                  <circle cx={mx} cy={my} r="3" fill="#FBBF24" opacity="0.6">
                    <animate attributeName="r" values="2;4;2" dur="2s" repeatCount="indefinite" />
                  </circle>
                </g>
              );
            })
          )}
        </svg>

        {agents.map((a, i) => {
          const p = positions[i];
          return (
            <div key={a.id} onClick={() => onSelect(a.id)}
              style={{ position:"absolute", left: p.x - 36, top: p.y - 36, width:72, height:72, borderRadius:20, background:"#0D1117", border:`2px solid ${a.color}44`, display:"flex", flexDirection:"column", alignItems:"center", justifyContent:"center", cursor:"pointer", transition:"all 0.2s", zIndex:5 }}
              onMouseOver={e => { e.currentTarget.style.borderColor = a.color; e.currentTarget.style.transform = "scale(1.1)"; }}
              onMouseOut={e => { e.currentTarget.style.borderColor = a.color + "44"; e.currentTarget.style.transform = "none"; }}>
              <div style={{ fontSize:22, fontFamily:"Syne", fontWeight:800, color:a.color, lineHeight:1 }}>{a.icon}</div>
              <div style={{ fontSize:8, color:"#94A3B8", marginTop:3, fontWeight:600, letterSpacing:"0.04em", maxWidth:60, overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap", textAlign:"center" }}>{a.name}</div>
              <div style={{ position:"absolute", top:4, right:4, width:6, height:6, borderRadius:3, background:"#34D399" }} />
              <div style={{ position:"absolute", bottom:-6, background:"#0D1117", border:`1px solid ${a.color}33`, padding:"1px 6px", borderRadius:4, fontSize:8, color:a.color, fontWeight:700, fontFamily:"Syne" }}>{a.level}</div>
            </div>
          );
        })}

        <div style={{ position:"absolute", left:cx-30, top:cy-10, textAlign:"center", pointerEvents:"none" }}>
          <div style={{ fontSize:9, color:"#334155", letterSpacing:"0.12em", fontWeight:600 }}>FACTORY</div>
          <div style={{ fontSize:8, color:"#1E2A3A" }}>CORE</div>
        </div>
      </div>

      {agents.length >= 2 && (
        <div style={{ marginTop:16, background:"#0D1117", borderRadius:12, padding:"16px 20px", border:"1px solid #111827" }}>
          <div style={{ fontSize:9, color:"#475569", letterSpacing:"0.12em", fontWeight:600, marginBottom:10 }}>QUICK CONNECT</div>
          <div style={{ display:"flex", flexWrap:"wrap", gap:6 }}>
            {agents.flatMap(a =>
              agents.filter(b => b.id !== a.id && !a.conns.includes(b.id)).map(b => (
                <button key={`${a.id}-${b.id}`} onClick={() => onConnect(a.id, b.id)}
                  style={{ padding:"6px 12px", borderRadius:6, border:"1px solid #1E2A3A", background:"transparent", cursor:"pointer", fontFamily:"inherit", fontSize:10, color:"#64748B", display:"flex", alignItems:"center", gap:4, transition:"all 0.15s" }}
                  onMouseOver={e => e.currentTarget.style.borderColor = "#FBBF2444"} onMouseOut={e => e.currentTarget.style.borderColor = "#1E2A3A"}>
                  <span style={{ color:a.color }}>{a.icon}</span>
                  <span style={{ color:"#334155" }}>→</span>
                  <span style={{ color:b.color }}>{b.icon}</span>
                  <span style={{ marginLeft:2 }}>{a.name} → {b.name}</span>
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}

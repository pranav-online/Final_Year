import React, { useState, useMemo, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getDiseaseStatus, predictDisease } from '../services/api';
import toast from 'react-hot-toast';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { motion, AnimatePresence } from 'framer-motion';
import { Activity, Shield, Beaker, HelpCircle, Layers, MessageCircle, ChevronDown, X, Clock, Leaf, AlertTriangle, TrendingUp } from 'lucide-react';
import AnimatedBackground from '../components/AnimatedBackground';
import './DiseaseDetection.css';

/* ══════════════════════════════════════════════════
   HELPERS – Parse AI report into sections
   ══════════════════════════════════════════════════ */
function splitScreens(report) {
  if (!report) return { first: '', second: '', third: '' };
  const f = report.indexOf('---FIRST_SCREEN---');
  const s = report.indexOf('---SECOND_SCREEN---');
  const t = report.indexOf('---THIRD_SCREEN---');
  if (f === -1 || s === -1 || t === -1) return { first: report, second: '', third: '' };
  return {
    first:  report.substring(f + 18, s).trim(),
    second: report.substring(s + 19, t).trim(),
    third:  report.substring(t + 18).trim(),
  };
}

function extractSection(md, keyword) {
  if (!md) return '';
  const lines = md.split('\n');
  let capturing = false, result = [];
  for (const line of lines) {
    if (line.startsWith('# ')) {
      if (capturing) break;
      if (line.toLowerCase().includes(keyword.toLowerCase())) capturing = true;
      continue;
    }
    if (capturing) result.push(line);
  }
  return result.join('\n').trim();
}

function parseMedicines(md) {
  const raw = extractSection(md, 'Recommended Medicines') || extractSection(md, 'Recommended Products');
  if (!raw) return [];
  const meds = [];
  const lines = raw.split('\n');
  let current = null;
  for (const line of lines) {
    const rankMatch = line.match(/^(🥇|🥈|🥉)\s*\*\*(.+?)\*\*/);
    if (rankMatch) {
      if (current) meds.push(current);
      current = { rank: rankMatch[1] === '🥇' ? '1st' : rankMatch[1] === '🥈' ? '2nd' : '3rd', name: rankMatch[2], details: [] };
    } else if (current && line.trim().startsWith('-')) {
      current.details.push(line.trim().replace(/^-\s*/, ''));
    }
  }
  if (current) meds.push(current);
  return meds;
}

function parseActionPlan(md) {
  const raw = extractSection(md, 'Action Plan') || extractSection(md, "Today's Action");
  if (!raw) return [];
  return raw.split('\n').filter(l => l.trim()).map(l => l.replace(/^[0-9️⃣]+\s*/, '').replace(/^\d+\.\s*/, '').trim()).filter(Boolean).slice(0, 5);
}

function parseBullets(md, keyword) {
  const raw = extractSection(md, keyword);
  if (!raw) return [];
  return raw.split('\n').map(l => l.replace(/^[-•✔☁🌧💧🌱🌾✅]\s*/, '').trim()).filter(Boolean).slice(0, 6);
}

function parseFaq(md) {
  const raw = extractSection(md, 'Frequently Asked');
  if (!raw) return [];
  const items = [];
  const lines = raw.split('\n');
  let q = null, a = [];
  for (const line of lines) {
    const qMatch = line.match(/\*\*❓?\s*(.+?)\*\*/);
    if (qMatch) {
      if (q) items.push({ q, a: a.join('\n').trim() });
      q = qMatch[1].replace(/^❓\s*/, '').replace(/\??\s*$/, '?');
      a = [];
    } else if (line.trim() && q) a.push(line);
  }
  if (q) items.push({ q, a: a.join('\n').trim() });
  return items;
}

function parseForecast(md) {
  const raw = extractSection(md, 'Forecast') || extractSection(md, 'Spread Forecast');
  if (!raw) return [];
  const days = [];
  const lines = raw.split('\n');
  for (const line of lines) {
    const m = line.match(/Day\s*(\d+)\s*\|\s*(High|Medium|Low)\s*\|\s*(.+)/i);
    if (m) days.push({ day: m[1], risk: m[2].toLowerCase(), reason: m[3].trim() });
  }
  return days;
}

function sevConfig(severity) {
  switch (severity) {
    case 'High':   return { color: '#ef4444', bg: 'rgba(239,68,68,0.1)', label: 'High Risk', pct: 80 };
    case 'Medium': return { color: '#f59e0b', bg: 'rgba(245,158,11,0.1)', label: 'Moderate Risk', pct: 50 };
    case 'None':   return { color: '#22c55e', bg: 'rgba(34,197,94,0.1)',  label: 'Healthy', pct: 5 };
    default:       return { color: '#22c55e', bg: 'rgba(34,197,94,0.1)',  label: 'Low Risk', pct: 25 };
  }
}

const TAB_ICONS = { overview: Activity, treatment: Beaker, prevention: Shield, faq: HelpCircle, advanced: Layers };
const TABS = ['overview', 'treatment', 'prevention', 'faq', 'advanced'];
const ADV_TABS = ['report', 'scientific', 'forecast', 'analysis'];
const fadeVariant = { initial: { opacity: 0, y: 12 }, animate: { opacity: 1, y: 0 }, exit: { opacity: 0, y: -8 }, transition: { duration: 0.25 } };

/* ══════════════════════════════════════════════════
   MAIN COMPONENT
   ══════════════════════════════════════════════════ */
export default function DiseaseDetection() {
  const nav = useNavigate();
  const [image, setImage]     = useState(null);
  const [preview, setPreview] = useState(null);
  const [result, setResult]   = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [serviceStatus, setServiceStatus] = useState(null);
  const [tab, setTab]         = useState('overview');
  const [advTab, setAdvTab]   = useState('report');
  const [faqOpen, setFaqOpen] = useState(null);
  const [drawer, setDrawer]   = useState(false);

  useEffect(() => {
    getDiseaseStatus()
      .then((response) => setServiceStatus(response.data))
      .catch(() => setServiceStatus({ success: false }));
  }, []);

  const handleImage = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.type.startsWith('image/')) {
      setError('Choose a valid image file.');
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      setError('Image must be 10 MB or smaller.');
      return;
    }
    setError('');
    setImage(file);
    setPreview(URL.createObjectURL(file));
    setResult(null);
  };

  const handleAnalyze = async () => {
    if (!image) { toast.error('Upload an image first'); return; }
    setError('');
    setLoading(true);
    try {
      const fd = new FormData(); fd.append('file', image);
      const res = await predictDisease(fd);
      setResult(res.data); setTab('overview');
      toast.success(res.data.ai_report_status === 'generated' ? 'Analysis and Gemini report complete' : 'Analysis complete; using treatment guidance fallback');
    } catch (err) {
      const message = err.response?.data?.detail || 'Disease analysis failed. Check the server and try again.';
      setError(message);
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  /* Parsed data */
  const screens = useMemo(() => splitScreens(result?.detailed_report), [result]);
  const meds = useMemo(() => parseMedicines(screens.first || screens.second), [screens]);
  const actions = useMemo(() => parseActionPlan(screens.first), [screens]);
  const causes = useMemo(() => parseBullets(screens.second, 'Why This Happened'), [screens]);
  const prevention = useMemo(() => parseBullets(screens.second, 'Prevent'), [screens]);
  const faqItems = useMemo(() => parseFaq(screens.second), [screens]);
  const forecast = useMemo(() => parseForecast(screens.third), [screens]);
  const sev = result ? sevConfig(result.severity) : null;

  const cropName = result?.raw_class?.split('___')[0]?.replace(/_/g, ' ')?.replace('(maize)', '(Maize)') || '';
  const diseaseName = result?.raw_class?.split('___')[1]?.replace(/_/g, ' ') || 'Healthy';
  const confidenceLabel = result?.prediction_source === 'gemini'
    ? 'AI-estimated confidence'
    : 'Model confidence';

  const isMalformed = Boolean(
    (result?.ai_report_status && result.ai_report_status !== 'generated') ||
    (result?.detailed_report && (
      (actions.length === 0 && meds.length === 0) ||
      result.detailed_report.includes('Could not generate AI detailed report')
    ))
  );

  /* ── Render ─────────────────────────────────── */
  return (
    <div className="dd-page">
      <AnimatedBackground diseaseDetected={result?.status === 'diseased'} />

      {/* Header */}
      <header className="dd-header">
        <button className="dd-header-back" onClick={() => nav('/farmer')}>← Back</button>
        <h1 className="dd-header-title">Disease Intelligence</h1>
        <span className="dd-header-badge">AI Powered</span>
      </header>

      {/* ── Upload View ──────────────────────────── */}
      {!result && (
        <div className="dd-upload-wrap">
          <div className="dd-upload-card">
            <h2 className="dd-upload-title">Analyze Crop Disease</h2>
            <p className="dd-upload-sub">Upload a clear leaf image for instant AI diagnosis</p>
            {serviceStatus && (
              <div className="dd-service-status" role="status">
                <div>
                  <strong>Prediction:</strong>{' '}
                  {serviceStatus.prediction_message || 'Status unavailable'}
                </div>
                <div>
                  <strong>Gemini analysis and report:</strong>{' '}
                  {serviceStatus.gemini_configured
                    ? `Configured (${serviceStatus.gemini_model}${serviceStatus.gemini_fallback_model ? `; fallback: ${serviceStatus.gemini_fallback_model}` : ''}); image classification is used when local model weights are unavailable.`
                    : 'Not configured. Gemini image classification and detailed reports need GEMINI_API_KEY in the backend .env file.'}
                </div>
              </div>
            )}
            <label className="dd-upload-box">
              {preview ? <img src={preview} alt="leaf" className="dd-upload-preview" />
                : <><div className="dd-upload-icon"><Leaf size={36} strokeWidth={1.5} /></div>
                    <p style={{ margin: 0, color: '#94A3B8' }}>Click to upload leaf image</p>
                    <p className="dd-upload-hint">JPG, PNG supported</p></>}
              <input type="file" accept="image/*" onChange={handleImage} style={{ display: 'none' }} />
            </label>
            {image && <p className="dd-upload-filename">{image.name}</p>}
            {error && <p className="dd-upload-error" role="alert">{error}</p>}
            <button
              className="dd-analyze-btn"
              onClick={handleAnalyze}
              disabled={loading || serviceStatus?.prediction_available === false}
            >
              {loading ? 'Analyzing…' : serviceStatus?.prediction_available === false ? 'Prediction Unavailable' : 'Analyze Disease'}
            </button>
          </div>
        </div>
      )}

      {/* ── Dashboard View ───────────────────────── */}
      {result && (
        <div className="dd-dashboard">

          {/* ── Sidebar ──────────────────────────── */}
          <aside className="dd-sidebar">
            {preview && <img src={preview} alt="leaf" className="dd-sidebar-img" />}

            <div>
              <p className="dd-sidebar-label">Crop</p>
              <p className="dd-sidebar-value green">{cropName}</p>
              <p className="dd-sidebar-label">Disease</p>
              <p className="dd-sidebar-value">{diseaseName}</p>
            </div>

            <div className="dd-sidebar-divider" />

            <div>
              <p className="dd-sidebar-label">
                {result.prediction_source === 'gemini' ? 'AI-estimated confidence' : 'Model confidence'}
              </p>
              <p className="dd-sidebar-value">{result.confidence}%</p>
              <div className="dd-sev-bar-bg">
                <div className="dd-sev-bar-fill" style={{ width: `${result.confidence}%`, background: 'var(--dd-accent)' }} />
              </div>
              <p className="dd-sidebar-label" style={{ marginTop: 8 }}>
                {result.prediction_source === 'gemini'
                  ? `Classified by Gemini${result.prediction_model ? ` (${result.prediction_model})` : ''}`
                  : 'Classified by local model'}
              </p>
            </div>

            <div className="dd-sidebar-divider" />

            {sev && (
              <div>
                <p className="dd-sidebar-label">Severity</p>
                <div className="dd-sev-bar-bg">
                  <div className="dd-sev-bar-fill" style={{ width: `${sev.pct}%`, background: sev.color }} />
                </div>
                <div className="dd-sev-badge" style={{ background: sev.bg, color: sev.color }}>{sev.label}</div>
              </div>
            )}

            <div className="dd-sidebar-divider" />

            <div>
              <p className="dd-sidebar-label">Scanned</p>
              <p className="dd-sidebar-value" style={{ fontSize: 13 }}>{new Date().toLocaleString()}</p>
            </div>

            <button className="dd-analyze-btn" style={{ marginTop: 'auto', fontSize: 13 }}
              onClick={() => { setResult(null); setImage(null); setPreview(null); }}>
              New Scan
            </button>
          </aside>

          {/* ── Content ──────────────────────────── */}
          <main className="dd-content">
            {/* Tabs */}
            <div className="dd-tabs">
              {TABS.map(t => {
                const Icon = TAB_ICONS[t];
                return (
                  <button key={t} className={`dd-tab ${tab === t ? 'active' : ''}`} onClick={() => setTab(t)}>
                    <Icon size={14} style={{ marginRight: 6, verticalAlign: -2 }} />
                    {t.charAt(0).toUpperCase() + t.slice(1)}
                  </button>
                );
              })}
            </div>

            {/* Tab Content */}
            <AnimatePresence mode="wait">
              <motion.div key={tab} {...fadeVariant}>

                {/* ═══ OVERVIEW TAB ═══════════════════ */}
                {tab === 'overview' && isMalformed ? (
                  <div className="dd-stagger" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                    <div className="dd-card-grid">
                      <div className="dd-card dd-fade-up">
                        <div className="dd-card-title"><Activity size={14} /> Disease Summary</div>
                        <div className="dd-metric"><span className="dd-metric-label">Crop</span><span className="dd-metric-value" style={{ color: 'var(--dd-accent)' }}>{cropName}</span></div>
                        <div className="dd-metric"><span className="dd-metric-label">Disease</span><span className="dd-metric-value">{diseaseName}</span></div>
                        <div style={{ display: 'flex', gap: 16, marginTop: 8 }}>
                          <div className="dd-metric"><span className="dd-metric-label">{confidenceLabel}</span><span className="dd-metric-value">{result.confidence}%</span></div>
                          <div className="dd-metric"><span className="dd-metric-label">Severity</span><span className="dd-metric-value" style={{ color: sev.color }}>{sev.label}</span></div>
                        </div>
                      </div>
                    </div>
                    <div className="dd-card dd-fade-up">
                      <div className="dd-card-title"><AlertTriangle size={14} /> AI Report / Fallback Data</div>
                      <div className="dd-md">
                        {result.ai_report_status === 'generated' ? (
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>{result.detailed_report}</ReactMarkdown>
                        ) : (
                          <>
                            <p>{result.detailed_report}</p>
                            <h4>💊 Treatment</h4>
                            <p>{result.treatment}</p>
                            <h4>🛡️ Prevention</h4>
                            <p>{result.prevention}</p>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                ) : tab === 'overview' && (
                  <div className="dd-stagger" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                    {/* Summary + Urgency */}
                    <div className="dd-card-grid">
                      <div className="dd-card dd-fade-up">
                        <div className="dd-card-title"><Activity size={14} /> Disease Summary</div>
                        <div className="dd-metric"><span className="dd-metric-label">Crop</span><span className="dd-metric-value" style={{ color: 'var(--dd-accent)' }}>{cropName}</span></div>
                        <div className="dd-metric"><span className="dd-metric-label">Disease</span><span className="dd-metric-value">{diseaseName}</span></div>
                        <div style={{ display: 'flex', gap: 16, marginTop: 8 }}>
                          <div className="dd-metric"><span className="dd-metric-label">{confidenceLabel}</span><span className="dd-metric-value">{result.confidence}%</span></div>
                          <div className="dd-metric"><span className="dd-metric-label">Severity</span><span className="dd-metric-value" style={{ color: sev.color }}>{sev.label}</span></div>
                        </div>
                      </div>
                      <div className="dd-card dd-fade-up">
                        <div className="dd-card-title"><AlertTriangle size={14} /> Urgency Status</div>
                        <div className="dd-md">
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>{extractSection(screens.first, 'Action Required')}</ReactMarkdown>
                        </div>
                      </div>
                    </div>

                    {/* Medicines */}
                    {meds.length > 0 && (
                      <div className="dd-card dd-fade-up">
                        <div className="dd-card-title"><Beaker size={14} /> Recommended Medicines</div>
                        <div className="dd-card-grid-3">
                          {meds.slice(0, 3).map((m, i) => (
                            <div className="dd-med-card" key={i}>
                              <div className="dd-med-rank">{m.rank} Choice</div>
                              <div className="dd-med-name">{m.name}</div>
                              {m.details.map((d, j) => <div className="dd-med-detail" key={j}>{d}</div>)}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Action Plan */}
                    {actions.length > 0 && (
                      <div className="dd-card dd-fade-up">
                        <div className="dd-card-title"><Clock size={14} /> Today's Action Plan</div>
                        <ul className="dd-checklist">
                          {actions.map((a, i) => (
                            <li className="dd-check-item" key={i}>
                              <div className="dd-check-icon" style={{ background: 'rgba(82,183,136,0.15)', color: 'var(--dd-accent)' }}>{i + 1}</div>
                              {a}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Economic Impact */}
                    {extractSection(screens.second, 'Economic') && (
                      <div className="dd-card dd-fade-up">
                        <div className="dd-card-title"><TrendingUp size={14} /> Economic Impact</div>
                        <div className="dd-md">
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>{extractSection(screens.second, 'Economic')}</ReactMarkdown>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* ═══ TREATMENT TAB ══════════════════ */}
                {tab === 'treatment' && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                    {/* Products Grid */}
                    {meds.length > 0 && (
                      <div className="dd-card dd-fade-up">
                        <div className="dd-card-title"><Beaker size={14} /> Medicine Details</div>
                        <div className="dd-card-grid-3">
                          {meds.map((m, i) => (
                            <div className="dd-med-card" key={i}>
                              <div className="dd-med-rank">{m.rank} Choice</div>
                              <div className="dd-med-name">{m.name}</div>
                              {m.details.map((d, j) => <div className="dd-med-detail" key={j}>{d}</div>)}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Treatment Timeline */}
                    {actions.length > 0 && (
                      <div className="dd-card dd-fade-up">
                        <div className="dd-card-title"><Clock size={14} /> Treatment Timeline</div>
                        <div className="dd-timeline">
                          {actions.map((a, i) => (
                            <div className="dd-timeline-item" key={i}>
                              <div className="dd-timeline-dot" />
                              <div className="dd-timeline-step">Step {i + 1}</div>
                              <div className="dd-timeline-text">{a}</div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Application Instructions */}
                    {extractSection(screens.third, 'Treatment Procedure') && (
                      <div className="dd-card dd-fade-up">
                        <div className="dd-card-title"><Shield size={14} /> Application Instructions</div>
                        <div className="dd-md">
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>{extractSection(screens.third, 'Treatment Procedure')}</ReactMarkdown>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* ═══ PREVENTION TAB ═════════════════ */}
                {tab === 'prevention' && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                    <div className="dd-card-grid">
                      {/* Causes */}
                      <div className="dd-card dd-fade-up">
                        <div className="dd-card-title"><AlertTriangle size={14} /> Why It Happened</div>
                        {causes.length > 0 ? (
                          <ul className="dd-checklist">
                            {causes.map((c, i) => (
                              <li className="dd-check-item" key={i}>
                                <div className="dd-check-icon" style={{ background: 'rgba(239,68,68,0.12)', color: 'var(--dd-danger)', fontSize: 10 }}>!</div>
                                {c}
                              </li>
                            ))}
                          </ul>
                        ) : <div className="dd-md"><ReactMarkdown remarkPlugins={[remarkGfm]}>{extractSection(screens.second, 'Why This Happened')}</ReactMarkdown></div>}
                      </div>

                      {/* Prevention Checklist */}
                      <div className="dd-card dd-fade-up">
                        <div className="dd-card-title"><Shield size={14} /> Prevention Checklist</div>
                        {prevention.length > 0 ? (
                          <ul className="dd-checklist">
                            {prevention.map((p, i) => (
                              <li className="dd-check-item" key={i}>
                                <div className="dd-check-icon" style={{ background: 'rgba(34,197,94,0.12)', color: 'var(--dd-success)' }}>✓</div>
                                {p}
                              </li>
                            ))}
                          </ul>
                        ) : <div className="dd-md"><ReactMarkdown remarkPlugins={[remarkGfm]}>{extractSection(screens.second, 'Prevent')}</ReactMarkdown></div>}
                      </div>
                    </div>

                    {/* Spread Risk Gauge */}
                    {sev && (
                      <div className="dd-card dd-fade-up" style={{ textAlign: 'center' }}>
                        <div className="dd-card-title" style={{ justifyContent: 'center' }}>Disease Spread Risk</div>
                        <div style={{ position: 'relative', width: 160, height: 80, margin: '12px auto 0', overflow: 'hidden' }}>
                          <div style={{ width: 160, height: 160, borderRadius: '50%', border: '8px solid rgba(255,255,255,0.06)', borderBottomColor: 'transparent', borderRightColor: 'transparent', transform: 'rotate(225deg)', position: 'absolute', top: 0, left: 0 }} />
                          <div style={{ width: 160, height: 160, borderRadius: '50%', border: `8px solid ${sev.color}`, borderBottomColor: 'transparent', borderRightColor: 'transparent', transform: `rotate(${225 + sev.pct * 1.8}deg)`, position: 'absolute', top: 0, left: 0, transition: 'transform 1.5s ease' }} />
                        </div>
                        <div style={{ fontSize: 28, fontWeight: 700, color: sev.color, marginTop: 4 }}>{sev.pct}%</div>
                        <div style={{ fontSize: 13, color: 'var(--dd-text-dim)', marginTop: 2 }}>{sev.label}</div>
                      </div>
                    )}
                  </div>
                )}

                {/* ═══ FAQ TAB ════════════════════════ */}
                {tab === 'faq' && (
                  <div className="dd-card dd-fade-up">
                    <div className="dd-card-title"><HelpCircle size={14} /> Frequently Asked Questions</div>
                    {faqItems.length > 0 ? (
                      <div className="dd-accordion">
                        {faqItems.map((item, i) => (
                          <div key={i}>
                            <div className={`dd-acc-header ${faqOpen === i ? 'open' : ''}`} onClick={() => setFaqOpen(faqOpen === i ? null : i)}>
                              {item.q}
                              <ChevronDown size={14} className={`dd-acc-chevron ${faqOpen === i ? 'open' : ''}`} />
                            </div>
                            {faqOpen === i && (
                              <div className="dd-acc-body dd-md">
                                <ReactMarkdown remarkPlugins={[remarkGfm]}>{item.a}</ReactMarkdown>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="dd-md">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{extractSection(screens.second, 'Frequently Asked')}</ReactMarkdown>
                      </div>
                    )}
                  </div>
                )}

                {/* ═══ ADVANCED TAB ═══════════════════ */}
                {tab === 'advanced' && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                    <div className="dd-subtabs">
                      {ADV_TABS.map(t => (
                        <button key={t} className={`dd-subtab ${advTab === t ? 'active' : ''}`} onClick={() => setAdvTab(t)}>
                          {t.charAt(0).toUpperCase() + t.slice(1)}
                        </button>
                      ))}
                    </div>

                    <AnimatePresence mode="wait">
                      <motion.div key={advTab} {...fadeVariant}>

                        {/* AI Report */}
                        {advTab === 'report' && (
                          <div className="dd-card dd-fade-up">
                            <div className="dd-card-title"><Layers size={14} /> AI Diagnostic Report</div>
                            <div className="dd-md">
                              <ReactMarkdown remarkPlugins={[remarkGfm]}>{extractSection(screens.third, 'Detailed AI Report') || extractSection(screens.third, 'AI Report')}</ReactMarkdown>
                            </div>
                          </div>
                        )}

                        {/* Scientific */}
                        {advTab === 'scientific' && (
                          <div className="dd-card dd-fade-up">
                            <div className="dd-card-title"><Beaker size={14} /> Scientific Information</div>
                            <div className="dd-md">
                              <ReactMarkdown remarkPlugins={[remarkGfm]}>{extractSection(screens.third, 'Scientific')}</ReactMarkdown>
                            </div>
                          </div>
                        )}

                        {/* Forecast */}
                        {advTab === 'forecast' && (
                          <div className="dd-card dd-fade-up">
                            <div className="dd-card-title"><TrendingUp size={14} /> 7-Day Disease Spread Forecast</div>
                            {forecast.length > 0 ? (
                              <div className="dd-forecast-row">
                                {forecast.map((d, i) => (
                                  <div className="dd-forecast-day" key={i}>
                                    <div className="dd-forecast-label">Day {d.day}</div>
                                    <div className={`dd-forecast-risk ${d.risk}`}>{d.risk.charAt(0).toUpperCase() + d.risk.slice(1)}</div>
                                    <div style={{ fontSize: 11, color: 'var(--dd-text-muted)', marginTop: 6 }}>{d.reason}</div>
                                  </div>
                                ))}
                              </div>
                            ) : (
                              <div className="dd-md">
                                <ReactMarkdown remarkPlugins={[remarkGfm]}>{extractSection(screens.third, 'Forecast')}</ReactMarkdown>
                              </div>
                            )}
                          </div>
                        )}

                        {/* Analysis */}
                        {advTab === 'analysis' && (
                          <div className="dd-card dd-fade-up">
                            <div className="dd-card-title"><Activity size={14} /> Advanced Analysis</div>
                            <div className="dd-md">
                              <ReactMarkdown remarkPlugins={[remarkGfm]}>{extractSection(screens.third, 'Advanced Analysis') || extractSection(screens.third, 'Analysis')}</ReactMarkdown>
                            </div>
                          </div>
                        )}

                      </motion.div>
                    </AnimatePresence>
                  </div>
                )}

              </motion.div>
            </AnimatePresence>
          </main>
        </div>
      )}

      {/* ── Floating AI Button ──────────────────── */}
      {result && (
        <button className="dd-fab" onClick={() => setDrawer(true)} title="Ask AI">
          <MessageCircle size={22} />
        </button>
      )}

      {/* ── AI Assistant Drawer ─────────────────── */}
      {drawer && (
        <>
          <div className="dd-drawer-overlay dd-fade-in" onClick={() => setDrawer(false)} />
          <div className="dd-drawer dd-slide-in">
            <div className="dd-drawer-title">
              AI Assistant
              <button className="dd-drawer-close" onClick={() => setDrawer(false)}><X size={18} /></button>
            </div>
            <p style={{ color: 'var(--dd-text-dim)', fontSize: 13, marginBottom: 20 }}>
              Ask any question about <strong>{diseaseName}</strong> on <strong>{cropName}</strong>.
            </p>
            <div className="dd-drawer-suggestions">
              {['Why did this disease happen?', 'Which medicine should I use?', 'Can it spread to other plants?', 'Will my yield be affected?', 'What should I do today?'].map((q, i) => (
                <button className="dd-drawer-sug" key={i} onClick={() => { toast(`💬 ${q}\n\nAI Chat feature coming soon!`, { duration: 3000 }); }}>
                  {q}
                </button>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
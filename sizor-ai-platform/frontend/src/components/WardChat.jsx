import { useState, useEffect, useRef } from "react";
import { sendWardChatMessage } from "../api/chat";
import { useTheme } from "../theme/ThemeContext";

const SUGGESTED = [
  "What's the overall patient status across all wards?",
  "Which wards need immediate attention right now?",
  "How many RED flag patients do we have and why?",
  "Give me a summary of open escalations",
  "Which pathway has the highest risk patients?",
  "Are there any patterns I should be concerned about?",
];

function TypingIndicator({ t }) {
  return (
    <div style={{ display:"flex", alignItems:"flex-end", gap:"8px" }}>
      <div style={{ width:24, height:24, borderRadius:"8px", background:t.brandGlow, border:"1px solid "+t.brand+"40", display:"flex", alignItems:"center", justifyContent:"center", flexShrink:0 }}>
        <svg style={{ width:12, height:12 }} fill="none" viewBox="0 0 24 24" stroke={t.brand} strokeWidth={2.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z"/>
        </svg>
      </div>
      <div style={{ background:t.surfaceHigh, border:"1px solid "+t.border, borderRadius:"14px", borderBottomLeftRadius:"4px", padding:"10px 14px", display:"flex", alignItems:"center", gap:"5px" }}>
        {[0, 150, 300].map(delay => (
          <span key={delay} style={{ width:6, height:6, borderRadius:"50%", background:t.textMuted, display:"inline-block", animation:"bounce 1.2s infinite", animationDelay:delay+"ms" }}/>
        ))}
      </div>
    </div>
  );
}

function Message({ msg, t }) {
  const isUser = msg.role === "user";
  return (
    <div style={{ display:"flex", flexDirection:"column", gap:"3px", alignItems:isUser?"flex-end":"flex-start" }}>
      <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", letterSpacing:"1px", color:isUser?t.brand:t.textMuted, paddingLeft:"2px", paddingRight:"2px" }}>
        {isUser ? "CLINICIAN" : "SIZOR AI"}
      </span>
      <div style={{
        maxWidth:"84%",
        background: isUser ? "linear-gradient(135deg,"+t.brand+","+t.brandDark+")" : t.surfaceHigh,
        border: "1px solid " + (isUser ? t.brand+"60" : t.border),
        borderRadius:"14px",
        borderTopRightRadius: isUser ? "4px" : "14px",
        borderTopLeftRadius:  isUser ? "14px" : "4px",
        padding:"10px 14px",
        fontFamily:"'Outfit',sans-serif",
        fontSize:"13px",
        lineHeight:1.6,
        color: isUser ? "#fff" : t.textPrimary,
        boxShadow: isUser ? "0 2px 12px "+t.brand+"30" : "none",
      }}>
        {msg.content.split("\n").map((line, i, arr) => (
          <span key={i}>{line}{i < arr.length - 1 && <br/>}</span>
        ))}
      </div>
    </div>
  );
}

export default function WardChat() {
  const { t } = useTheme();
  const [open, setOpen]         = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput]       = useState("");
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState("");
  const bottomRef = useRef(null);
  const inputRef  = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior:"smooth" });
  }, [messages, loading]);

  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 100);
  }, [open]);

  async function send(text) {
    const content = (text || input).trim();
    if (!content || loading) return;
    setInput("");
    setError("");
    const userMsg = { role:"user", content };
    const next = [...messages, userMsg];
    setMessages(next);
    setLoading(true);
    try {
      const { reply } = await sendWardChatMessage(next, null);
      setMessages([...next, { role:"assistant", content:reply }]);
    } catch {
      setError("Failed to get a response. Check your API keys and try again.");
    } finally {
      setLoading(false);
    }
  }

  function handleKey(e) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
  }

  return (
    <>
      {/* Floating button */}
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          position:"fixed", bottom:"24px", right:"24px", zIndex:50,
          width:52, height:52, borderRadius:"50%", border:"none",
          background: open
            ? t.surfaceHigh
            : "linear-gradient(135deg,"+t.brand+","+t.brandDark+")",
          boxShadow: open
            ? "0 4px 20px "+t.shadow
            : "0 8px 32px "+t.brand+"50",
          cursor:"pointer",
          display:"flex", alignItems:"center", justifyContent:"center",
          transition:"all 0.25s ease",
        }}
        onMouseEnter={e => { if (!open) e.currentTarget.style.transform="scale(1.1)"; }}
        onMouseLeave={e => { if (!open) e.currentTarget.style.transform="scale(1)"; }}
        title="Sizor AI — Ward Intelligence"
      >
        {open ? (
          <svg style={{ width:18, height:18 }} fill="none" viewBox="0 0 24 24" stroke={t.textPrimary} strokeWidth={2.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12"/>
          </svg>
        ) : (
          <svg style={{ width:22, height:22 }} fill="none" viewBox="0 0 24 24" stroke="#fff" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z"/>
          </svg>
        )}
        {!open && messages.length > 0 && (
          <span style={{ position:"absolute", top:2, right:2, width:10, height:10, borderRadius:"50%", background:t.red, border:"2px solid "+t.bg }}/>
        )}
      </button>

      {/* Chat panel */}
      {open && (
        <div style={{
          position:"fixed", bottom:"88px", right:"24px", zIndex:50,
          width:400, maxHeight:"72vh",
          display:"flex", flexDirection:"column",
          background:t.surface,
          border:"1px solid "+t.border,
          borderRadius:"20px",
          boxShadow:"0 24px 64px "+t.shadow+", 0 0 0 1px "+t.borderHigh,
          overflow:"hidden",
          animation:"chatSlideUp 0.2s ease",
        }}>

          {/* Header */}
          <div style={{
            background:"linear-gradient(135deg,"+t.brand+"18,"+t.brandDark+"10)",
            borderBottom:"1px solid "+t.border,
            padding:"14px 16px",
            display:"flex", alignItems:"center", justifyContent:"space-between",
            flexShrink:0,
          }}>
            <div style={{ display:"flex", alignItems:"center", gap:"10px" }}>
              <div style={{ width:34, height:34, borderRadius:"10px", background:"linear-gradient(135deg,"+t.brand+","+t.brandDark+")", display:"flex", alignItems:"center", justifyContent:"center", boxShadow:"0 4px 12px "+t.brand+"40" }}>
                <svg style={{ width:17, height:17 }} fill="none" viewBox="0 0 24 24" stroke="#fff" strokeWidth={2.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z"/>
                </svg>
              </div>
              <div>
                <div style={{ fontFamily:"'Outfit',sans-serif", fontWeight:800, fontSize:"14px", color:t.textPrimary, lineHeight:1.1 }}>Sizor AI</div>
                <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.brand, marginTop:"2px", letterSpacing:"0.5px" }}>WARD INTELLIGENCE</div>
              </div>
            </div>
            <div style={{ display:"flex", alignItems:"center", gap:"8px" }}>
              <div style={{ display:"flex", alignItems:"center", gap:"4px" }}>
                <span style={{ width:6, height:6, borderRadius:"50%", background:t.green, display:"inline-block", boxShadow:"0 0 6px "+t.green }}/>
                <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.green }}>LIVE</span>
              </div>
              {messages.length > 0 && (
                <button
                  onClick={() => { setMessages([]); setError(""); }}
                  title="Clear chat"
                  style={{ width:26, height:26, borderRadius:"7px", background:t.surfaceHigh, border:"1px solid "+t.border, cursor:"pointer", display:"flex", alignItems:"center", justifyContent:"center" }}
                  onMouseEnter={e => e.currentTarget.style.borderColor = t.borderHigh}
                  onMouseLeave={e => e.currentTarget.style.borderColor = t.border}
                >
                  <svg style={{ width:12, height:12 }} fill="none" viewBox="0 0 24 24" stroke={t.textMuted} strokeWidth={2.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                  </svg>
                </button>
              )}
            </div>
          </div>

          {/* Messages */}
          <div style={{ flex:1, overflowY:"auto", padding:"16px", display:"flex", flexDirection:"column", gap:"12px", minHeight:0 }}>
            {messages.length === 0 ? (
              <div style={{ display:"flex", flexDirection:"column", gap:"12px" }}>
                <div style={{ textAlign:"center", padding:"8px 0 4px" }}>
                  <div style={{ width:48, height:48, borderRadius:"14px", background:"linear-gradient(135deg,"+t.brand+"20,"+t.brandDark+"10)", border:"1px solid "+t.brand+"30", display:"flex", alignItems:"center", justifyContent:"center", margin:"0 auto 10px" }}>
                    <svg style={{ width:24, height:24 }} fill="none" viewBox="0 0 24 24" stroke={t.brand} strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2"/>
                    </svg>
                  </div>
                  <div style={{ fontFamily:"'Outfit',sans-serif", fontWeight:700, fontSize:"13px", color:t.textPrimary }}>Ask about your wards</div>
                  <div style={{ fontFamily:"'Outfit',sans-serif", fontSize:"11px", color:t.textMuted, marginTop:"3px" }}>Full visibility across all patients and pathways</div>
                </div>
                <div style={{ display:"flex", flexDirection:"column", gap:"6px" }}>
                  {SUGGESTED.map(s => (
                    <button key={s} onClick={() => send(s)} style={{
                      textAlign:"left", padding:"9px 12px",
                      borderRadius:"10px",
                      background:t.surfaceHigh,
                      border:"1px solid "+t.border,
                      fontFamily:"'Outfit',sans-serif", fontSize:"12px",
                      color:t.textSecond,
                      cursor:"pointer",
                      transition:"all 0.15s",
                      lineHeight:1.4,
                    }}
                    onMouseEnter={e => { e.currentTarget.style.borderColor = t.brand+"60"; e.currentTarget.style.color = t.brand; e.currentTarget.style.background = t.brandGlow; }}
                    onMouseLeave={e => { e.currentTarget.style.borderColor = t.border; e.currentTarget.style.color = t.textSecond; e.currentTarget.style.background = t.surfaceHigh; }}
                    >{s}</button>
                  ))}
                </div>
              </div>
            ) : (
              messages.map((msg, i) => <Message key={i} msg={msg} t={t}/>)
            )}
            {loading && <TypingIndicator t={t}/>}
            {error && (
              <div style={{ padding:"10px 12px", borderRadius:"10px", background:t.redBg, border:"1px solid "+t.redBorder, fontFamily:"'Outfit',sans-serif", fontSize:"12px", color:t.red }}>
                {error}
              </div>
            )}
            <div ref={bottomRef}/>
          </div>

          {/* Input */}
          <div style={{ borderTop:"1px solid "+t.border, padding:"12px 14px", flexShrink:0, background:t.surface }}>
            <div style={{ display:"flex", alignItems:"flex-end", gap:"8px" }}>
              <textarea
                ref={inputRef}
                rows={1}
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKey}
                placeholder="Ask about wards, patients, escalations…"
                style={{
                  flex:1, resize:"none",
                  fontFamily:"'Outfit',sans-serif", fontSize:"13px",
                  color:t.textPrimary,
                  background:t.surfaceHigh,
                  border:"1px solid "+t.border,
                  borderRadius:"10px",
                  padding:"9px 12px",
                  outline:"none",
                  maxHeight:"80px",
                  overflowY:"auto",
                  lineHeight:1.5,
                  transition:"border-color 0.15s",
                }}
                onFocus={e => e.target.style.borderColor = t.brand+"80"}
                onBlur={e => e.target.style.borderColor = t.border}
              />
              <button
                onClick={() => send()}
                disabled={!input.trim() || loading}
                style={{
                  width:36, height:36, borderRadius:"10px", border:"none",
                  background: input.trim() && !loading
                    ? "linear-gradient(135deg,"+t.brand+","+t.brandDark+")"
                    : t.surfaceHigh,
                  cursor: input.trim() && !loading ? "pointer" : "not-allowed",
                  display:"flex", alignItems:"center", justifyContent:"center",
                  flexShrink:0,
                  transition:"all 0.15s",
                  opacity: input.trim() && !loading ? 1 : 0.4,
                  boxShadow: input.trim() && !loading ? "0 4px 12px "+t.brand+"40" : "none",
                }}
              >
                <svg style={{ width:15, height:15 }} fill="none" viewBox="0 0 24 24" stroke={input.trim() && !loading ? "#fff" : t.textMuted} strokeWidth={2.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"/>
                </svg>
              </button>
            </div>
            <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.textMuted, marginTop:"6px", textAlign:"center", letterSpacing:"0.5px" }}>
              ENTER TO SEND · SHIFT+ENTER FOR NEW LINE
            </div>
          </div>
        </div>
      )}

      <style>{`
        @keyframes chatSlideUp {
          from { opacity:0; transform:translateY(10px) scale(0.98); }
          to   { opacity:1; transform:translateY(0) scale(1); }
        }
        @keyframes bounce {
          0%,80%,100% { transform:translateY(0); }
          40%          { transform:translateY(-5px); }
        }
      `}</style>
    </>
  );
}

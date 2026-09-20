const $ = id => document.getElementById(id);
let conversationId = localStorage.getItem("acos-conversation-id");
let incognito = localStorage.getItem("acos-incognito") === "true";
const safe = value => typeof value === "string" ? value : value == null ? "" : JSON.stringify(value);
async function api(path, options = {}) {
  const response = await fetch(path, { headers: {"Content-Type":"application/json", ...(options.headers || {})}, ...options });
  if (!response.ok) throw new Error(`Request unavailable (${response.status})`);
  try { return await response.json(); } catch (_) { return {}; }
}
const blockedTerms = /\b(kill|murder|assassinate|poison|strangle|shoot|bomb|weapon|explosive|ransomware|keylogger|steal passwords|botnet|suicide|self[- ]harm|kill myself|hurt myself)\b/i;
function offlineReply(text) {
  if (blockedTerms.test(text)) return "I can’t help with instructions that could enable serious harm, weapons, self-harm, malware, or bypassing safeguards. I can help with prevention, safety, emergency response, or a high-level explanation instead.";
  return `Local offline advisory: I received “${text}”. I can help separate definitions, assumptions, evidence, uncertainty, and a bounded next step. The hosted preview has no connected AI backend, so this response is a safe local simulation rather than web-grounded advice.`;
}
function addMessage(text, role = "acos") {
  const node = document.createElement("div"); node.className = `message ${role}`; node.textContent = safe(text);
  $("messages").appendChild(node); $("messages").scrollTop = $("messages").scrollHeight;
}
function formatResponse(data) {
  data = data && typeof data === "object" ? data : {};
  let out = safe(data.reply) || "No response was returned. Please try again.";
  if (data.route) out += `\n\nRoute: ${safe(data.route)}`;
  const plan = data.data && data.data.plan;
  if (Array.isArray(plan)) out += "\n\n" + plan.map((x,i) => `${i + 1}. ${safe(x && (x.action || x.phase) || x)}`).join("\n");
  if (data.data && data.data.simulation_boundary) out += `\n\nNote: ${safe(data.data.simulation_boundary)}`;
  return out;
}
function applyPrivacy() {
  $("privacyMode").checked = incognito; $("privacyNote").classList.toggle("hidden", !incognito);
  if (incognito) { conversationId = null; $("conversationTitle").textContent = "Ephemeral conversation"; $("conversationList").replaceChildren(); }
}
async function restore() {
  if (incognito) { $("messages").replaceChildren(); return; }
  try {
    if (!conversationId) { const created = await api("/api/conversations",{method:"POST",body:"{}"}); conversationId=created.id; localStorage.setItem("acos-conversation-id",conversationId); }
    const meta = await api(`/api/conversations/${encodeURIComponent(conversationId)}/metadata`);
    $("conversationTitle").textContent = safe(meta.title) || "Conversation";
    const history = await api(`/api/conversations/${encodeURIComponent(conversationId)}?limit=40`);
    $("messages").replaceChildren(); (Array.isArray(history) ? history : []).forEach(item => addMessage(item.content, item.role === "user" ? "user" : "acos"));
    await refreshConversations();
  } catch (_) { conversationId = null; localStorage.removeItem("acos-conversation-id"); $("conversationTitle").textContent="New conversation"; }
}
async function refreshConversations() {
  if (incognito) return;
  const items = await api("/api/conversations"); $("conversationList").replaceChildren();
  (Array.isArray(items) ? items : []).forEach(item => { const li=document.createElement("li"); li.textContent=`${safe(item.title)||"Conversation"} · ${item.message_count||0}`; li.className=item.id===conversationId?"active":""; li.onclick=async()=>{conversationId=item.id;localStorage.setItem("acos-conversation-id",conversationId);await restore()}; $("conversationList").appendChild(li); });
}
async function refreshContext() {
  try {
    const [health,status,workspace,model,topology] = await Promise.all([api("/api/health"),api("/api/status"),api("/api/workspace"),api("/api/model/status"),api("/api/compute/topology")]);
    $("healthText").textContent=health.ok?"online":"offline"; $("health").style.background=health.ok?"#55d69a":"#d66b6b";
    $("attention").textContent=safe(workspace.attention)||"Waiting for a goal"; $("goal").textContent=workspace.active_goal?`Goal: ${safe(workspace.active_goal)}`:"No active goal";
    $("compute").textContent=`${Array.isArray(topology)?topology.filter(x=>x.available).length:0} backends ready`; $("model").textContent=`${safe(model.provider)||"mock"} · advisory output`;
    void status;
  } catch (_) { $("healthText").textContent="local preview"; }
}
async function send(text) {
  addMessage(text,"user");
  const sendButton = document.querySelector(".send"); sendButton.disabled = true;
  try { const body={text,context:{modalities:["text"],client:"local-pwa",incognito}}; if (!incognito) body.conversation_id=conversationId; const data=await api("/api/message",{method:"POST",body:JSON.stringify(body)}); addMessage(formatResponse(data)); if (!incognito) await refreshConversations(); await refreshContext(); }
  catch (_) {
    addMessage(offlineReply(text));
  }
  finally { sendButton.disabled = false; }
}
$("privacyMode").onchange=async e=>{incognito=e.target.checked; localStorage.setItem("acos-incognito",String(incognito)); if(incognito){conversationId=null;localStorage.removeItem("acos-conversation-id");} applyPrivacy(); await restore();};
$("chatForm").onsubmit=e=>{e.preventDefault();const text=$("prompt").value.trim();if(text){$("prompt").value="";send(text)}};$("expression").onclick=()=>$("prompt").focus();
document.querySelectorAll("[data-prompt]").forEach(b=>b.onclick=()=>send(b.dataset.prompt));
$("newChat").onclick=async()=>{if(incognito){$("messages").replaceChildren();return}const x=await api("/api/conversations",{method:"POST",body:"{}"});conversationId=x.id;localStorage.setItem("acos-conversation-id",conversationId);await restore()};
$("clearHistory").onclick=()=>{localStorage.removeItem("acos-conversation-id");conversationId=null;restore()};
$("renameChat").onclick=async()=>{if(incognito||!conversationId)return;const title=prompt("Conversation title",$("conversationTitle").textContent);if(title&&title.trim()){try{const x=await api(`/api/conversations/${conversationId}`,{method:"PATCH",body:JSON.stringify({title:title.trim()})});$("conversationTitle").textContent=safe(x.title);await refreshConversations()}catch(_){}}};
$("searchForm").onsubmit=async e=>{e.preventDefault();const query=$("searchQuery").value.trim();if(!query)return;$("searchResult").textContent="Searching local fallback…";try{const x=await api("/api/search",{method:"POST",body:JSON.stringify({query,network:false})});$("searchResult").textContent=safe(x.notice)+" "+((x.results||[]).map(r=>safe(r.title)+" · "+safe(r.url)).join(" "));}catch(_){$("searchResult").textContent="Search unavailable; no network request was made."}};
document.querySelectorAll('a[href^="#"]').forEach(link=>link.addEventListener("click",()=>document.querySelectorAll(".nav-links a").forEach(item=>item.classList.toggle("active",item===link))));
applyPrivacy(); Promise.all([restore(),refreshContext()]);

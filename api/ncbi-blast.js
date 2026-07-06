// Vercel Edge Function: NCBI BLAST Proxy
// Submits queries via NCBI BLAST CGI and parses XML results into JSON
export const config = { runtime: "edge" };

const NCBI_URL = "https://blast.ncbi.nlm.nih.gov/Blast.cgi";
const USER_AGENT = "VigyanLLM/1.0 (contact@vigyanllm.in)";

async function submitBlast(seq, db, org) {
  const params = new URLSearchParams();
  params.set("CMD", "Put");
  params.set("PROGRAM", "blastn");
  params.set("DATABASE", db || "nt");
  params.set("QUERY", ">query\n" + seq);
  params.set("HITLIST_SIZE", "50");
  params.set("FORMAT_TYPE", "XML");
  params.set("EMAIL", "contact@vigyanllm.in");
  params.set("TOOL", "VigyanLLM");
  if (org) params.set("EQ_QUERY", org + "[ORGN]");

  const resp = await fetch(NCBI_URL, {
    method: "POST",
    headers: { "User-Agent": USER_AGENT, "Content-Type": "application/x-www-form-urlencoded" },
    body: params.toString(),
  });
  const html = await resp.text();
  const rid = (html.match(/RID\s*=\s*(\S+)/) || [])[1];
  const rtoe = (html.match(/RTOE\s*=\s*(\d+)/) || [])[1];
  if (!rid) throw new Error("NCBI did not return a request ID");
  return { rid, rtoe: parseInt(rtoe || "30") };
}

function extractTag(xml, tag) {
  const m = xml.match(new RegExp("<" + tag + ">([^<]*)<\\/" + tag + ">"));
  return m ? m[1].replace(/&amp;/g,"&").replace(/&lt;/g,"<").replace(/&gt;/g,">").replace(/&quot;/g,'"').replace(/&#39;/g,"'") : "";
}

async function pollBlast(rid) {
  const url = NCBI_URL + "?CMD=Get&FORMAT_TYPE=XML&RID=" + encodeURIComponent(rid);
  const resp = await fetch(url, { headers: { "User-Agent": USER_AGENT } });
  const text = await resp.text();
  if (text.startsWith("<!DOCTYPE") || text.startsWith("<html") || text.startsWith("<!")) {
    if (text.includes("No hits found") || text.includes("There are no more hits")) {
      return { status: "READY", hits: [] };
    }
    return { status: "WAITING" };
  }
  const hits = [];
  const hitRegex = /<Hit>([\s\S]*?)<\/Hit>/g;
  let m;
  while ((m = hitRegex.exec(text)) !== null) {
    const h = m[1];
    const id = extractTag(h, "Hit_id");
    const def = extractTag(h, "Hit_def");
    const accession = extractTag(h, "Hit_accession");
    const hitLen = parseInt(extractTag(h, "Hit_len") || "0");
    const hsps = [];
    const hspRegex = /<Hsp>([\s\S]*?)<\/Hsp>/g;
    let hm;
    while ((hm = hspRegex.exec(h)) !== null) {
      const s = hm[1];
      hsps.push({
        identity: parseInt(extractTag(s, "Hsp_identity") || "0"),
        gaps: parseInt(extractTag(s, "Hsp_gaps") || "0"),
        align_len: parseInt(extractTag(s, "Hsp_align-len") || "0"),
        bit_score: parseFloat(extractTag(s, "Hsp_bit-score") || "0"),
        evalue: extractTag(s, "Hsp_evalue") || "",
        hit_seq: extractTag(s, "Hsp_hit-seq") || "",
        midline: extractTag(s, "Hsp_midline") || "",
      });
    }
    hits.push({ id, def, accession, len: hitLen, hsps });
  }
  return { status: "READY", hits };
}

export default async function handler(request) {
  const url = new URL(request.url);
  if (request.method === "POST") {
    try {
      const body = await request.json();
      const { sequence, database, organism } = body;
      if (!sequence) return new Response(JSON.stringify({ error: "Missing sequence" }), { status: 400, headers: { "Content-Type": "application/json" } });
      const result = await submitBlast(sequence, database, organism);
      return new Response(JSON.stringify({ rid: result.rid, rtoe: result.rtoe }), { headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" } });
    } catch (e) {
      return new Response(JSON.stringify({ error: e.message }), { status: 502, headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" } });
    }
  }
  if (request.method === "GET" && url.searchParams.has("rid")) {
    try {
      const result = await pollBlast(url.searchParams.get("rid"));
      return new Response(JSON.stringify(result), { headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" } });
    } catch (e) {
      return new Response(JSON.stringify({ error: e.message }), { status: 502, headers: { "Content-Type": "application/json" } });
    }
  }
  return new Response(JSON.stringify({ error: "Method not allowed" }), { status: 405, headers: { "Content-Type": "application/json" } });
}

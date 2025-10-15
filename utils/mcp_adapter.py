# utils/mcp_adapter.py
import time
import requests
from cachetools import TTLCache, cached
from typing import Dict

_cache = TTLCache(maxsize=200, ttl=300)

def _shorten(text: str, max_chars: int = 500) -> str:
    if not text:
        return ""
    return text if len(text) <= max_chars else text[:max_chars].rsplit(" ", 1)[0] + "..."

@cached(_cache)
def fetch_external_context(query: str, provider: str = "mock", limit: int = 3, api_key: str = None) -> Dict:
    start = time.time()
    q = (query or "").strip()
    if not q:
        return {"summary": "", "source": provider, "raw": None, "elapsed": 0.0}

    if provider == "mock":
        kb = {
            "fever": "Fever is a temporary increase in body temperature often caused by infection. Check duration, associated symptoms (chills, rash, shortness of breath). If >3 days or >39°C, seek urgent care.",
            "chest pain": "Chest pain can be cardiac or non-cardiac. Red flags: sweating, radiating pain, shortness of breath, syncope. If present, call emergency services.",
            "cough": "Cough may be viral or bacterial; productive cough with green sputum suggests possible bacterial infection. Consider imaging if cough >2 weeks or hemoptysis.",
            "headache": "Headaches are common; red flags include sudden severe onset, focal neurology, or altered consciousness."
        }
        lower = q.lower()
        for k, v in kb.items():
            if k in lower:
                summary = v
                break
        else:
            summary = "No immediate high-confidence match in mock KB. Consider further literature search."
        elapsed = round(time.time() - start, 3)
        return {"summary": _shorten(summary), "source": "mock", "raw": summary, "elapsed": elapsed}

    elif provider == "pubmed":
        try:
            esearch = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
            params = {"db": "pubmed", "term": q, "retmax": limit, "retmode": "json"}
            r = requests.get(esearch, params=params, timeout=6)
            r.raise_for_status()
            ids = r.json().get("esearchresult", {}).get("idlist", [])
            if not ids:
                return {"summary": "No PubMed results found.", "source": "pubmed", "raw": None, "ids": [], "elapsed": round(time.time()-start,3)}
            efetch = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
            efetch_params = {"db": "pubmed", "id": ",".join(ids), "retmode": "xml"}
            r2 = requests.get(efetch, params=efetch_params, timeout=8)
            raw_xml = r2.text[:4000]
            summary = f"Fetched {len(ids)} PubMed records (raw xml truncated)."
            return {"summary": _shorten(summary), "source": "pubmed", "raw": raw_xml, "ids": ids, "elapsed": round(time.time()-start,3)}
        except Exception as e:
            return {"summary": f"PubMed fetch error: {e}", "source": "pubmed", "raw": None, "elapsed": round(time.time()-start,3)}

    elif provider == "openfda":
        try:
            base = "https://api.fda.gov/drug/label.json"
            params = {"search": q, "limit": 1}
            r = requests.get(base, params=params, timeout=6)
            r.raise_for_status()
            j = r.json()
            results = j.get("results", [])
            if results:
                snippet_list = results[0].get("indications_and_usage") or results[0].get("warnings") or []
                snippet = snippet_list[0] if snippet_list else "OpenFDA returned results but no snippet available."
                return {"summary": _shorten(snippet), "source": "openfda", "raw": results[0], "elapsed": round(time.time()-start,3)}
            else:
                return {"summary": "No OpenFDA results.", "source": "openfda", "raw": j, "elapsed": round(time.time()-start,3)}
        except Exception as e:
            return {"summary": f"OpenFDA fetch error: {e}", "source": "openfda", "raw": None, "elapsed": round(time.time()-start,3)}

    elif provider == "wikipedia":
        try:
            url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + requests.utils.quote(q)
            r = requests.get(url, timeout=5)
            if r.status_code == 200:
                j = r.json()
                summary = j.get("extract") or j.get("description") or ""
                return {"summary": _shorten(summary), "source": "wikipedia", "raw": j, "elapsed": round(time.time()-start,3)}
            else:
                return {"summary": "Wikipedia page not found.", "source": "wikipedia", "raw": r.text, "elapsed": round(time.time()-start,3)}
        except Exception as e:
            return {"summary": f"Wikipedia fetch error: {e}", "source": "wikipedia", "raw": None, "elapsed": round(time.time()-start,3)}

    else:
        return {"summary": f"Provider '{provider}' not implemented.", "source": provider, "raw": None, "elapsed": round(time.time()-start,3)}

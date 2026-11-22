"""Remote Print 1.9.0: "Add the card" - puts the printer mini card + its two popups on a dashboard (#11).

Uses the Home Assistant websocket through the Supervisor (homeassistant_api: true). Only administrators can call it
(checked in app.py). The cards come from dashboard_card.json (= examples/printer_card_popup.yaml) with the printer
sensors, the ink style and the ingress address filled in. A copy of the dashboard is saved in /data before changing it.
"""
import copy
import json
import os
import re
import time

import aiohttp

WS = "http://supervisor/core/websocket"
HERE = os.path.dirname(os.path.abspath(__file__))
POPUP_IDS = ("rp_printer", "rp_printer_carica")
INK_RX = re.compile(r"(ink|toner|cartridge|cartuccia|inchiostro)", re.I)
COLOUR_RX = re.compile(r"(photo_?black|black|cyan|magenta|yellow|light_?cyan|light_?magenta|grey|gray|red|blue|green|"
                       r"tri_?colou?r|colou?r|nero|ciano|azzurro|giallo)", re.I)
IT = {"UPLOAD FILE AND PRINT": "CARICA FILE E STAMPA",
      "tap · pick a file on your phone, it prints at home": "tocca · scegli un file sul telefono, si stampa a casa",
      "Printer": "Stampante", "My printer": "Stampante"}
# 1.9.1: texts inside the card templates (JavaScript strings), Italian when Home Assistant / the add-on is in Italian
JS_IT = {"Off": "Spenta", "Printing…": "In stampa…", "Power saving: wakes up by itself": "Risparmio energetico: si sveglia da sola",
         "Ready to print": "Pronta per stampare", "OFF": "SPENTA", "PRINTING…": "IN STAMPA…", "PRINTING": "IN STAMPA",
         "SLEEP": "RIPOSO", "READY": "PRONTA", "Almost empty: ": "Quasi finito: ", "Low: ": "In esaurimento: ",
         " · order a new one": " · ordinane uno nuovo", "All supplies OK": "Tutto a posto", "Pages left": "Pagine rimaste",
         "toner estimate": "stima del toner", "Printed": "Stampate", "with this toner": "con questo toner", "Scans": "Scansioni",
         "from the glass": "dal vetro", "Misfeeds": "Prese mancate", "sheets not picked": "fogli non presi",
         "Toner made": "Toner prodotto", "cartridge production date": "data di produzione",
         "Ink / toner levels": "Livelli inchiostro / toner", "Ink / toner": "Inchiostro / toner", "My printer": "Stampante"}


class Ha:
    """Minimal Home Assistant websocket client."""

    def __init__(self):
        self.n = 0

    async def __aenter__(self):
        self.s = aiohttp.ClientSession()
        self.ws = await self.s.ws_connect(WS, timeout=20)
        await self.ws.receive_json()
        await self.ws.send_json({"type": "auth", "access_token": os.environ.get("SUPERVISOR_TOKEN", "")})
        r = await self.ws.receive_json()
        if r.get("type") != "auth_ok":
            raise RuntimeError("Home Assistant API not available (homeassistant_api)")
        return self

    async def __aexit__(self, *a):
        await self.ws.close()
        await self.s.close()

    async def call(self, msg):
        self.n += 1
        await self.ws.send_json(dict(msg, id=self.n))
        while True:
            r = await self.ws.receive_json()
            if r.get("id") == self.n:
                return r


def guess_printer(states, ink_sensors):
    """prefix / status / name of the printer from the IPP (or HP) sensors."""
    ids = {s["entity_id"]: s for s in states}
    inks = [s for s in states if s["entity_id"].startswith("sensor.") and INK_RX.search(s["entity_id"])
            and s.get("attributes", {}).get("unit_of_measurement") == "%"]
    if ink_sensors:
        inks = [ids[e] for e in ink_sensors if e in ids] or inks
    for s in inks:
        e = s["entity_id"]
        m = COLOUR_RX.search(e.split(".", 1)[1])
        prefix = e[:e.index(m.group(0), 7)] if m else e.rsplit("_", 2)[0] + "_"
        if not prefix.endswith("_"):
            prefix += "_"
        for st in (prefix.rstrip("_"), prefix + "status", prefix + "state"):
            if st in ids:
                name = ids[st].get("attributes", {}).get("friendly_name") or st
                name = re.sub(r"\s*(status|stato)$", "", name, flags=re.I)
                name = re.sub(r"\s*\([^)]*\)\s*$", "", name) or name   # 1.9.1: "HP LaserJet (192.168.1.5)" -> "HP LaserJet"
                return {"prefix": prefix, "status": st, "name": name}
        return {"prefix": prefix, "status": prefix + "status", "name": "Printer"}
    return None


def build_cards(pr, style, ink_sensors, ingress, lang):
    tpl = json.load(open(os.path.join(HERE, "dashboard_card.json"), encoding="utf-8"))

    def fix(o):
        if isinstance(o, dict):
            for k, v in list(o.items()):
                if k == "variables" and isinstance(v, dict) and "prefix" in v:
                    v.update(prefix=pr["prefix"], status=pr["status"], name=pr["name"], style=style)
                    v["inks"] = list(ink_sensors)
                elif isinstance(v, str):
                    v = v.replace("sensor.YOUR_PRINTER_status", pr["status"]).replace("sensor.YOUR_PRINTER_", pr["prefix"])
                    v = v.replace("/api/hassio_ingress/YOUR_INGRESS_TOKEN/", ingress)
                    if lang == "it" and k in ("name", "label", "title") and v in IT:
                        v = IT[v]
                    if lang == "it" and "[[[" in v:
                        for en, it in JS_IT.items():
                            v = v.replace("'" + en + "'", "'" + it + "'")
                    o[k] = v
                else:
                    fix(v)
        elif isinstance(o, list):
            for x in o:
                fix(x)
        return o

    return fix(copy.deepcopy(tpl["mini"])), [fix(copy.deepcopy(p)) for p in tpl["popups"]]


def has_ours(cfg):
    t = json.dumps(cfg)
    return any(f'"popup_card_id": "{p}"' in t for p in POPUP_IDS)


async def dashboards():
    async with Ha() as ha:
        r = await ha.call({"type": "lovelace/dashboards/list"})
        out = [{"url_path": None, "title": "Overview / Panoramica"}]
        out += [{"url_path": d["url_path"], "title": d.get("title") or d["url_path"]}
                for d in (r.get("result") or []) if d.get("mode", "storage") == "storage"]
        res = await ha.call({"type": "lovelace/resources"})
        urls = " ".join(x.get("url", "") for x in (res.get("result") or []))
        sv = await ha.call({"type": "get_services"})
        missing = [n for n, ok in (("button-card", "button-card" in urls),
                                   ("browser_mod", "browser_mod" in (sv.get("result") or {})),
                                   ("card-mod", "card-mod" in urls)) if not ok]
        return {"dashboards": out, "missing": missing}


async def add_card(url_path, style, ink_sensors, ingress, lang):
    async with Ha() as ha:
        r = await ha.call({"type": "lovelace/config", "url_path": url_path})
        if not r.get("success"):
            return {"ok": False, "why": "auto"}          # Overview still generated by Home Assistant
        cfg = r["result"]
        if has_ours(cfg):
            return {"ok": False, "why": "exists"}
        views = cfg.get("views") or []
        if not views:
            return {"ok": False, "why": "noview"}
        st = await ha.call({"type": "get_states"})
        pr = guess_printer(st.get("result") or [], ink_sensors)
        if not pr:
            return {"ok": False, "why": "noprinter"}
        mini, popups = build_cards(pr, style, ink_sensors, ingress, lang)
        v = views[0]
        if v.get("type") == "sections" or "sections" in v:
            v.setdefault("sections", []).append({"type": "grid", "cards": [
                {"type": "heading", "heading": "Stampante" if lang == "it" else "Printer", "icon": "mdi:printer"}, mini] + popups})
        elif v.get("type") in (None, "masonry"):
            mini.pop("section_mode", None)
            mini.pop("grid_options", None)
            v.setdefault("cards", []).extend([mini] + popups)
        else:
            return {"ok": False, "why": "view"}
        os.makedirs("/data/dashboard_backups", exist_ok=True)
        bk = f"/data/dashboard_backups/{url_path or 'lovelace'}_{time.strftime('%Y%m%d_%H%M%S')}.json"
        json.dump(r["result"], open(bk, "w", encoding="utf-8"), ensure_ascii=False)
        s = await ha.call({"type": "lovelace/config/save", "url_path": url_path, "config": cfg})
        if not s.get("success"):
            return {"ok": False, "why": "save", "detail": str(s.get("error", ""))[:200]}
        print(f"[card] added to dashboard '{url_path or 'lovelace'}' view '{v.get('title') or v.get('path') or 0}' "
              f"(printer {pr['status']}), backup {bk}", flush=True)
        return {"ok": True, "printer": pr, "view": v.get("title") or v.get("path") or "1"}

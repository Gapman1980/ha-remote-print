"""Remote Print - Home Assistant add-on.

Upload a file from your phone (through Home Assistant ingress, so it also works away from home)
and print it on a network printer. CUPS creates a driverless queue (IPP Everywhere / AirPrint),
so PDF, photos (JPG/PNG/HEIC) and text are converted to whatever the printer accepts.
"""
import asyncio
import ipaddress
import json
import os
import re
import time

from aiohttp import web

OPTIONS_FILE = "/data/options.json"
QUEUE = "RemotePrint"
UPLOADS = "/data/uploads"
JOBS_FILE = "/data/jobs.json"
INGRESS_IP = "172.30.32.2"   # only Home Assistant ingress may talk to this server
EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".gif", ".tif", ".tiff", ".heic", ".heif", ".txt"}
MIME_EXT = {"application/pdf": ".pdf", "image/jpeg": ".jpg", "image/png": ".png", "image/gif": ".gif", "image/tiff": ".tif",
            "image/heic": ".heic", "image/heif": ".heif", "text/plain": ".txt"}
PAPER = {"A4": "iso_a4_210x297mm", "A5": "iso_a5_148x210mm", "Letter": "na_letter_8.5x11in", "Legal": "na_legal_8.5x14in"}

MSG = {
    "it": {"format": "Formato {} non supportato: usa PDF, foto o testo", "nofile": "Nessun file ricevuto",
           "heic": "Non riesco a convertire la foto HEIC", "offline": "Stampante non raggiungibile: è accesa? ",
           "noairprint": "Stampante non raggiungibile oppure senza AirPrint / IPP Everywhere. Controlla printer_uri; "
                         "se è una Brother laser senza AirPrint usa driver: brlaser con printer_uri socket://IP:9100. ",
           "model": "brother_model \"{}\" non trovato tra i driver brlaser. Scrivi nella Configurazione uno di questi "
                    "(se il tuo non c'è, scegli uno della stessa serie): {}"},
    "en": {"format": "Format {} not supported: use PDF, photos or text", "nofile": "No file received",
           "heic": "Could not convert the HEIC photo", "offline": "Printer not reachable: is it on? ",
           "noairprint": "Printer not reachable or without AirPrint / IPP Everywhere. Check printer_uri; "
                         "for a Brother laser without AirPrint use driver: brlaser with printer_uri socket://IP:9100. ",
           "model": "brother_model \"{}\" matches no brlaser driver. Put one of these in the Configuration "
                    "(if yours is missing, pick one of the same series): {}"},
}


def options():
    try:
        return json.load(open(OPTIONS_FILE))
    except Exception:
        return {}


OPT = options()
MEDIA = PAPER.get(OPT.get("paper", "A4"), "iso_a4_210x297mm")
KEEP_DAYS = int(OPT.get("keep_days", 3))
LAN_ACCESS = bool(OPT.get("lan_access", False))   # direct access on the add-on port (Network section), local network only


def clean_model(v):
    return re.sub(r"(?i)^\s*brother_?model\s*:\s*", "", str(v or "DCP-1600")).strip(" \"'")


def host_of(uri):
    m = re.search(r"://([^/:]+)", str(uri or ""))
    return m.group(1) if m else ""


# 1.3.0: main printer (top-level options, queue RemotePrint) + optional other_printers (queues RemotePrint2, 3 ...)
PRINTERS = [{"queue": "RemotePrint", "name": (OPT.get("printer_name") or "").strip() or host_of(OPT.get("printer_uri")) or "Printer",
             "driver": OPT.get("driver", "driverless"), "model": clean_model(OPT.get("brother_model"))}]
for i, p in enumerate(OPT.get("other_printers") or [], start=2):
    PRINTERS.append({"queue": f"RemotePrint{i}", "name": (p.get("name") or "").strip() or host_of(p.get("printer_uri")) or f"Printer {i}",
                     "driver": p.get("driver", "driverless"), "model": clean_model(p.get("brother_model"))})
QUEUE_RE = r"(RemotePrint\d*)-(\d+)"
CONFIG_JS = json.dumps({"lang": OPT.get("language", "auto"), "paper": OPT.get("paper", "A4"),
                        "duplex": bool(OPT.get("duplex_default", False)), "printers": [p["name"] for p in PRINTERS]})


def printer(i):
    try:
        return int(i), PRINTERS[int(i)]
    except (ValueError, TypeError, IndexError):
        return 0, PRINTERS[0]


async def run(*cmd, timeout=60):
    p = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
    try:
        out, _ = await asyncio.wait_for(p.communicate(), timeout)
    except asyncio.TimeoutError:
        p.kill()
        return 1, "timeout"
    return p.returncode, out.decode(errors="replace")


async def ensure_queue(idx):
    q = PRINTERS[idx]["queue"]
    rc, _ = await run("lpstat", "-p", q)
    if rc == 0:
        return True, ""
    last = ""
    # Keep the whole wait short: the upload request is still open and remote proxies drop it after ~1 minute.
    # run.sh already created the queue at start-up, so this only matters if the printer was off back then.
    for wait in (35, 15):   # printers in power-save mode sometimes answer slowly the first time
        rc, last = await run("/queue.sh", str(idx), timeout=wait)   # driverless or brlaser, from the options
        if rc == 2:   # brother_model matches no brlaser driver: retrying is pointless, list the models
            models = [re.sub(r"^Brother |( series)?, using brlaser.*$", "", l.strip())
                      for l in last.splitlines() if l.startswith("  ")]
            return False, "model:" + ", ".join(models)
        if rc == 0:
            await run("cupsenable", q)
            await run("cupsaccept", q)
            return True, ""
        await asyncio.sleep(2)
    return False, last.strip()[-200:]


IMAGES = (".jpg", ".jpeg", ".png", ".gif", ".tif", ".tiff")


def image_to_pdf(path):
    """Photo -> one-page PDF. With a JPG the printer often decodes it itself ("DirectJPEG") and some models fail on
    modern phone photos (Ultra HDR gain map, progressive, huge EXIF). A PDF is rendered by CUPS/Ghostscript instead.
    Also applies the EXIF rotation and shrinks huge photos (200 MP phones) to 300 dpi on A4."""
    from PIL import Image, ImageOps
    with Image.open(path) as src:
        src.draft("RGB", (4000, 4000))          # fast JPEG downscale while decoding
        im = ImageOps.exif_transpose(src)        # also loads only the first frame of GIF/TIFF
        im.thumbnail((3600, 3600))
        if im.mode in ("RGBA", "LA", "P", "PA"):
            im = im.convert("RGBA")
            bg = Image.new("RGB", im.size, "white")
            bg.paste(im, mask=im.getchannel("A"))
            im = bg
        elif im.mode not in ("RGB", "L"):
            im = im.convert("RGB")
        w, h = im.size
        dpi = max(max(w, h) / 11.0, min(w, h) / 7.8, 72)   # page fits A4/Letter with margins, either orientation
        out = path.rsplit(".", 1)[0] + ".pdf"
        im.save(out, "PDF", resolution=dpi, quality=92)
    return out


def read_jobs():
    try:
        return json.load(open(JOBS_FILE))
    except Exception:
        return []


def write_jobs(jobs):
    json.dump(jobs[-30:], open(JOBS_FILE, "w"))


def cleanup_uploads():
    limit = time.time() - KEEP_DAYS * 86400
    for f in os.listdir(UPLOADS):
        p = os.path.join(UPLOADS, f)
        if os.path.getmtime(p) < limit:
            os.remove(p)


@web.middleware
async def ingress_only(request, handler):
    if request.remote != INGRESS_IP and not (LAN_ACCESS and is_local(request.remote)):
        return web.Response(status=403, text="Only through Home Assistant (or enable lan_access)")
    return await handler(request)


def is_local(ip):
    """lan_access: accept only private / local addresses, never the internet."""
    try:
        a = ipaddress.ip_address(ip or "")
        return a.is_private or a.is_loopback or a.is_link_local
    except ValueError:
        return False


async def page(request):
    html = open("/index.html", encoding="utf-8").read().replace("__CONFIG__", CONFIG_JS)
    return web.Response(text=html, content_type="text/html", headers={"Cache-Control": "no-store"})


async def print_file(request):
    cleanup_uploads()
    reader = await request.multipart()
    fields, name, path = {}, None, None
    async for part in reader:
        if part.name == "file" and part.filename:
            name = os.path.basename(part.filename)
            ext = os.path.splitext(name)[1].lower()
            if ext not in EXTENSIONS:   # Android file pickers sometimes give names without extension: use the MIME type
                ext = MIME_EXT.get((part.headers.get("Content-Type") or "").split(";")[0].strip().lower(), ext)
                if ext in EXTENSIONS:
                    name = (os.path.splitext(name)[0] or "file") + ext
            if ext not in EXTENSIONS:
                lang = fields.get("lang") if fields.get("lang") in MSG else "en"
                return web.json_response({"ok": False, "error": MSG[lang]["format"].format(ext or "?")})
            safe = re.sub(r"[^A-Za-z0-9._-]+", "_", name)[-80:]
            path = os.path.join(UPLOADS, f"{int(time.time())}_{safe}")
            with open(path, "wb") as f:
                while True:
                    chunk = await part.read_chunk(1 << 16)
                    if not chunk:
                        break
                    f.write(chunk)
        else:
            fields[part.name] = (await part.text()).strip()
    m = MSG[fields.get("lang") if fields.get("lang") in MSG else "en"]
    if not path:
        return web.json_response({"ok": False, "error": m["nofile"]})
    if path.lower().endswith((".heic", ".heif")):          # iPhone photos -> JPG
        jpg = path.rsplit(".", 1)[0] + ".jpg"
        rc, _ = await run("heif-convert", path, jpg)
        if rc != 0:
            return web.json_response({"ok": False, "error": m["heic"]})
        path = jpg
    if path.lower().endswith(IMAGES):
        try:
            path = await asyncio.to_thread(image_to_pdf, path)
        except Exception as e:   # keep the original photo: the printer may still manage it
            print(f"Photo -> PDF failed, sending the original: {e}", flush=True)
    idx, pr = printer(fields.get("printer", "0"))
    ok, err = await ensure_queue(idx)
    if not ok:
        tag = f"[{pr['name']}] " if len(PRINTERS) > 1 else ""
        if err.startswith("model:"):
            return web.json_response({"ok": False, "error": tag + m["model"].format(pr["model"], err[6:])})
        return web.json_response({"ok": False, "error": tag + (m["offline"] if pr["driver"] == "brlaser" else m["noairprint"]) + err})
    copies = max(1, min(20, int(fields.get("copies", "1") or 1)))
    opts = ["-d", pr["queue"], "-n", str(copies), "-t", name[:60], "-o", f"media={MEDIA}"]
    opts += ["-o", "sides=two-sided-long-edge" if fields.get("duplex") == "1" else "sides=one-sided"]
    if fields.get("fit", "1") == "1":
        opts += ["-o", "fit-to-page"]
    if fields.get("pages") and re.fullmatch(r"[0-9,\- ]+", fields["pages"]):
        opts += ["-o", "page-ranges=" + fields["pages"].replace(" ", "")]
    rc, out = await run("lp", *opts, path)
    job = re.search(QUEUE_RE, out)
    if rc != 0 or not job:
        return web.json_response({"ok": False, "error": "CUPS: " + out.strip()[-200:]})
    jid = int(job.group(2))   # CUPS job numbers are unique across all queues
    jobs_ = read_jobs()
    # CUPS restarts job numbers from 1 after an add-on restart/update: close older jobs with the same number
    for j in jobs_:
        if j["id"] == jid:
            j["closed"] = True
    jobs_.append({"id": jid, "name": name, "copies": copies, "time": time.time(), "canceled": False, "printer": pr["name"]})
    write_jobs(jobs_)
    return web.json_response({"ok": True, "id": jid})


async def jobs(request):
    _, pr = printer(request.query.get("printer", "0"))
    _, open_ = await run("lpstat", "-W", "not-completed", "-o")
    _, done = await run("lpstat", "-W", "completed", "-o")
    _, every = await run("lpstat", "-p")
    rc, state = await run("lpstat", "-l", "-p", pr["queue"])   # alerts of the printer chosen on the page
    op = {int(x[1]) for x in re.findall(rf"^{QUEUE_RE}", open_, re.M)}
    dn = {int(x[1]) for x in re.findall(rf"^{QUEUE_RE}", done, re.M)}
    now = {int(x[1]) for x in re.findall(rf"now printing {QUEUE_RE}", every)}
    out = []
    for j in reversed(read_jobs()[-15:]):
        if j.get("canceled"):
            s = "canceled"
        elif j.get("closed") or time.time() - j["time"] > 6 * 3600:
            s = "done"
        elif j["id"] in now:
            s = "printing"
        elif j["id"] in op:
            s = "queued"
        elif j["id"] in dn:
            s = "done"
        else:
            s = "done" if time.time() - j["time"] > 600 else "queued"
        out.append({**j, "state": s})
    alerts = re.search(r"Alerts:\s*(.*)", state)
    alerts = [a for a in (alerts.group(1).split() if alerts else []) if a != "none"]
    return web.json_response({"jobs": out, "alerts": alerts, "queue_ok": rc == 0 and "disabled" not in state})


async def cancel(request):
    jid = int(request.query.get("id", "0"))
    await run("cancel", str(jid))   # job number alone: works for every queue
    jobs_ = read_jobs()
    for j in jobs_:
        if j["id"] == jid:
            j["canceled"] = True
    write_jobs(jobs_)
    return web.json_response({"ok": True})


app = web.Application(middlewares=[ingress_only], client_max_size=80 * 1024 * 1024)
app.add_routes([web.get("/", page), web.post("/print", print_file), web.get("/jobs", jobs), web.post("/cancel", cancel)])

if __name__ == "__main__":
    os.makedirs(UPLOADS, exist_ok=True)
    web.run_app(app, host="0.0.0.0", port=8099)

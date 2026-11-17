"""Remote Print - Home Assistant add-on.

Upload a file from your phone (through Home Assistant ingress, so it also works away from home)
and print it on a network printer. CUPS creates a driverless queue (IPP Everywhere / AirPrint),
so PDF, photos (JPG/PNG/HEIC) and text are converted to whatever the printer accepts.
"""
import asyncio
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
PAPER = {"A4": "iso_a4_210x297mm", "A5": "iso_a5_148x210mm", "Letter": "na_letter_8.5x11in", "Legal": "na_legal_8.5x14in"}

MSG = {
    "it": {"format": "Formato {} non supportato: usa PDF, foto o testo", "nofile": "Nessun file ricevuto",
           "heic": "Non riesco a convertire la foto HEIC", "offline": "Stampante non raggiungibile: è accesa? "},
    "en": {"format": "Format {} not supported: use PDF, photos or text", "nofile": "No file received",
           "heic": "Could not convert the HEIC photo", "offline": "Printer not reachable: is it on? "},
}


def options():
    try:
        return json.load(open(OPTIONS_FILE))
    except Exception:
        return {}


OPT = options()
PRINTER_URI = OPT.get("printer_uri", "")
MEDIA = PAPER.get(OPT.get("paper", "A4"), "iso_a4_210x297mm")
KEEP_DAYS = int(OPT.get("keep_days", 3))
CONFIG_JS = json.dumps({"lang": OPT.get("language", "auto"), "paper": OPT.get("paper", "A4"),
                        "duplex": bool(OPT.get("duplex_default", False))})


async def run(*cmd, timeout=60):
    p = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
    try:
        out, _ = await asyncio.wait_for(p.communicate(), timeout)
    except asyncio.TimeoutError:
        p.kill()
        return 1, "timeout"
    return p.returncode, out.decode(errors="replace")


async def ensure_queue():
    rc, _ = await run("lpstat", "-p", QUEUE)
    if rc == 0:
        return True, ""
    last = ""
    for _ in range(3):   # printers in power-save mode sometimes answer slowly
        rc, last = await run("/queue.sh", timeout=90)   # driverless or brlaser, from the options
        if rc == 0:
            await run("cupsenable", QUEUE)
            await run("cupsaccept", QUEUE)
            return True, ""
        await asyncio.sleep(5)
    return False, last.strip()[-200:]


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
    if request.remote != INGRESS_IP:
        return web.Response(status=403, text="Only through Home Assistant")
    return await handler(request)


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
    ok, err = await ensure_queue()
    if not ok:
        return web.json_response({"ok": False, "error": m["offline"] + err})
    copies = max(1, min(20, int(fields.get("copies", "1") or 1)))
    opts = ["-d", QUEUE, "-n", str(copies), "-t", name[:60], "-o", f"media={MEDIA}"]
    opts += ["-o", "sides=two-sided-long-edge" if fields.get("duplex") == "1" else "sides=one-sided"]
    if fields.get("fit", "1") == "1":
        opts += ["-o", "fit-to-page"]
    if fields.get("pages") and re.fullmatch(r"[0-9,\- ]+", fields["pages"]):
        opts += ["-o", "page-ranges=" + fields["pages"].replace(" ", "")]
    rc, out = await run("lp", *opts, path)
    job = re.search(rf"{QUEUE}-(\d+)", out)
    if rc != 0 or not job:
        return web.json_response({"ok": False, "error": "CUPS: " + out.strip()[-200:]})
    jobs_ = read_jobs()
    # CUPS restarts job numbers from 1 after an add-on restart/update: close older jobs with the same number
    for j in jobs_:
        if j["id"] == int(job.group(1)):
            j["closed"] = True
    jobs_.append({"id": int(job.group(1)), "name": name, "copies": copies, "time": time.time(), "canceled": False})
    write_jobs(jobs_)
    return web.json_response({"ok": True, "id": int(job.group(1))})


async def jobs(request):
    _, open_ = await run("lpstat", "-W", "not-completed", "-o", QUEUE)
    _, done = await run("lpstat", "-W", "completed", "-o", QUEUE)
    rc, state = await run("lpstat", "-l", "-p", QUEUE)
    op = {int(x) for x in re.findall(rf"^{QUEUE}-(\d+)", open_, re.M)}
    dn = {int(x) for x in re.findall(rf"^{QUEUE}-(\d+)", done, re.M)}
    now = re.search(rf"now printing {QUEUE}-(\d+)", state)
    now = int(now.group(1)) if now else None
    out = []
    for j in reversed(read_jobs()[-15:]):
        if j.get("canceled"):
            s = "canceled"
        elif j.get("closed") or time.time() - j["time"] > 6 * 3600:
            s = "done"
        elif j["id"] == now:
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
    await run("cancel", f"{QUEUE}-{jid}")
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

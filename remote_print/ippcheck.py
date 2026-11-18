#!/usr/bin/env python3
"""Remote Print 1.5.1 - why was the driverless queue not created?

Called by queue.sh when `lpadmin -m everywhere` fails. Sends one read-only IPP Get-Printer-Attributes request
(nothing is printed) and writes in the add-on Log what the printer answered, in plain words:
TLS problems, HTTP 401 (IPP authentication), IPP status codes (forbidden, operation not supported ...),
or the document formats the printer offers when it answers fine.
Usage: ippcheck.py QUEUE PRINTER_URI
"""
import http.client
import socket
import ssl
import struct
import sys
import warnings
from urllib.parse import urlsplit

Q, URI = sys.argv[1], sys.argv[2]
warnings.simplefilter("ignore")   # old-TLS test uses deprecated settings on purpose
TIMEOUT = 8

STATUS = {
    0x0400: ("client-error-bad-request", "the printer did not understand the request: try another path (/ipp/print, /ipp, /ipp/printer)"),
    0x0401: ("client-error-forbidden", "the printer refuses to describe itself: in its web page allow IPP operations / Get-Printer-Attributes"),
    0x0402: ("client-error-not-authenticated", "IPP authentication is on: turn it off in the printer's web page (IPP settings)"),
    0x0403: ("client-error-not-authorized", "IPP access is restricted: in the printer's web page allow IPP from Home Assistant's address"),
    0x0406: ("client-error-not-found", "wrong path in printer_uri: try /ipp/print, /ipp or /ipp/printer"),
    0x0501: ("server-error-operation-not-supported", "IPP is disabled or limited on the printer: turn on IPP in its web page"),
    0x0503: ("server-error-version-not-supported", "the printer only speaks an old IPP version"),
}


def say(text):
    print(f"[{Q}] Printer check: {text}", flush=True)


def attr(tag, name, value):
    n, v = name.encode(), value.encode()
    return struct.pack(">BH", tag, len(n)) + n + struct.pack(">H", len(v)) + v


def request(version):
    body = struct.pack(">BBHI", version[0], version[1], 0x000B, 1) + b"\x01"
    body += attr(0x47, "attributes-charset", "utf-8") + attr(0x48, "attributes-natural-language", "en")
    body += attr(0x45, "printer-uri", URI)
    body += attr(0x44, "requested-attributes", "printer-make-and-model")
    body += attr(0x44, "", "document-format-supported")
    body += attr(0x44, "", "ipp-versions-supported")
    return body + b"\x03"


def parse(data):
    """-> status code, {name: [values]} (strings only, enough for a diagnosis)."""
    status = struct.unpack(">H", data[2:4])[0]
    out, i, name = {}, 8, None
    while i < len(data):
        tag = data[i]; i += 1
        if tag == 0x03:
            break
        if tag < 0x10:
            continue
        nl = struct.unpack(">H", data[i:i + 2])[0]; i += 2
        if nl:
            name = data[i:i + nl].decode(errors="replace")
        i += nl
        vl = struct.unpack(">H", data[i:i + 2])[0]; i += 2
        val = data[i:i + vl]; i += vl
        if name and tag >= 0x40:
            out.setdefault(name, []).append(val.decode(errors="replace"))
    return status, out


def tls_context(legacy):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE   # printers use self-signed certificates (CUPS accepts them too)
    if legacy:
        ctx.minimum_version = ssl.TLSVersion.TLSv1
        try:
            ctx.set_ciphers("DEFAULT:@SECLEVEL=0")
        except ssl.SSLError:
            pass
    return ctx


def ask(version, legacy=False):
    u = urlsplit(URI)
    port = u.port or 631
    path = u.path or "/"
    if u.scheme == "ipps":
        conn = http.client.HTTPSConnection(u.hostname, port, timeout=TIMEOUT, context=tls_context(legacy))
    else:
        conn = http.client.HTTPConnection(u.hostname, port, timeout=TIMEOUT)
    try:
        conn.request("POST", path, body=request(version), headers={"Content-Type": "application/ipp"})
        r = conn.getresponse()
        return r.status, r.reason, r.read()
    finally:
        conn.close()


def main():
    u = urlsplit(URI)
    if u.scheme not in ("ipp", "ipps") or not u.hostname:
        say(f"'{URI}' is not an IPP address: driverless needs ipp://PRINTER-IP/ipp/print (or ipps://)")
        return
    if u.port in (9100, 515):
        say(f"port {u.port} is raw/LPD printing, not IPP: remove ':{u.port}' (IPP uses 631)")
        return
    try:
        status, reason, data = ask((2, 0))
    except ssl.SSLError as e:
        try:
            ask((2, 0), legacy=True)
            say(f"encrypted connection fails ({e.reason or e}) but works with old TLS settings: the printer only offers "
                "old TLS versions/ciphers. Update its firmware or SSL/TLS settings, or use ipp:// instead of ipps://")
        except Exception:
            say(f"encrypted connection (ipps) failed ({e.reason or e}). Check the SSL/TLS settings in the printer's "
                "web page, or use ipp:// instead of ipps://")
        return
    except (ConnectionResetError, http.client.RemoteDisconnected) as e:
        say(f"the printer closed the connection ({type(e).__name__}). With ipps:// this usually means its SSL/TLS "
            "settings refuse Home Assistant; try ipp:// or check IPP/SSL in the printer's web page")
        return
    except ConnectionRefusedError:
        say(f"nothing answers on port {u.port or 631}: IPP is off on the printer or the port is wrong")
        return
    except (socket.timeout, TimeoutError):
        say("no answer within 8 s: printer off, asleep or wrong IP address")
        return
    except OSError as e:
        say(f"cannot reach the printer ({e.strerror or e})")
        return
    if status == 401:
        say("HTTP 401: the printer asks for a user and password for IPP. Turn off IPP authentication in its web page")
        return
    if status != 200:
        say(f"HTTP {status} {reason}: wrong path in printer_uri? Try /ipp/print, /ipp or /ipp/printer")
        return
    if len(data) < 8:
        say("empty IPP answer: wrong path in printer_uri? Try /ipp/print, /ipp or /ipp/printer")
        return
    code, attrs = parse(data)
    if code == 0x0503:
        try:
            _, _, data = ask((1, 1))
            code, attrs = parse(data)
        except Exception:
            pass
    if code >= 0x0400:
        name, hint = STATUS.get(code, (f"0x{code:04x}", "the printer refused the request"))
        say(f"IPP status {name}: {hint}")
        return
    fmts = attrs.get("document-format-supported", [])
    model = ", ".join(attrs.get("printer-make-and-model", [])) or "?"
    good = [f for f in fmts if f in ("image/urf", "image/pwg-raster", "application/pdf")]
    say(f"answers fine ({model}); formats: {', '.join(fmts) or 'none listed'}")
    if not good:
        say("no driverless format (image/urf, image/pwg-raster or application/pdf) offered: this printer needs a driver")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:   # a diagnosis must never break the add-on
        say(f"check failed ({type(e).__name__}: {e})")

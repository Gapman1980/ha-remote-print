<p align="center"><img src="remote_print/logo.png" width="120" alt="Remote Print"></p>

<h1 align="center">Remote Print for Home Assistant</h1>

<p align="center">
Upload a file from your phone — even when you are away from home — and your home printer prints it.<br>
<b>🇬🇧 English</b> · <a href="#-italiano">🇮🇹 Italiano</a>
</p>

<p align="center"><img src="docs/demo.gif" width="300" alt="Remote Print: printer popup, upload page, print, printed"></p>

---

## What it does

- A page inside Home Assistant (sidebar entry **Print**): pick a file, choose copies, two-sided, fit to page, page ranges, tap **PRINT AT HOME**.
- Works from anywhere Home Assistant works (Nabu Casa, VPN, reverse proxy…): the file travels through Home Assistant **ingress**, nothing is exposed to the internet.
- Accepts **PDF, photos (JPG, PNG, HEIC from iPhone) and text**. Word/Excel: export them to PDF on the phone first.
- Live list of recent prints (*Queued → Printing… → Printed ✓*), cancel button, printer alerts (out of paper, toner low, door open).
- No printer driver needed: inside the add-on **CUPS** creates a *driverless* queue (IPP Everywhere / AirPrint) and converts files to the format your printer wants. Made for printers that **do not accept PDF directly** and whose vendor "print anywhere" cloud service is not available.
- Italian and English (follows the phone language).

## Requirements

- Home Assistant **OS** or **Supervised** (add-ons are needed).
- A network printer that supports **IPP / AirPrint** (almost every printer sold in the last 10 years: HP, Brother, Canon, Epson, Samsung, Kyocera…), **or** a Brother mono laser without AirPrint (see *Brother lasers* below). Give it a fixed IP address on your router.

## Installation

1. Home Assistant → **Settings → Add-ons → Add-on store** → ⋮ (top right) → **Repositories**.
2. Add: `https://github.com/Gapman1980/ha-remote-print` → **Add** → close.
3. Find **Remote Print** in the store → **Install** (the first build takes a few minutes: it downloads CUPS).
4. **Configuration** tab → set **printer_uri** (see below) → **Save**.
5. **Info** tab → **Start**, turn on **Show in sidebar**.
6. Open **Print** from the sidebar, pick a file and print. 🎉

### Finding the printer address (`printer_uri`)

Most printers: `ipp://PRINTER-IP/ipp/print` (e.g. `ipp://192.168.1.100/ipp/print`).
If it does not work try `ipps://PRINTER-IP/ipp/print` or `ipp://PRINTER-IP/ipp`.
The **Log** tab tells you if the queue was created: `Queue RemotePrint ready`.

### Brother lasers without AirPrint (new in 1.1.0)

Some cheap Brother mono lasers (e.g. **DCP-1610W**, HL-1210W, MFC-1910W) print from the phone only with the Brother app and
have no AirPrint. For them set:

```yaml
printer_uri: socket://PRINTER-IP:9100
driver: brlaser
brother_model: DCP-1600   # part of the model name: DCP-1600 covers DCP-1610W/1612W
```

It uses the open source [brlaser](https://github.com/pdewacht/brlaser) driver. If the model is not found, the **Log** lists the
available ones. Paper/toner alerts are not available in this mode.

### Options

| Option | Default | Meaning |
|---|---|---|
| `printer_uri` | `ipp://192.168.1.100/ipp/print` | IPP address of the printer (`socket://IP:9100` with brlaser) |
| `driver` | `driverless` | `driverless` (AirPrint / IPP Everywhere) or `brlaser` (Brother lasers without AirPrint) |
| `brother_model` | `DCP-1600` | brlaser only: part of the model name |
| `paper` | `A4` | A4, A5, Letter, Legal |
| `duplex_default` | `false` | "Two-sided" switch starts on |
| `keep_days` | `3` | uploaded files are deleted after N days |
| `language` | `auto` | `auto` (phone language), `en`, `it` |

## Dashboard (optional)

**Simple button** – [`examples/simple_button.yaml`](examples/simple_button.yaml): a normal Home Assistant button that opens the page.

**Animated printer card + popup** – [`examples/printer_card_popup.yaml`](examples/printer_card_popup.yaml):
a mini card with an animated printer (paper coming out while printing, toner bar, glow by state) and, on double tap, a popup with
toner level, pages left, printed pages, scans, misfeeds and an **UPLOAD FILE AND PRINT** button that opens the page *inside the popup*;
its **Back** button returns to the printer popup.

- Needs (HACS): [button-card](https://github.com/custom-cards/button-card), [browser_mod](https://github.com/thomasloven/hass-browser_mod), [card-mod](https://github.com/thomasloven/lovelace-card-mod).
- Sensors are written for the HP Printer integration: replace `sensor.YOUR_PRINTER_` with your sensors.
- Replace `YOUR_INGRESS_TOKEN` with the address shown in the add-on **Log**: `Ingress URL for the dashboard popup: /api/hassio_ingress/…/`.
- Only **administrator** users can open add-on pages in Home Assistant.

## How it works

```
phone ──(HA app / browser)──► Home Assistant ingress ──► Remote Print add-on
                                                            │ CUPS driverless queue (IPP Everywhere)
                                                            │ PDF / JPG / PNG / HEIC / TXT → PWG / URF raster
                                                            ▼
                                                      network printer (IPP)
```

The web server only accepts requests coming from Home Assistant ingress (`172.30.32.2`); CUPS only listens inside the container.

## Troubleshooting

- **"Printer not reachable"**: check the IP and that the printer is on; wrong path → try the alternatives above.
- **Jobs stay "Queued"**: the printer is asleep or off; CUPS retries automatically when it comes back.
- **Nothing happens when tapping the card button**: open the page once from the sidebar, check the ingress token in the example.

---

## 🇮🇹 Italiano

**Remote Print** ti permette di stampare a casa un file che hai sul telefono, anche quando sei fuori.

### Come si presenta

Nella GIF in alto: popup della stampante → **CARICA FILE E STAMPA** → scelta del file → **STAMPA A CASA** → "Stampato ✓".

### Cosa fa
- Una pagina dentro Home Assistant (voce **Stampa** nel menu): scegli il file, copie, fronte/retro, adatta al foglio, pagine e premi **STAMPA A CASA**.
- Funziona ovunque funzioni Home Assistant (Nabu Casa, VPN…): il file passa dall'**ingress** di HA, niente porte aperte su internet.
- Accetta **PDF, foto (JPG, PNG, HEIC dell'iPhone) e testo**. Word/Excel: esportali prima in PDF dal telefono.
- Elenco delle ultime stampe con stato in tempo reale, annulla, avvisi della stampante (carta finita, toner, sportello aperto).
- Nessun driver: dentro l'add-on **CUPS** crea una coda *driverless* (IPP Everywhere / AirPrint) e converte i file nel formato della stampante. Pensato per le stampanti che **non accettano PDF diretti** e per cui il servizio cloud del produttore non funziona.

### Installazione
1. Home Assistant → **Impostazioni → Componenti aggiuntivi → Store** → ⋮ in alto a destra → **Repository**.
2. Aggiungi `https://github.com/Gapman1980/ha-remote-print` → **Aggiungi**.
3. Cerca **Remote Print** → **Installa** (la prima volta ci mette qualche minuto).
4. Scheda **Configurazione** → scrivi **printer_uri**, di solito `ipp://IP-STAMPANTE/ipp/print` → **Salva**.
5. Scheda **Info** → **Avvia** e attiva **Mostra nella barra laterale**.
6. Apri **Stampa** dal menu laterale, scegli un file e stampa. 🎉

Nel **Registro** dell'add-on deve comparire `Queue RemotePrint ready`. Se la stampante non risponde prova `ipps://IP/ipp/print` oppure `ipp://IP/ipp`. Dai alla stampante un IP fisso nel router.

### Laser Brother senza AirPrint (novità 1.1.0)
Alcune Brother laser economiche (es. **DCP-1610W**, HL-1210W, MFC-1910W) stampano dal telefono solo con l'app Brother. Per queste, in **Configurazione**:
- `printer_uri`: `socket://IP-STAMPANTE:9100`
- `driver`: `brlaser`
- `brother_model`: `DCP-1600` (parte del nome del modello; DCP-1600 va bene per DCP-1610W/1612W)

Usa il driver libero [brlaser](https://github.com/pdewacht/brlaser). Se il modello non viene trovato, il Registro elenca quelli disponibili. In questa modalità non ci sono gli avvisi carta/toner.

### Card per la dashboard (facoltativa)
- `examples/simple_button.yaml`: pulsante semplice che apre la pagina.
- `examples/printer_card_popup.yaml`: mini card animata della stampante + popup con toner e contatori, e pulsante **CARICA FILE E STAMPA** che apre la pagina *dentro il popup* (con **Indietro** torni al popup). Servono button-card, browser_mod e card-mod; sostituisci `sensor.YOUR_PRINTER_` con i tuoi sensori e `YOUR_INGRESS_TOKEN` con l'indirizzo scritto nel Registro dell'add-on.
- Le pagine degli add-on si aprono solo agli utenti **amministratori**.

---

MIT License · made with ❤️ for Home Assistant

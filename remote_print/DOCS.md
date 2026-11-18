# Remote Print

Upload a file from your phone (even away from home) and your network printer prints it.

## Configuration

- **printer_uri**: IPP address of the printer, usually `ipp://PRINTER-IP/ipp/print`.
  Alternatives: `ipps://PRINTER-IP/ipp/print`, `ipp://PRINTER-IP/ipp`. Give the printer a fixed IP.
- **driver**: `driverless` (AirPrint / IPP Everywhere, default) or `brlaser` for Brother mono lasers without AirPrint
  (e.g. DCP-1610W, HL-1210W). With `brlaser` use `printer_uri: socket://PRINTER-IP:9100`.
- **brother_model**: only for `brlaser`: part of the model name, e.g. `DCP-1600` (covers DCP-1610W/1612W), `HL-1200`, `MFC-L2710`.
  Models in the included brlaser (v6): DCP-1510, DCP-1600, DCP-7030, DCP-7040, DCP-7055, DCP-7055W, DCP-7060D, DCP-7065DN,
  DCP-7080, DCP-7080D, DCP-L2500D, DCP-L2520D, DCP-L2540DW, HL-1110, HL-1200, HL-2030, HL-2140, HL-2220, HL-2270DW, HL-5030,
  HL-L2300D, HL-L2320D, HL-L2340D, HL-L2360D, MFC-1910W, MFC-7240, MFC-7360N, MFC-7365DN, MFC-L2710DW.
  If yours is missing, try one of the same series and age (e.g. MFC-7820N → `HL-2030`).
  If nothing matches, the log lists the available models.
- **paper**: A4, A5, Letter or Legal.
- **duplex_default**: the "two-sided" switch starts on.
- **keep_days**: uploaded files are deleted after this many days.
- **language**: `auto` (phone language), `en` or `it`.
- **allowed_users** (optional, 1.5.0): Home Assistant usernames that may print without being administrators (see Notes).
- **printer_name** (optional): name of the main printer on the page when you have more than one.
- **other_printers** (optional): more printers to choose from on the page. Easiest with **⋮ → Edit in YAML**:

```yaml
printer_name: HP Office
printer_uri: ipp://192.168.1.60/ipp/print
driver: driverless
other_printers:
  - name: Brother
    printer_uri: socket://192.168.1.70:9100
    driver: brlaser
    brother_model: HL-1200
```

The main printer is the default; with two or more printers the page shows a selector (the choice is remembered on each phone),
alerts refer to the printer selected and the job list shows where each job went.

After saving, start the add-on and turn on **Show in sidebar**. The log must say `[RemotePrint] Queue ready`
(one line per printer: `RemotePrint2`, `RemotePrint3` ...).

## Use

Open **Print** from the sidebar → tap to choose a file (PDF, JPG, PNG, HEIC, TXT) → copies / two-sided / fit / pages →
**PRINT AT HOME**. The list below shows the state of the last 15 jobs; ✕ cancels a queued job, 🗑 removes a finished
job from the list and **Clear** (tap twice) empties it.

**Preview and position** (optional, after choosing a file): shows the sheet with the printer's printable border (red dashes)
and your page. Portrait / landscape, scale slider, **Fit**, **Center**, **100 %**, drag the page with a finger, arrows to see
the other pages of a PDF. What you see is what gets printed; adjustments apply to all pages.

The log also prints the **Ingress URL** used by the dashboard popup example (see the repository README).

## Notes

- **Non-admin users** (1.5.0): add their Home Assistant **usernames** to `allowed_users` (e.g. `- alisha`), save and
  restart. They open **Print** from the sidebar or the dashboard popup with their own login, also away from home.
  Administrators can always use it; other users see "Not allowed" (they can hide the sidebar entry).
- Alternative for the local network only: turn on `lan_access`, set a port in **Network**, restart, then use a Webpage card with `http://HOME-ASSISTANT-IP:PORT/` (no password: anyone on your Wi-Fi can print; never forward the port; needs Home Assistant opened over `http://`).
- With `brlaser` the printer does not report paper/toner state (no IPP), so alerts are not shown.
- Files never leave your home network: they go phone → Home Assistant → printer.

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

After saving, start the add-on and turn on **Show in sidebar**. The log must say `Queue RemotePrint ready`.

## Use

Open **Print** from the sidebar → tap to choose a file (PDF, JPG, PNG, HEIC, TXT) → copies / two-sided / fit / pages →
**PRINT AT HOME**. The list below shows the state of each job; ✕ cancels a queued job.

The log also prints the **Ingress URL** used by the dashboard popup example (see the repository README).

## Notes

- Only Home Assistant administrators can open add-on pages.
- With `brlaser` the printer does not report paper/toner state (no IPP), so alerts are not shown.
- Files never leave your home network: they go phone → Home Assistant → printer.

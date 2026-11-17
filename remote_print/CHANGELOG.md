# Changelog

## 1.1.4
- With `driver: brlaser`, a `brother_model` that matches no driver now shows a clear message with the full list
  of supported models (before only the last part of the list, inside "Printer not reachable"), without retrying.

## 1.1.3
- `printer_uri` and `brother_model` tolerate common typing mistakes: the label typed in the field too
  (`printer_uri: socket://...`), quotes and spaces are removed (before: "Bad device-uri").

## 1.1.2
- When the print queue is missing, the add-on now waits at most ~50 s for the printer instead of several minutes.
  Before, a printer without AirPrint could keep the upload open so long that the page only said "Connection lost".
- Clearer errors: printers without AirPrint / IPP Everywhere get a hint to use `driver: brlaser` (Brother lasers),
  also in the add-on Log; "file sent but no answer" is now told apart from a real upload failure.

## 1.1.1
- Android: the file picker now opens without type filters. With filters the Home Assistant Android app could crash
  when returning from the picker (back to the dashboard, picker stuck until the app was closed). The add-on still
  accepts only PDF, photos and text.
- Files whose name has no extension (some Android pickers) are recognised by their type (PDF, JPG, PNG, HEIC, TXT).

## 1.1.0
- New option **driver**: `brlaser` adds support for Brother mono laser printers without AirPrint / IPP Everywhere
  (e.g. DCP-1610W, HL-1210W, MFC-1910W). Use `printer_uri: socket://PRINTER-IP:9100` and set **brother_model** (default `DCP-1600`).
- Default `driverless` behaves exactly as before.

## 1.0.1
- Fix: after an add-on restart CUPS reuses job numbers, so old prints showed again as "Printing…" (duplicated list).

## 1.0.0
- First public release: upload page (ingress), driverless CUPS queue, copies, two-sided, fit to page, page ranges,
  HEIC photos, job list with live status and cancel, printer alerts (paper, toner, door), Italian/English.

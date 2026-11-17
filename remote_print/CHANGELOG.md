# Changelog

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

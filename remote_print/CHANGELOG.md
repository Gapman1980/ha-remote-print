# Changelog

## 1.8.0
- **Ink and toner levels on the page** ([#11](https://github.com/Gapman1980/ha-remote-print/issues/11)): under the printer choice a new box shows one
  animated bar per cartridge (black, cyan, magenta, yellow, or the toner of a laser) with its percentage, coloured like the ink.
  Orange with "running low" near the printer's own low mark, red and blinking when it is empty.
- The levels are read from the printer itself with a read-only IPP request (`marker-levels`, the same data the printer's web page shows):
  nothing is printed and nothing to configure. Works with driverless/AirPrint printers; for `socket://` queues the add-on tries IPP
  on the same address, otherwise it uses the copy CUPS keeps while printing. If the printer does not report levels, the box stays hidden.
- Refreshed when the page opens, when you switch printer and every 5 minutes. Thanks @Eugenio-1204 for the idea.

## 1.7.0
- **Black & white switch** on the page (suggested on Facebook): prints without colour ink. The file is turned into shades
  of grey before printing (Ghostscript) and the printer is also asked for monochrome (`print-color-mode`), so it works
  even with printers that ignore that option. The preview turns grey too, and the job list shows ⚫ B&W.
- Printers that are black & white only (read from their driver) get the switch already on and locked, with a short note.
- New option `bw_default`: the switch starts on (handy if you mostly print documents).

## 1.6.1
- **`http://…:9100` is now fixed automatically** ([#10](https://github.com/Gapman1980/ha-remote-print/issues/10)): port 9100 is the
  printer's raw port, which prints whatever it receives as text. With `http://`, `ipp://` or no scheme on that port the
  printer printed the request itself (`POST / HTTP/1.1`, `content-length` …). The add-on now uses `socket://host:9100`
  and says so in the Log. Other ports and URIs are untouched.

## 1.6.0
- **URF (AirPrint raster) printers get the same header macOS sends** ([#2](https://github.com/Gapman1980/ha-remote-print/issues/2)): CUPS writes
  page count 0 ("unknown") and a one-sided flag of 1, Apple writes the real number of pages and 0. Some printers
  (e.g. Samsung M2070) fed blank or garbage sheets with the CUPS header. A small filter (`urffix`) now rewrites only
  those bytes; the image data is untouched and anything unexpected is sent unchanged. Thanks @Danyasr for finding it.

## 1.5.2
- The yellow alert box no longer shows CUPS' own internal messages (e.g. `cups-waiting-for-job-completed`, which appeared
  during every print on some printers and vanished at the end, [#7](https://github.com/Gapman1980/ha-remote-print/issues/7)). Real printer alerts (paper, toner, door ...) are shown as before.

## 1.5.1
- **Clearer reason when the queue can't be created** (driverless): the add-on now asks the printer once (read-only, nothing is
  printed) and writes in the Log what it answered, e.g. *IPP authentication is on*, *encrypted connection refused*,
  *wrong path*, *IPP status client-error-forbidden*, or the formats it offers. The same line is shown on the page.

## 1.5.0
- **Non-admin Home Assistant users** ([#3](https://github.com/Gapman1980/ha-remote-print/issues/3)): new option
  `allowed_users` (Home Assistant usernames, e.g. `alisha`). Those users can open **Print** from the sidebar or a
  dashboard popup like administrators, through Home Assistant with their own login: no extra port, no `lan_access`.
  Administrators can always use it; anyone else sees a "Not allowed" page. Empty list (default) = administrators only, as before.
- The **Print** entry now appears in the sidebar of every user (Home Assistant can only show an add-on panel to
  everyone or to administrators). Users not in the list can hide it from their sidebar.
- With prints from more than one person, the job list shows who printed each file.

## 1.4.1
- **Clean up the job list**: each finished or canceled print has a 🗑 button to remove it from the list, and
  **Clear** next to "Recent prints" empties the whole list (tap twice to confirm). Jobs still queued or printing stay.
  Reminder: the list already showed only the last 15 prints, and uploaded files are deleted after `keep_days`.

## 1.4.0
- **Print preview with scale and position** ([#5](https://github.com/Gapman1980/ha-remote-print/issues/5)): after choosing a
  file, tap **Preview and position** to see the sheet with the printer's printable border and your page on it.
  Portrait / landscape, scale slider (5–300 %), **Fit**, **Center**, **100 %**, drag with a finger to move it, page arrows
  for multi-page PDFs. The add-on builds a PDF with exactly that layout and prints it without extra scaling, so the print
  matches the preview. Adjustments apply to all pages. Without opening the preview, printing works as before.

## 1.3.0
- **More printers** ([#4](https://github.com/Gapman1980/ha-remote-print/issues/4)): new optional `other_printers` list
  (name, printer_uri, driver, brother_model) and `printer_name` for the main printer. With two or more printers the page
  shows a printer selector (remembered on each phone); alerts follow the selected printer and the job list shows where
  each job went. One CUPS queue per printer (`RemotePrint`, `RemotePrint2` ...). Existing single-printer setups work unchanged.

## 1.2.0
- Fix for printers that only accept URF / Apple raster (e.g. Samsung M2070, #2): if the generated driver used a
  1-bit black colour model, pages were sent as 1-bit URF and the printer printed random characters and blank sheets.
  URF queues are now forced to 8-bit gray / colour. The add-on Log also shows the colour model, to help with reports.
- New option `lan_access` (#3): with a port set in the **Network** section, the page also opens at
  `http://HOME-ASSISTANT-IP:PORT/` so non-admin users can use it in a Webpage card. Off by default, local network
  addresses only, no password: anyone on your Wi-Fi can print. Never forward this port on the router.

## 1.1.5
- Photos (JPG, PNG, GIF, TIFF and converted HEIC) are turned into a PDF before printing. Some printers decode JPGs
  themselves and failed on modern phone photos (e.g. HP "DirectJPEG ERROR - Decoding Fail" with Samsung Ultra HDR
  photos). Rotation from the phone is applied, very large photos are reduced to 300 dpi. If the conversion fails the
  original photo is sent as before.

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

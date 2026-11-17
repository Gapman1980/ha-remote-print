#!/bin/sh
# Create the CUPS queue "RemotePrint" from the add-on options.
#   driver: driverless -> IPP Everywhere / AirPrint (no driver, the printer describes itself)
#   driver: brlaser    -> open source driver for Brother mono lasers that have no AirPrint
#                         (DCP-1510/1600, HL-1200/L2300, MFC-1910/7360/L2710 ... families)
OPT=/data/options.json
# Forgive common typing mistakes in the UI fields: "printer_uri: socket://..." (label typed too), quotes, spaces
URI=$(jq -r '.printer_uri' $OPT | sed -E 's/^[[:space:]]*[Pp][Rr][Ii][Nn][Tt][Ee][Rr]_?[Uu][Rr][Ii][[:space:]]*:[[:space:]]*//' | tr -d "\"' ")
DRIVER=$(jq -r '.driver // "driverless"' $OPT)
MODEL=$(jq -r '.brother_model // "DCP-1600"' $OPT | sed -E 's/^[[:space:]]*[Bb][Rr][Oo][Tt][Hh][Ee][Rr]_?[Mm][Oo][Dd][Ee][Ll][[:space:]]*:[[:space:]]*//' | tr -d "\"'" | sed -E 's/^[[:space:]]+|[[:space:]]+$//g')
echo "Printer URI: $URI"
case "$(jq -r '.paper // "A4"' $OPT)" in
  A5) MEDIA=iso_a5_148x210mm ;; Letter) MEDIA=na_letter_8.5x11in ;; Legal) MEDIA=na_legal_8.5x14in ;; *) MEDIA=iso_a4_210x297mm ;;
esac

if [ "$DRIVER" = "brlaser" ]; then
  PPD=$(lpinfo -m 2>/dev/null | grep -i brlaser | grep -i -- "$MODEL" | head -1 | cut -d' ' -f1)
  if [ -z "$PPD" ]; then
    echo "brlaser: no driver matches brother_model '$MODEL'. Available models:"
    lpinfo -m 2>/dev/null | grep -i brlaser | cut -d' ' -f2- | sed 's/^/  /'
    exit 2
  fi
  echo "Driver: brlaser ($(lpinfo -m | grep -F "$PPD " | head -1 | cut -d' ' -f2-))"
  exec lpadmin -p RemotePrint -E -v "$URI" -m "$PPD" -o printer-error-policy=retry-job -o media-default=$MEDIA
fi

echo "Driver: driverless (IPP Everywhere / AirPrint)"
lpadmin -p RemotePrint -E -v "$URI" -m everywhere -o printer-error-policy=retry-job -o media-default=$MEDIA || exit $?

# URF (Apple raster) printers only understand 8-bit gray or 24-bit colour pages.
# Some printers (e.g. Samsung M2070) end up with a 1-bit / black colour model in the generated PPD:
# the page is sent as 1-bit URF and the printer prints random characters + blank sheets.
# Force 8-bit sGray / sRGB on URF queues.
PPDF=/etc/cups/ppd/RemotePrint.ppd
if [ -f "$PPDF" ] && grep -q 'cupsFilter2: "image/urf' "$PPDF"; then
  if grep -E 'cupsBitsPerColor (1|2|4)[^0-9]|cupsColorSpace (3|0)[^0-9]' "$PPDF" >/dev/null; then
    sed -i -E 's/cupsBitsPerColor (1|2|4)([^0-9])/cupsBitsPerColor 8\2/g; s/cupsColorSpace (3|0)([^0-9])/cupsColorSpace 18\2/g' "$PPDF"
    echo "URF printer: colour model forced to 8-bit (sGray/sRGB)"
  fi
fi
exit 0

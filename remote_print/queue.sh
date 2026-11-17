#!/bin/sh
# Create the CUPS queue "RemotePrint" from the add-on options.
#   driver: driverless -> IPP Everywhere / AirPrint (no driver, the printer describes itself)
#   driver: brlaser    -> open source driver for Brother mono lasers that have no AirPrint
#                         (DCP-1510/1600, HL-1200/L2300, MFC-1910/7360/L2710 ... families)
OPT=/data/options.json
URI=$(jq -r '.printer_uri' $OPT)
DRIVER=$(jq -r '.driver // "driverless"' $OPT)
MODEL=$(jq -r '.brother_model // "DCP-1600"' $OPT)
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
exec lpadmin -p RemotePrint -E -v "$URI" -m everywhere -o printer-error-policy=retry-job -o media-default=$MEDIA

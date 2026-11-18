#!/bin/sh
# Remote Print: start CUPS (container-only), create one queue per printer (driverless or brlaser, see queue.sh),
# then the ingress web page (port 8099)
mkdir -p /data/uploads /run/cups
cupsd
sleep 2
N=$(jq -r '(.other_printers // []) | length' /data/options.json)
# printers removed from the configuration: delete their old queues
for q in $(lpstat -e 2>/dev/null | grep -E '^RemotePrint[0-9]+$'); do
  [ "${q#RemotePrint}" -gt $((N + 1)) ] && lpadmin -x "$q" && echo "Removed old queue $q"
done
i=0
while [ $i -le "$N" ]; do
  Q=RemotePrint; [ $i -gt 0 ] && Q="RemotePrint$((i + 1))"
  if [ $i -eq 0 ]; then DRV=$(jq -r '.driver // "driverless"' /data/options.json); else DRV=$(jq -r ".other_printers[$((i - 1))].driver // \"driverless\"" /data/options.json); fi
  if /queue.sh $i; then
    echo "[$Q] Queue ready"
    lpoptions -p "$Q" -l | grep -iE "PageSize|Duplex|ColorModel" | cut -c1-120
    grep -E 'cupsFilter2|^\*ColorModel ' "/etc/cups/ppd/$Q.ppd" 2>/dev/null | cut -c1-140
  else
    echo "[$Q] Queue not created now (printer off or wrong URI?): retrying at the first print"
    [ "$DRV" = "driverless" ] && \
      echo "[$Q] Hint: driverless needs a printer with AirPrint / IPP Everywhere. Brother laser without AirPrint? Use driver: brlaser + socket://PRINTER-IP:9100"
  fi
  i=$((i + 1))
done
# show the ingress URL (needed by the dashboard popup example, see README)
INGRESS=$(curl -s -H "Authorization: Bearer $SUPERVISOR_TOKEN" http://supervisor/addons/self/info | jq -r '.data.ingress_url')
echo "Ingress URL for the dashboard popup: $INGRESS"
exec python3 /app.py

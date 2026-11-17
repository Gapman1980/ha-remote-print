#!/bin/sh
# Remote Print: start CUPS (container-only), create the queue (driverless or brlaser, see queue.sh), then the ingress web page (port 8099)
mkdir -p /data/uploads /run/cups
cupsd
sleep 2
URI=$(jq -r '.printer_uri' /data/options.json)
echo "Printer: $URI"
if /queue.sh; then
  echo "Queue RemotePrint ready"
  lpoptions -p RemotePrint -l | grep -iE "PageSize|Duplex|ColorModel" | cut -c1-120
else
  echo "Queue not created now (printer off or wrong URI?): retrying at the first print"
fi
# show the ingress URL (needed by the dashboard popup example, see README)
INGRESS=$(curl -s -H "Authorization: Bearer $SUPERVISOR_TOKEN" http://supervisor/addons/self/info | jq -r '.data.ingress_url')
echo "Ingress URL for the dashboard popup: $INGRESS"
exec python3 /app.py

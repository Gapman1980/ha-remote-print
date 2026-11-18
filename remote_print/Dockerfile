ARG BUILD_FROM
FROM ${BUILD_FROM}

# CUPS + filters (PDF/images/text -> printer format), HEIC support for iPhone photos, small web server
# Pillow: photos are turned into a clean PDF first (some printers cannot decode modern phone JPGs themselves)
# brlaser: open source driver for Brother mono lasers without AirPrint (option driver: brlaser)
RUN apk add --no-cache python3 py3-aiohttp cups cups-client cups-filters ghostscript libheif-tools font-dejavu jq brlaser py3-pillow py3-pypdf

# CUPS only listens inside the container (unix socket + localhost), no authentication needed
COPY cupsd.conf /etc/cups/cupsd.conf
ENV CUPS_SERVER=/run/cups/cups.sock

COPY run.sh /run.sh
COPY app.py /app.py
COPY index.html /index.html
COPY queue.sh /queue.sh
COPY ippcheck.py /ippcheck.py
RUN chmod +x /run.sh /queue.sh

ENTRYPOINT []
CMD ["/run.sh"]

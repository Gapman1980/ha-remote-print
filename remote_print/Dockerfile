ARG BUILD_FROM
FROM ${BUILD_FROM}

# CUPS + filters (PDF/images/text -> printer format), HEIC support for iPhone photos, small web server
RUN apk add --no-cache python3 py3-aiohttp cups cups-client cups-filters ghostscript libheif-tools font-dejavu jq

# CUPS only listens inside the container (unix socket + localhost), no authentication needed
COPY cupsd.conf /etc/cups/cupsd.conf
ENV CUPS_SERVER=/run/cups/cups.sock

COPY run.sh /run.sh
COPY app.py /app.py
COPY index.html /index.html
RUN chmod +x /run.sh

ENTRYPOINT []
CMD ["/run.sh"]

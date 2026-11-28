FROM pgsty/mc:RELEASE.2026-11-12T00-00-00Z AS mcli

FROM alpine:3.20

RUN apk add --no-cache bash postgresql16-client openssl tar gzip coreutils curl ca-certificates tzdata \
    && addgroup -S backup && adduser -S backup -G backup

COPY --from=mcli /usr/bin/mc /usr/local/bin/mc
COPY backup.sh restore.sh scheduler.sh /scripts/
# Strip CRLF in case the source was copied through Windows.
RUN sed -i 's/\r$//' /scripts/*.sh && chmod +x /scripts/*.sh && mkdir -p /backups && chown backup:backup /backups

USER backup
ENTRYPOINT ["/scripts/scheduler.sh"]

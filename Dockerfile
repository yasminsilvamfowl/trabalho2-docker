# A MinIO deixou de publicar a imagem minio/minio no Docker Hub, então
# geramos a imagem a partir do código-fonte oficial (github.com/minio/minio).
# A primeira build leva alguns minutos; depois fica em cache.
FROM golang:1.24-alpine AS build
ARG MINIO_RELEASE=RELEASE.2025-04-22T22-12-26Z
RUN apk add --no-cache git
RUN git clone --depth 1 --branch ${MINIO_RELEASE} https://github.com/minio/minio.git /src
WORKDIR /src
RUN CGO_ENABLED=0 go build -trimpath -ldflags "-s -w" -o /minio .

FROM alpine:3.20
RUN apk add --no-cache ca-certificates curl
COPY --from=build /minio /usr/bin/minio
EXPOSE 9000 9001
VOLUME ["/data"]
ENTRYPOINT ["minio"]
CMD ["server", "/data", "--console-address", ":9001"]

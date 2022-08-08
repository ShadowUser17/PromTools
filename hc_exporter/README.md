#### Build docker image:
```bash
cd prometheus && docker build -f dockerfile_hc_exporter -t hc_exporter .
```

#### Run docker image:
```bash
docker run --rm --name hc_exporter -d -p '9097:9097/tcp' hc_exporter:latest
```

#### Probe URL:
```bash
curl '127.0.0.1:9097/probe?target=https://ident.me/'
```

#### Prometheus config:
```yaml
scrape_configs:
  - job_name: "hc-exporter"
    metrics_path: "/probe"
    static_configs:
      - targets:
        - "https://ident.me/"
    relabel_configs:
      - source_labels: ["__address__"]
        target_label: "__param_target"
      - source_labels: ["__param_target"]
        target_label: "instance"
      - target_label: "__address__"
        replacement: "127.0.0.1:9097"
```

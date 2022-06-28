#### Build docker image:
```bash
cd alertmanager && docker build -f dockerfile_alerts_exporter -t alerts_exporter .
```

#### Run docker image:
```bash
docker run --rm --name alerts_exporter -d -p '9095:9095/tcp' alerts_exporter:latest
```

#### Collect data:
```bash
curl -X GET 'http://127.0.0.1:9095/metrics'
```

#### Reset data:
```bash
curl -X POST 'http://127.0.0.1:9095/reset'
```

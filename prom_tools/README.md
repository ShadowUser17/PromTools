#### Configure environment:
```bash
python3 -m venv --upgrade-deps env && \
./env/bin/pip3 install -r requirements.txt
```

#### Template example:
```
groups:
- name: Service checks
  rules:
{%- for item in services %}
  - alert: service-{{ item }}
    expr: absent_over_time(service_logs_count{env="{{ env }}", service="{{ item }}"}[1h]) == 1
    for: 0m
    labels:
{%- if env != "prod" %}
      severity: warning
      slack_channel: prom-test-env
{%- else %}
      severity: warning
      slack_channel: prom-prod-env
{%- endif %}
    annotations:
      summary: "Alert from {{ item }} during the last hour"
      description: "Env: {{ env }} Service: {{ item }}"
      fingerprint: "Service (Instance: {{ item }})"
{% endfor %}
```

#### URLs:
- [querying](https://prometheus.io/docs/prometheus/latest/querying/api/)
- [alerting](https://prometheus.io/docs/alerting/latest/clients/)

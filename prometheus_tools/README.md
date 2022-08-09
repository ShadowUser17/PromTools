#### URLs:
- [querying_api](https://prometheus.io/docs/prometheus/latest/querying/api/)

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

# Grafana dashboards

Dashboards are generated from `scripts/build_dashboards.py`; the committed
JSON is its output. UI tweaks live only in Grafana's database and are
overwritten at the next provisioning reload, so put anything worth keeping in
the spec.

```bash
python3 scripts/build_dashboards.py
python3 scripts/test_dashboards.py       # not optional: a bad panel fails silently at runtime
```

Check the live boat:

```bash
python3 scripts/verify_dashboards_live.py --grafana https://grafana.<DOMAIN> --user <admin> --password <password>
curl -sG http://localhost:9000/exec --data-urlencode "query=SELECT table_name FROM tables()"   # a missing Telegraf table is a panel that cannot draw
```

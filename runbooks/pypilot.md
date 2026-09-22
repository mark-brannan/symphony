# pypilot

Containerized; the native units are disabled and `~/.pypilot` is the rollback.
State is in `pypilot/data/` (untracked: compass calibration and a SignalK
token).

*Verify,* in order:

```bash
docker exec pypilot i2cdetect -y 1                                    # 0x68 present = the IMU answers
docker logs pypilot 2>&1 | grep -i realtime                           # must read: made imu process realtime
docker exec pypilot pypilot_client imu.heading imu.pitch imu.error    # tilt the Pi, run again
curl -s -o /dev/null -w '%{http_code}\n' localhost:8000               # 200
```

Back up before any rebuild or re-image:

```bash
tar czf ~/pypilot-data-$(date +%Y%m%d).tgz -C pypilot data
tar tzf ~/pypilot-data-*.tgz | grep RTIMULib.ini      # must match
```

Move `PYPILOT_REF` forward by editing the ARG in `pypilot/Dockerfile`, not on
the boat first:

```bash
docker compose --profile pypilot up -d --build pypilot pypilot-web
docker exec pypilot pip show pypilot | head -2        # the version you expect, then re-run the four checks
```

Roll back to native:

```bash
docker compose --profile pypilot down
sudo systemctl enable --now pypilot pypilot_web
```

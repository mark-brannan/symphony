# Read-only stock-state inventory of a fresh HaLOS box. No writes.
set +e
s(){ printf '\n===== %s =====\n' "$1"; }
s hostname; hostname; hostnamectl 2>/dev/null | head -12
s os; cat /etc/os-release | head -4; uname -a
s halos-version; cat /etc/halos-release /etc/halos/version 2>/dev/null; ls /etc/halos 2>/dev/null
s halos-packages; dpkg -l | grep -iE 'halos|halpi|signalk|grafana|influx|questdb|avnav|opencpn|traefik|authelia|cockpit|docker' | awk '{print $2, $3}'
s apt-sources; grep -rh '^[^#]' /etc/apt/sources.list /etc/apt/sources.list.d/ 2>/dev/null
s block-devices; lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINT,LABEL
s disk; df -h / /boot/firmware 2>/dev/null
s memory; free -m
s cpu-model; cat /proc/device-tree/model 2>/dev/null | tr -d '\0'; echo; cat /proc/cpuinfo | grep -E 'Revision|Serial' 
s eeprom; sudo -n rpi-eeprom-update 2>/dev/null | head -8 || echo 'rpi-eeprom-update needs sudo/not present'
s network; ip -br addr; ip route; cat /etc/hostname; nmcli -t dev status 2>/dev/null; nmcli -t con show 2>/dev/null
s hotspot; nmcli -t con show 2>/dev/null | grep -i -E 'hotspot|halos|ap' ; ls /etc/NetworkManager/system-connections/ 2>/dev/null
s config-txt; cat /boot/firmware/config.txt 2>/dev/null | grep -v '^#' | grep -v '^$'
s cmdline; cat /boot/firmware/cmdline.txt 2>/dev/null
s overlays-loaded; ls /proc/device-tree/soc 2>/dev/null | grep -iE 'can|spi|mcp' ; ip -br link | grep -i can
s users; getent passwd | awk -F: '$3>=1000{print $1, $3, $6, $7}'; id; sudo -n true 2>/dev/null && echo 'passwordless sudo: yes' || echo 'passwordless sudo: no'
s ssh; ls -la ~/.ssh 2>/dev/null; cat ~/.ssh/authorized_keys 2>/dev/null | wc -l; grep -E '^(PasswordAuthentication|PermitRootLogin|PubkeyAuthentication)' /etc/ssh/sshd_config /etc/ssh/sshd_config.d/* 2>/dev/null
s services-enabled; systemctl list-unit-files --state=enabled --no-pager | grep -vE '^(UNIT|$|.*unit files listed)' | awk '{print $1}'
s services-failed; systemctl --failed --no-pager --no-legend
s docker; docker ps -a --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}' 2>/dev/null || sudo -n docker ps -a --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}' 2>/dev/null
s docker-images; (docker images --format '{{.Repository}}:{{.Tag}} {{.Size}}' 2>/dev/null || sudo -n docker images --format '{{.Repository}}:{{.Tag}} {{.Size}}' 2>/dev/null)
s docker-volumes; (docker volume ls -q 2>/dev/null || sudo -n docker volume ls -q 2>/dev/null)
s halos-config-dirs; ls -la /etc/halos /opt/halos /var/lib/halos /srv 2>/dev/null; find /etc /opt /var/lib -maxdepth 2 -iname '*halos*' -o -maxdepth 2 -iname '*halpi*' 2>/dev/null
s listening; (ss -tlnp 2>/dev/null || sudo -n ss -tlnp 2>/dev/null) | awk 'NR>1{print $4, $6}' 
s halpi-daemon; systemctl list-units --all --no-pager --no-legend 2>/dev/null | grep -iE 'halpi|rp2040|power|halos' ; which halpi halpid 2>/dev/null; ls /dev/i2c* /dev/ttyAMA* /dev/ttyS* /dev/serial/by-id/ 2>/dev/null
s usb; lsusb 2>/dev/null
s tailscale; command -v tailscale && tailscale status 2>&1 | head -3 || echo 'tailscale: not installed'
s timers; systemctl list-timers --no-pager --no-legend 2>/dev/null | awk '{print $NF, $(NF-1)}' | head -20
s uptime; uptime; last -x 2>/dev/null | head -5
s home; ls -la ~
s etc-recently-modified; find /etc -newer /etc/os-release -type f 2>/dev/null | head -40

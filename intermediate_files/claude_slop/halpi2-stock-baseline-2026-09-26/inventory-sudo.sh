set +e
S(){ echo "$SUDO_PASS" | sudo -S -p '' "$@" 2>/dev/null; }
s(){ printf '\n===== %s =====\n' "$1"; }
s image-id; cat /etc/rpi-issue 2>/dev/null; ls /boot/firmware/*.txt /boot/firmware/*release* 2>/dev/null; cat /boot/firmware/issue.txt 2>/dev/null
s boots; S journalctl --list-boots --no-pager | tail -15; echo; last -x reboot shutdown 2>/dev/null | head -12
s machine-id-and-hostkeys; ls -l --time-style=long-iso /etc/machine-id /etc/ssh/ssh_host_*_key.pub
s cloud-init; cloud-init status --long 2>/dev/null; ls -la /var/lib/cloud/instance/ /var/lib/cloud/instances/ 2>/dev/null; S cat /var/lib/cloud/instance/user-data.txt 2>/dev/null | head -40; ls /etc/cloud/cloud.cfg.d/ 2>/dev/null; S ls /boot/firmware/ | grep -iE 'user-data|meta-data|network' 
s halos-state; cat /var/lib/halos/resolved-domain; echo; cat /etc/halos/port-registry; echo; cat /etc/halos/hostnames.conf | grep -v '^#' | grep -v '^$'; ls -la /etc/halos/*.d/ ; S ls -la /etc/halos/ca
s docker; S docker ps -a --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'
s docker-images; S docker images --format '{{.Repository}}:{{.Tag}} {{.Size}} {{.CreatedSince}}'
s docker-volumes; S docker volume ls --format '{{.Name}}'
s container-apps; ls -la /etc/container-apps/ /var/lib/container-apps/ 2>/dev/null; find /etc/container-apps /var/lib/container-apps -maxdepth 2 2>/dev/null | head -30
s halpi; halpi --version 2>&1; halpi status 2>&1 | head -20; cat /etc/halpid/halpid.conf 2>/dev/null | grep -v '^#' | grep -v '^$'
s eeprom; S rpi-eeprom-update | head -8
s halos-cli; dpkg -L halos halos-halpi2 halos-core-containers 2>/dev/null | grep -E '/bin/|/sbin/'; ls /usr/lib/halos /usr/share/halos 2>/dev/null
s signalk-data; ls -la /var/lib/container-apps/*/ 2>/dev/null | head -30; S find / -xdev -maxdepth 4 -type d -name '.signalk' 2>/dev/null
s ap-config; S cat /etc/NetworkManager/system-connections/Halos-AP.nmconnection | grep -vE '^(psk|$)'; cat /var/lib/halos/wifi-sta-ap-configured; ls /etc/NetworkManager/conf.d/ /etc/NetworkManager/dispatcher.d/ 2>/dev/null
s ssh-hostkeys-regen; systemctl status regenerate_ssh_host_keys.service --no-pager 2>/dev/null | head -5
s big-dirs; S du -xsh /var/lib/docker /var/lib/container-apps /home /usr /var/log 2>/dev/null
s shadow-age; S chage -l pi | head -3
s wifi-country; S iw reg get 2>/dev/null | head -3; timedatectl | grep -E 'zone|NTP'

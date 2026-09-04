# shellcheck shell=bash
# Single source of truth for how the HALOS card's SignalK config is meant to
# differ from the boat's (halos-swap-plan.md). Sourced by halos_preflight.sh
# (to check the difference is exactly this) and halos_config_sync.sh (to
# exclude these files when copying the boat's config onto the card) -- one
# list, so adding or dropping a disabled plugin can't leave the two scripts
# disagreeing.

# Enabled on the boat, disabled on HALOS by decision.
EXPECT="signalk-container signalk-to-influxdb2 signalk-to-influxdb-v2-buffer signalk-notification-player"
# Their plugin-config-data files differ for the same reason -- the disable is
# written into the config -- as does venus.json, which carries the HALOS card's
# own Venus host.
CONFIG_EXPECT="${EXPECT// /.json|}.json|venus.json"

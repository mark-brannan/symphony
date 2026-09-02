#!/usr/bin/env python3
"""Inventory one SignalK install so two of them can be compared.

Symphony runs SignalK twice: natively on the boat Pi, and in a container on
the dev box. Both are real, both have been changed by hand, and they have
drifted. Deciding what to keep means knowing which plugins are actually doing
something on each -- and "enabled" does not answer that, because a plugin can
be enabled, loaded, and completely idle.

Run this against each server and diff the two JSON outputs.

    python3 scripts/signalk_plugin_census.py --url http://localhost:3000 \
        --token "$TOK" --out boat.json
    python3 scripts/signalk_plugin_census.py --url http://dev:3000 \
        --token "$TOK" --out container.json

WHAT THE 'evidence' FIELD MEANS, AND WHAT IT DOESN'T
----------------------------------------------------
Every leaf in the data model carries a $source. The obvious census is "which
plugin ids appear as a $source" -- and it is wrong. Plugins are free to name
their source whatever they like, and the good ones do: bt-sensors-plugin-sk
publishes as "House Battery 1", i2c-reader as "OpenPlotter.I2C.BME680/688-1".
Both were scored silent by a first cut of this script while working perfectly.

So a plugin that publishes nothing under its own id is not idle. It is one of:

  webapp     - a user interface. Publishing nothing is correct.
  exporter   - writes outward (InfluxDB, NMEA 2000, push notifications). It
               consumes the model rather than adding to it. Silence is correct.
  actor      - its product is an effect, not a value: it plays a sound, clears
               a notification, rewrites a path, serves a v2 API. A working
               signalk-notification-player publishes zero paths, because what
               it does is make a noise. Silence is correct.
  renamed    - publishes under a source name that isn't its id. Working.
  unmatched  - none of the above. This is the only bucket worth reviewing,
               and it is still a question rather than a verdict.

The unattributed_sources list is the other half: source names in the model
that no enabled plugin id explains. Every 'renamed' plugin shows up there.
Read the two lists together and the mapping is usually obvious by eye; that
judgement is deliberately left to a human rather than guessed here.
"""
import argparse
import collections
import datetime
import json
import re
import sys
import urllib.request

# Plugins that write outward instead of into the model. Silence from these is
# the design, not a fault. Matched as substrings against the plugin id.
EXPORTER_HINTS = (
    'influxdb', 'postgsail', 'questdb', 'aisreporter', 'ntp-server',
    'to-nmea2000', 'nmea0183', 'push-notifications', 'tracks', 'saillogger',
    'internet-speed', 'speedtest', 'set-gps-timezone', 'grafana', 'usage',
)

# Plugins whose product is an effect, not a value. They mutate existing state,
# clear it, or do something off the boat's data model entirely -- play a sound,
# rename a path, edit zone metadata, serve a v2 API. Counting published paths
# says nothing about them, in either direction: signalk-notification-player
# working perfectly publishes exactly zero paths, because what it does is make
# a noise.
#
# There is no reliable programmatic test for "did this plugin have its intended
# effect", so this bucket is a flag for a human, not a verdict. Same asymmetry
# as webapps: it exists to stop an actor being mistaken for an idle plugin.
ACTOR_HINTS = (
    'notification-player', 'alarm-silencer', 'path-mapper', 'zones',
    'flags', 'autostate', 'beeper', 'course-provider', 'resources-provider',
    'activecaptain', 'wilhelmsk', 'alternator-engine-on', 'ais-status',
    # Providers register a v2 API and serve it on request. Their product is the
    # endpoint, not a published path, so they look identical to an idle plugin
    # from the data model's side. open-meteo scored 'unmatched' and read as a
    # fault while working correctly, which is the same mistake the renamed
    # sources caused -- a plugin doing its job filed as a problem.
    'meteo', 'weather', 'tide', 'chart', 'provider',
    # Same failure, second family: plugins whose product is notifications plus
    # a v2 resources endpoint. signalk-dsc raises distress alarms and serves
    # /resources/dsc-calls, publishes no $source path, and scored 'unmatched'
    # in the 2026-08-14 census -- reading as a fault what was the plugin
    # working exactly as designed.
    'dsc', 'distress',
)


def api(url, token, path, timeout=90):
    req = urllib.request.Request(
        url.rstrip('/') + path,
        headers={'Authorization': 'Bearer ' + token} if token else {},
    )
    return json.load(urllib.request.urlopen(req, timeout=timeout))


def leaves(node, path=''):
    """Yield (path, $source, timestamp) for every value-bearing leaf."""
    if not isinstance(node, dict):
        return
    if '$source' in node and ('value' in node or 'values' in node):
        yield path, node['$source'], node.get('timestamp')
        return
    for key, child in node.items():
        if key in ('meta', '$source', 'timestamp', 'values', 'sentence', 'pgn'):
            continue
        yield from leaves(child, f'{path}.{key}' if path else key)


def self_vessel(model):
    ref = model.get('self', '')
    vessels = model.get('vessels', {})
    key = ref.replace('vessels.', '')
    if key in vessels:
        return vessels[key]
    tail = ref.split('.')[-1]
    for name, vessel in vessels.items():
        if tail and tail in name:
            return vessel
    return next(iter(vessels.values()), {})


def classify(pid, keywords, published):
    # Webapps are checked before publishing on purpose. Publishing paths is not
    # what a webapp is for, so it is the wrong question to ask of one either
    # way -- a webapp that happens to publish is still judged on whether anyone
    # opens it, which is what --access-log measures.
    if 'signalk-webapp' in keywords:
        return 'webapp'
    if published:
        return 'publishing'
    if any(h in pid.lower() for h in EXPORTER_HINTS):
        return 'exporter'
    if any(h in pid.lower() for h in ACTOR_HINTS):
        return 'actor'
    return 'unmatched'


# Matches the request lines SignalK's express logger emits, scoped
# (@meri-imperiumi/signalk-logbook) and unscoped (galadrielmap_sk) alike.
WEBAPP_REQ = re.compile(r'GET /(@[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+|[A-Za-z0-9_.-]+)')

# Request prefixes that are the server itself, not a webapp being opened.
NOT_A_WEBAPP = ('skServer', 'signalk', 'plugins', 'favicon.ico', 'data',
                'admin', 'apple-touch-icon', 'manifest.json', 'robots.txt')


def webapp_loads(stream):
    """Count webapp opens from a stream of server request-log lines.

    Deliberately reads a stream rather than calling journalctl: the boat runs
    SignalK under systemd and the dev box runs it in a container, so the caller
    pipes in whichever of these applies --

        journalctl -u signalk --since '7 days ago' | ... --access-log -
        docker logs signalk-server 2>&1 | ... --access-log -

    Read the result as positive evidence only. A webapp with loads is being
    used. A webapp with none is unproven, not unused: the count only covers
    however far back the log happens to reach, which on the boat is whatever
    journald has not yet rotated away.
    """
    counts = collections.Counter()
    for line in stream:
        for m in WEBAPP_REQ.finditer(line):
            name = m.group(1)
            if name.split('/')[0] in NOT_A_WEBAPP:
                continue
            counts[name] += 1
    return counts


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--url', default='http://localhost:3000')
    ap.add_argument('--token', default='')
    ap.add_argument('--out', help='write JSON census here (default: stdout summary only)')
    ap.add_argument('--model', help='read a saved data model instead of fetching')
    ap.add_argument('--plugins', help='read a saved /skServer/plugins instead of fetching')
    ap.add_argument('--access-log', metavar='FILE',
                    help="server request log to count webapp opens from; '-' for stdin. "
                         "Positive evidence only -- see webapp_loads().")
    args = ap.parse_args()

    loads = collections.Counter()
    if args.access_log:
        fh = sys.stdin if args.access_log == '-' else open(args.access_log, errors='ignore')
        loads = webapp_loads(fh)

    model = (json.load(open(args.model)) if args.model
             else api(args.url, args.token, '/signalk/v1/api/'))
    plugins = (json.load(open(args.plugins)) if args.plugins
               else api(args.url, args.token, '/skServer/plugins'))

    paths_by_source = collections.Counter()
    newest = {}
    for _, source, ts in leaves(self_vessel(model)):
        paths_by_source[source] += 1
        if ts and (source not in newest or ts > newest[source]):
            newest[source] = ts

    census = {}
    for p in plugins:
        pid = p['id']
        data = p.get('data') or {}
        keywords = p.get('keywords') or []
        published = sum(n for s, n in paths_by_source.items() if pid in s)
        cfg = data.get('configuration') or {}
        census[pid] = {
            'package': p.get('packageName'),
            'version': p.get('version'),
            'enabled': bool(data.get('enabled')),
            'configured_values': len(json.dumps(cfg)) > 2,
            'is_webapp': 'signalk-webapp' in keywords,
            'paths_published': published,
            'status_message': (p.get('statusMessage') or '').strip() or None,
            'bucket': classify(pid, keywords, published) if data.get('enabled') else 'disabled',
            'webapp_loads': loads.get(p.get('packageName') or pid) or loads.get(pid) or 0,
        }

    explained = {s for s in paths_by_source
                 if any(pid in s for pid in census)}
    unattributed = sorted(set(paths_by_source) - explained,
                          key=lambda s: -paths_by_source[s])

    out = {
        'generated': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'server_version': model.get('version'),
        'plugins': census,
        'sources': dict(paths_by_source.most_common()),
        'unattributed_sources': {s: paths_by_source[s] for s in unattributed},
    }

    buckets = collections.Counter(v['bucket'] for v in census.values())
    print("plugins: %d   %s" % (
        len(census), '  '.join('%s=%d' % kv for kv in sorted(buckets.items()))))
    print("\nunmatched (enabled, not a webapp, not an exporter, publishes nothing"
          " under its own id):")
    for pid, v in sorted(census.items()):
        if v['bucket'] == 'unmatched':
            print("  %-36s configured=%s" % (pid, v['configured_values']))
    if args.access_log:
        print("\nwebapps, by opens in the supplied log (absence is unproven, not unused):")
        apps = sorted(((v['webapp_loads'], k) for k, v in census.items() if v['is_webapp']),
                      reverse=True)
        for n, pid in apps:
            print("  %-40s %s" % (pid, n or '-- none seen --'))

    print("\nsource names no plugin id explains -- renamed publishers hide here:")
    for s in unattributed[:25]:
        print("  %-52s %4d paths" % (s, paths_by_source[s]))

    if args.out:
        with open(args.out, 'w') as fh:
            json.dump(out, fh, indent=1, sort_keys=True)
        print("\nwrote %s" % args.out)
    return 0


if __name__ == '__main__':
    sys.exit(main())

# syntax=docker/dockerfile:1
#
# pypilot -- the autopilot daemon and its web UI, containerised.
#
# Built, not pulled: upstream publishes no image. Everything is pinned to one
# commit so a rebuild months from now produces the same software; bump
# PYPILOT_REF deliberately, never float it to master.
#
# Two heavy things happen at build time and must not happen at run time:
# pypilot's own C++/SWIG extensions (linebuffer, arduino_servo, ugfx,
# spireader) and RTIMULib2, which pypilot pulls straight from git and which
# has no wheel for any architecture.

ARG PYTHON_VERSION=3.11

FROM python:${PYTHON_VERSION}-slim-bookworm AS build

# Pinned to pypilot master as of 2026-07-16. The boat's OpenPlotter install
# reports version 0.56; this tree is that line's current head.
ARG PYPILOT_REF=a395789cb1924df92cffc5b8f45f9329bc3d297a

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential swig git pkg-config ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH

# Clone rather than `pip install git+...` because of a real packaging trap:
# setup.py runs SWIG from a `cmdclass` hooked onto the *install* command, which
# modern pip never invokes (it builds a wheel). Installing straight from the
# git URL therefore ships the compiled `_linebuffer.so` but not the SWIG-
# generated `linebuffer.py` wrapper beside it, and pypilot dies on its first
# pipe with `NameError: name 'linebuffer' is not defined`. Running build_ext
# in the source tree first generates the wrappers where the wheel build can
# see them. Verified: without this, the container exits at startup.
RUN git clone https://github.com/pypilot/pypilot /src \
    && git -C /src checkout --detach ${PYPILOT_REF} \
    && cd /src && python setup.py build_ext --inplace

# Extras: optimize (ujson/pyudev/inotify -- faster serial probing and json),
# signalk (requests/websocket-client, the pypilot -> SignalK push), web (the
# :8000 UI and the websocket the SignalK autopilot-provider plugin talks to).
# Deliberately absent: hat (LCD/GPIO front panel, needs libgpiod) and ui
# (wxPython desktop apps). Neither is aboard.
WORKDIR /src
RUN pip install --no-cache-dir ".[optimize,signalk,web]"


FROM python:${PYTHON_VERSION}-slim-bookworm

# sudo + util-linux: pypilot raises its own scheduling priority by shelling out
# to `sudo -n chrt -f -p 1 <pid>` (autopilot.py, boatimu.py). Both binaries must
# exist or every start logs "failed to make autopilot process realtime" and the
# control loop runs at ordinary priority. See compose-pypilot.yml for the
# cap_add/ulimits that make the call actually succeed.
# i2c-tools: `i2cdetect -y 1` from inside the container is the one check that
# distinguishes "no IMU wired" from "container cannot see the bus".
RUN apt-get update && apt-get install -y --no-install-recommends \
        sudo util-linux i2c-tools libstdc++6 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=build /opt/venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    HOME=/root

# pypilot reads RTIMULib.ini -- the compass calibration -- from its *working
# directory*, not from ~/.pypilot. OpenPlotter's units set
# WorkingDirectory=/home/pi/.pypilot for exactly this reason; the units in
# pypilot's own repo do not, and lose the calibration silently. Keep these two
# paths the same and the mounted volume holds both.
WORKDIR /root/.pypilot

EXPOSE 8000 20220 23322

CMD ["pypilot"]

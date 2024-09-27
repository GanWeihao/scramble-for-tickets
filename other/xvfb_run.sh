#!/bin/bash
if ! xdpyinfo 2>/dev/null | grep "Xvfb" > /dev/null; then
  Xvfb :99 -screen 0 1920x1080x24 &
  export DISPLAY=:99
fi
#!/bin/bash

# Exit if something fails
set -e

rm ~/.local/share/kservices5/plasma-runner-zoom.desktop
rm ~/.local/share/dbus-1/services/com.github.krunner-zoom.service
kquitapp5 krunner

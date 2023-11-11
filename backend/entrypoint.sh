#!/bin/sh
# Taken from https://github.com/marissa999/decky-recorder
set -e

OUTDIR="/backend/out"
cd /backend
cp -r /pacman/usr/lib/* /backend/out

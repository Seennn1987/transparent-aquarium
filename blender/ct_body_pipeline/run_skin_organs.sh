#!/bin/bash
cd "$(dirname "$0")"
timeout 3000 python3 skinbody.py > skinbody.log 2>&1 || { echo FAIL skinbody; tail -5 skinbody.log; exit 1; }
for f in organs_cav.py organs.py organs_mesh.py eyes_mesh.py hyoidcart_mesh.py pack_soft.py; do timeout 1500 python3 $f > ${f%.py}.log 2>&1 || { echo FAIL $f; tail -5 ${f%.py}.log; exit 1; }; done
echo DONE

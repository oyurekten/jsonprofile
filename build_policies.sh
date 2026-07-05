#!/bin/bash

cd mztab_m_io/resources/opa_policies
opa build -t wasm \
  --ignore tests \
  --ignore mztabm/policies/input.json \
  -e mztabm/policies \
  -o ../mztabm-default-2.1.0-M.wasm .

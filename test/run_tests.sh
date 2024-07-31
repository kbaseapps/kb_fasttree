#!/bin/bash
script_dir=$(dirname "$(readlink -f "$0")")
export KB_DEPLOYMENT_CONFIG=$script_dir/../deploy.cfg
export KB_AUTH_TOKEN=`cat /kb/module/work/token`
export PYTHONPATH=$script_dir/../lib:$PATH:$PYTHONPATH

# run without collecting coverage data
# pytest -vv test

# collect coverage data
pytest \
    --cov=lib/ \
    --cov-config=.coveragerc \
    --cov-report=html \
    --cov-report=xml \
    test

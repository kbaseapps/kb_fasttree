#!/bin/bash
script_dir=$(dirname "$(readlink -f "$0")")
export PYTHON_LIB_DIR=$script_dir/../lib
export KB_DEPLOYMENT_CONFIG=$script_dir/../deploy.cfg
export KB_AUTH_TOKEN=`cat /kb/module/work/token`
export PYTHONPATH=$PYTHON_LIB_DIR:$PYTHONPATH

# run without collecting coverage data
# pytest -vv test

# collect coverage data
pytest \
    --cov-config=.coveragerc \
    --cov-report=html \
    --cov-report=xml \
    --cov=/kb/module/lib \
    -vv \
    test

echo "Finished tests!"

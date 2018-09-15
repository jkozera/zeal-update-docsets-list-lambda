#!/bin/bash

set -ex

rm -rf build
pip install . -t build/update-docsets
rm -rf build/update-docsets/dulwich*
pip install --no-dependencies --force-reinstall dulwich --global-option="--pure"  -t build/update-docsets
(cd build/update-docsets; zip -r ../update-docsets.zip .)
aws lambda update-function-code --function-name update-docsets --zip-file fileb://build/update-docsets.zip

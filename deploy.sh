#!/bin/bash

set -ex

if [ "$1" = "ziponly" ]; then
    rm -rf build
    pip3.6 install . -t build/update-docsets
    rm -rf build/update-docsets/dulwich*
    pip3.6 install --no-dependencies --force-reinstall dulwich --global-option="--pure"  -t build/update-docsets
    (cd build/update-docsets; zip -r ../update-docsets.zip .)
else
    rm -f update-docsets.zip
    docker build . -t zevdocs-update-docsets-lambda
    IMAGE=$(docker create zevdocs-update-docsets-lambda)
    docker cp $IMAGE:/zevdocs-update-docsets-lambda/build/update-docsets.zip .
    docker rm $IMAGE
    aws lambda update-function-code --function-name update-docsets --zip-file fileb://update-docsets.zip
fi

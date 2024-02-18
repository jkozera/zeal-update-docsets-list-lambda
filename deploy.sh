#!/bin/bash

set -ex

if [ "$1" = "ziponly" ]; then
    rm -rf build
    pip3.12 install . -t build/update-docsets
    rm -rf build/update-docsets/dulwich*
    pip3.12 install --no-dependencies --force-reinstall dulwich -t build/update-docsets
    (cd build/update-docsets; zip -r ../update-docsets.zip .)
else
    rm -f update-docsets.zip
    podman build . -t zevdocs-update-docsets-lambda
    IMAGE=$(podman create zevdocs-update-docsets-lambda)
    podman cp $IMAGE:/zevdocs-update-docsets-lambda/build/update-docsets.zip .
    podman rm $IMAGE
    aws lambda update-function-code --function-name update-docsets --zip-file fileb://update-docsets.zip
fi

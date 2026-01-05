#!/bin/bash

# ask for confirmation
read -p "This will update the RC car firmware. Are you sure? (y/n) " -n 1 -r
echo    # move to a new line
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
fi

curl -X POST http://192.168.4.1/update -H "Content-Type: application/octet-stream" --data-binary @ota.tar.gz
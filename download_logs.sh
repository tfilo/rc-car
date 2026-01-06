#!/bin/bash

# curl to download logs from the RC car
curl -X GET http://192.168.4.1/log.txt -o log.txt
curl -X GET http://192.168.4.1/log.old.txt -o log.old.txt
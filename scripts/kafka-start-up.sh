#!/bin/bash
echo 'removing meta.properties'
rm -rf /kafka/kafka-logs-kafka/meta.properties

echo 'starting kafka'
start-kafka.sh

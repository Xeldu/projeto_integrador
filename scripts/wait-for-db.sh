#!/bin/sh
# Usage: wait-for-db.sh host port -- command
HOST=$1
PORT=$2
shift 2

echo "Waiting for $HOST:$PORT..."
while ! nc -z "$HOST" "$PORT"; do
  sleep 1
done
echo "$HOST:$PORT is up"
exec "$@"

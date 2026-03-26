CREATE TABLE IF NOT EXISTS readings (
    id          SERIAL PRIMARY KEY,
    device_id   VARCHAR(64)    NOT NULL,
    temperature NUMERIC(6, 2)  NOT NULL,
    timestamp   TIMESTAMPTZ    NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_readings_timestamp  ON readings (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_readings_device_id  ON readings (device_id);

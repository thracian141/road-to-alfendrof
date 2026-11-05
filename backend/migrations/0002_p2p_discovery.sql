ALTER TABLE rooms ADD COLUMN public INTEGER NOT NULL DEFAULT 0 CHECK(public IN (0,1));
CREATE INDEX matchmaking ON rooms(public,mode,build,expires);

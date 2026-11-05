# Multiplayer backend

Cloudflare Worker with D1 accounts/friends and hibernating Durable Objects for
presence and private 1v1/2v2 WebSocket rooms. The Rust game currently uses its
existing UDP transport; the desktop login, friends menu, and WebSocket/GGRS
adapter are not yet integrated. A passing backend test is not a playable online
match in the game.

## Development

From the repository root, enter `nix develop path:$PWD/nix`, then:

```sh
cd backend
npm ci
npm run types
npm run check
npm test
npx wrangler d1 migrations apply DB --local
npm run dev
```

Tests use `.wrangler/test` and synthetic accounts, never the remote database.
Do not run `test/seed.sql` against a remote binding. Local OAuth settings belong
in the ignored `.dev.vars` file; see `.dev.vars.example`. Never commit secrets.

## Deployed resources

- Worker: `alfendrof-multiplayer`
- Origin: `https://alfendrof-multiplayer.important-762.workers.dev`
- D1: `alfendrof-social` (WEUR)
- Durable Objects: `Room`, `Presence`, both SQLite-backed
- Health: `GET /health`

These resources use the Free plan allowances; quotas still apply. This project
does not enable a paid plan. Each API call can read/write D1, while gameplay
packets stay in the room Durable Object. Incoming WebSocket messages count
toward Durable Object limits. See [Cloudflare pricing](https://developers.cloudflare.com/durable-objects/platform/pricing/).

## Configure Discord

1. Create an application named **Road to Alfendrof** in the
   [Discord Developer Portal](https://discord.com/developers/applications).
2. Add the OAuth2 redirect:
   `https://alfendrof-multiplayer.important-762.workers.dev/auth/discord/callback`.
3. Put the public Application ID in `vars.DISCORD_CLIENT_ID` in
   `wrangler.jsonc`, and run `npm run types`.
4. Run `npx wrangler secret put DISCORD_CLIENT_SECRET` and enter the secret at
   the hidden terminal prompt. Never paste it into chat or a shell command.
5. Run `npm run check`, `npm test`, then `npm run deploy`.

Only the `identify` scope is requested. No bot, privileged intents, Discord
friend permissions, or Discord guild membership is required. Game friends are
managed separately by friend codes. Discord access tokens are used transiently
to retrieve the profile and are not stored.

Deployment commands target the account and resources in `wrangler.jsonc`:

```sh
npx wrangler d1 migrations apply DB --remote
npm run deploy
```

## Client protocol (version 1)

All JSON APIs require `Content-Type: application/json`. Authenticated calls
and native WebSocket upgrades carry `Authorization: Bearer <access_token>`.
Tokens must not be placed in URLs or logs. The service returns JSON errors
with an appropriate HTTP status; login is 503 until Discord is configured.

### Login

`POST /auth/device` returns `device_token`, `verification_uri`, `expires_in`
and polling `interval`. Keep the secret device token only in the client; open
the verification URI in the browser. Poll `POST /auth/device/claim` with
`{"device_token":"..."}` every three seconds. A 202 means pending; a 200
returns a one-time claim of a 30-day bearer token; a 410 means expired or
already claimed. Persist the bearer token in the operating system keychain.
The browser never receives the game bearer token. `POST /v1/logout` revokes
the session and closes that user's current connections.

### Friends and presence

| Endpoint | Purpose |
| --- | --- |
| `GET /v1/me` | Player ID, name, friend code |
| `GET /v1/friends` | Pending/accepted friendships and current presence |
| `POST /v1/friends` | Request using `{"friend_code":"..."}` |
| `POST /v1/friends/:id/accept` | Accept an incoming request |
| `DELETE /v1/friends/:id` | Remove a friendship/request |
| `POST /v1/blocks` | Block using `{"user_id":"..."}` |
| `GET /v1/events` (WebSocket) | `friend_request`, `friend_accepted`, `room_invite` |
| `GET /v1/invites` | Pending room invitations |

Presence is queried on refresh; it is not a continuous online/offline feed.
Send text `ping` for an automatic `pong`. Reconnect with backoff on failure.
Each player has one current presence connection and at most 32 friendships.

### Private rooms

Create using `POST /v1/rooms` with `{"mode":"1v1","build":"<fingerprint>"}`
or mode `2v2`. Use an exact simulation/protocol fingerprint for `build`, not
just a display version. The owner occupies slot 0. Invite accepted friends
using `POST /v1/rooms/:id/invite` with `{"user_id":"..."}`; invitees call
`POST /v1/rooms/:id/join`. `GET /v1/rooms/:id` returns members and slots.
The host closes the room using `DELETE /v1/rooms/:id`.

Connect to `/v1/rooms/:id/ws?build=<fingerprint>` using an authenticated native
WebSocket upgrade. The server assigns player IDs and slots. In 2v2, use teams
`[0,1,0,1]` to match the game's local mode. Client messages:

```json
{"type":"pick","character":0}
{"type":"ready","ready":true}
{"type":"packet","to":1,"payload":"<base64 GGRS packet>"}
```

The server sends `hello`, `players`, `start`, `left`, and `packet` messages.
Read the authoritative slot from `hello`; all players must be ready before
`start`. Relay packets only after `start`; received packets contain a
server-owned `from` slot. Route decoded bytes into a native GGRS socket
adapter. The server relays packets and coordinates the lobby; it does not
simulate combat or validate outcomes. TCP/WebSocket transport characteristics
differ from the game's existing UDP transport and need real match testing.

Rooms expire after three hours; invites and login requests after ten minutes.
Room messages are capped at 240/second per connection, with base64 packet
payloads up to 5464 characters. A disconnected match should return to the
lobby; resumable live matches are not supported by this protocol.

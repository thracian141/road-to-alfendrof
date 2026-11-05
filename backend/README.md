# Multiplayer backend

Cloudflare handles Discord accounts, game friends, presence, matchmaking and UDP
connection discovery. Combat inputs and rollback snapshots never pass through
Cloudflare: the native game uses a direct GGRS UDP mesh (two peers for 1v1,
four for 2v2). There is no gameplay relay or relay fallback.

In the game, open **Online**, sign in with Discord, then choose **Find players**
or host a private room and invite accepted friends. Each player selects a
fighter; the match starts once every player is ready and every direct UDP path
has been discovered. The operating system credential store holds the session.
Direct connection / LAN remains available without an account.

## Development

From the repository root, enter `nix develop path:$PWD/nix`, then:

```sh
cd backend
npm ci
npm run types
npm run check
npm test
npm run test:native
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
does not enable a paid plan. API calls can read/write D1. Room Durable Objects store pre-match
connection details and readiness; presence notifications can use WebSockets. See [Cloudflare pricing](https://developers.cloudflare.com/durable-objects/platform/pricing/).

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

## Client protocol (version 2)

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
| `POST /v1/presence` | Renew a 60-second online lease (native client: every 25 seconds) |
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

`POST /v1/matchmaking` with the same mode/build body atomically finds or creates
a public room and returns `{id,slot}`. Full, already-started, blocked-player,
and mismatched-build rooms are excluded. In 2v2 the slot teams are `[0,1,0,1]`.
Use `POST /v1/rooms/:id/leave` to cancel a search or leave a room; a host leaving
closes the room for everyone. Matchmaking is unranked and has no region filter.

Exchange pre-match connection information using `POST /v1/rooms/:id/signal`:

```json
{"build":"<fingerprint>","character":0,"ready":false,"candidates":["203.0.113.1:7777","192.168.1.10:7777"]}
```

The server owns player IDs/slots. Each member can update only their own
candidates, fighter and readiness. `GET /v1/rooms/:id/state` returns `players`,
`members` (names/slots), and `playing`. Poll at most once every 1.5 seconds.
Send candidates before attempting direct UDP probes. The native client reuses
the same UDP socket for STUN, room-scoped probes, and GGRS so NAT mappings
remain valid. It probes public and LAN candidates, learns actual source
addresses, and maps verified route aliases to stable GGRS peer addresses.
Mark ready only after the fighter is locked and every peer is reachable.
When all players are ready, `playing` becomes true and no more signaling is
accepted. Combat then uses UDP exclusively; the discovery room is not needed
to run the match. The old room WebSocket/packet-relay endpoint is removed.

After all peers arrive, a direct connectivity failure times out after 30
seconds. Some symmetric NAT/CGNAT or firewall configurations cannot establish
direct UDP; use a suitable network or port forwarding. There is no TURN,
WebSocket, or other gameplay relay fallback. A disconnected combat peer ends
the session; live match reconnection is not implemented.

Private rooms expire after three hours; matchmaking rooms after one hour;
invites and login requests after ten minutes. Discovery requests remain
subject to API limits. The native client polls friends/invitations every eight
seconds in the lobby and renews its presence lease independently of gameplay.

## Validation

`npm test` exercises authentication, friends, blocking, private discovery,
concurrent four-slot matchmaking and absence of the packet relay. The separate
`npm run test:native` starts an isolated local Worker and runs the actual Rust
HTTP/UDP client test. Four fixture accounts discover a room, exchange UDP
candidates and probe each other, then close the backend room **before** running
a four-player GGRS match. This proves local integration and direct transport;
it does not establish connectivity across every real internet NAT topology.

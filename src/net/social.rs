//! Account and discovery HTTP work runs off the game thread. No combat data uses this service.
use serde_json::{json, Value};
use std::sync::{mpsc, Mutex};
use std::time::{Duration, Instant};

pub const ORIGIN: &str = "https://alfendrof-multiplayer.important-762.workers.dev";
pub enum Command {
    Login,
    Logout,
    Call {
        tag: String,
        method: &'static str,
        path: String,
        body: Option<Value>,
    },
}
pub struct Reply {
    pub tag: String,
    pub result: Result<Value, String>,
}
pub struct Service {
    tx: mpsc::SyncSender<Command>,
    rx: Mutex<mpsc::Receiver<Reply>>,
}
impl Service {
    pub fn new() -> Self {
        let origin = std::env::var("ALFENDROF_BACKEND_URL").unwrap_or_else(|_| ORIGIN.into());
        let (tx, commands) = mpsc::sync_channel(16);
        let (replies, rx) = mpsc::channel();
        std::thread::spawn(move || worker(origin, commands, replies));
        Self {
            tx,
            rx: Mutex::new(rx),
        }
    }
    pub fn send(&self, command: Command) -> bool {
        self.tx.try_send(command).is_ok()
    }
    pub fn call(
        &self,
        tag: impl Into<String>,
        method: &'static str,
        path: impl Into<String>,
        body: Option<Value>,
    ) -> bool {
        self.send(Command::Call {
            tag: tag.into(),
            method,
            path: path.into(),
            body,
        })
    }
    pub fn drain(&self) -> Vec<Reply> {
        self.rx.lock().expect("social replies").try_iter().collect()
    }
}
impl Default for Service {
    fn default() -> Self {
        Self::new()
    }
}
struct Api {
    origin: String,
    token: Option<String>,
    agent: ureq::Agent,
}
impl Api {
    fn call(&self, method: &str, path: &str, body: Option<Value>) -> Result<(u16, Value), String> {
        let url = format!("{}{}", self.origin, path);
        let auth = self
            .token
            .as_ref()
            .map(|s| format!("Bearer {s}"))
            .unwrap_or_default();
        let r = match method {
            "POST" => self
                .agent
                .post(&url)
                .header("Authorization", &auth)
                .send_json(body.unwrap_or(json!({}))),
            "DELETE" => self
                .agent
                .delete(&url)
                .header("Authorization", &auth)
                .call(),
            _ => self.agent.get(&url).header("Authorization", &auth).call(),
        }
        .map_err(|_| "Cannot reach the friends service. Check your connection.".to_string())?;
        let status = r.status().as_u16();
        let mut r = r;
        let value = r
            .body_mut()
            .with_config()
            .limit(128 * 1024)
            .read_json::<Value>()
            .map_err(|_| "The friends service returned an invalid response.".to_string())?;
        if status >= 400 {
            return Err(format!(
                "HTTP {status}: {}",
                value["error"].as_str().unwrap_or("Request failed")
            ));
        }
        Ok((status, value))
    }
}
fn credential(origin: &str) -> Result<keyring::Entry, keyring::Error> {
    keyring::Entry::new("Road to Alfendrof multiplayer", origin)
}
fn worker(origin: String, commands: mpsc::Receiver<Command>, replies: mpsc::Sender<Reply>) {
    // Permit HTTP only for an explicitly selected local development server.
    if !(origin.starts_with("https://")
        || origin.starts_with("http://127.0.0.1:")
        || origin.starts_with("http://localhost:"))
    {
        let _ = replies.send(Reply {
            tag: "error".into(),
            result: Err("Invalid backend URL".into()),
        });
        return;
    }
    let agent = ureq::Agent::config_builder()
        .timeout_global(Some(Duration::from_secs(10)))
        .user_agent(format!("RoadToAlfendrof/{}", env!("CARGO_PKG_VERSION")))
        .http_status_as_error(false)
        .build()
        .into();
    let mut api = Api {
        token: credential(&origin).ok().and_then(|e| e.get_password().ok()),
        origin,
        agent,
    };
    let send = |tag: &str, result| {
        let _ = replies.send(Reply {
            tag: tag.into(),
            result,
        });
    };
    if api.token.is_some() {
        send("me", api.call("GET", "/v1/me", None).map(|(_, v)| v));
    }
    let mut heartbeat = Instant::now() - Duration::from_secs(30);
    let mut login: Option<(String, Instant, Instant)> = None;
    loop {
        match commands.recv_timeout(Duration::from_millis(100)) {
            Ok(Command::Login) => match api.call("POST", "/auth/device", None) {
                Ok((_, v)) => {
                    if let (Some(secret), Some(uri)) =
                        (v["device_token"].as_str(), v["verification_uri"].as_str())
                    {
                        login = Some((
                            secret.into(),
                            Instant::now() + Duration::from_secs(600),
                            Instant::now(),
                        ));
                        send("browser", Ok(json!({"uri":uri})));
                    }
                }
                Err(e) => send("error", Err(e)),
            },
            Ok(Command::Logout) => {
                login = None;
                let _ = api.call("POST", "/v1/logout", None);
                api.token = None;
                if let Ok(e) = credential(&api.origin) {
                    let _ = e.delete_credential();
                }
                send("logout", Ok(json!({})));
            }
            Ok(Command::Call {
                tag,
                method,
                path,
                body,
            }) => {
                let result = api.call(method, &path, body).map(|(_, v)| v);
                if result
                    .as_ref()
                    .err()
                    .is_some_and(|e| e.starts_with("HTTP 401:"))
                {
                    api.token = None;
                    if let Ok(e) = credential(&api.origin) {
                        let _ = e.delete_credential();
                    }
                    send("logout", Ok(json!({})));
                }
                send(&tag, result);
            }
            Err(mpsc::RecvTimeoutError::Disconnected) => return,
            Err(mpsc::RecvTimeoutError::Timeout) => {}
        }
        if api.token.is_some() && heartbeat.elapsed() > Duration::from_secs(25) {
            heartbeat = Instant::now();
            let _ = api.call("POST", "/v1/presence", None);
        }
        if let Some((secret, deadline, next)) = login.as_mut() {
            if Instant::now() >= *deadline {
                login = None;
                send("error", Err("Discord sign-in expired. Try again.".into()));
                continue;
            }
            if Instant::now() < *next {
                continue;
            }
            *next = Instant::now() + Duration::from_secs(3);
            match api.call(
                "POST",
                "/auth/device/claim",
                Some(json!({"device_token":secret})),
            ) {
                Ok((202, _)) => {}
                Ok((_, v)) => {
                    api.token = v["access_token"].as_str().map(String::from);
                    if let Some(token) = &api.token {
                        if credential(&api.origin)
                            .and_then(|e| e.set_password(token))
                            .is_err()
                        {
                            send(
                                "error",
                                Err("Signed in for this run; credential store unavailable.".into()),
                            );
                        }
                    }
                    login = None;
                    send("me", api.call("GET", "/v1/me", None).map(|(_, v)| v));
                }
                Err(e) => {
                    login = None;
                    send("error", Err(e));
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    #[ignore = "requires the local backend native fixture on port 8790"]
    fn native_discovery_then_direct_four_player_combat() {
        use crate::{
            net::{self, lobby::Lobby, NetInput},
            sim::{CharacterData, GameState, Input},
        };
        use ggrs::{GgrsEvent, SessionState};
        use std::net::SocketAddr;
        let origin = std::env::var("ALFENDROF_NATIVE_TEST_URL").expect("local fixture URL");
        assert!(origin.starts_with("http://127.0.0.1:"));
        let clients = (1..=4)
            .map(|i| Api {
                origin: origin.clone(),
                token: Some(i.to_string().repeat(64)),
                agent: ureq::Agent::config_builder()
                    .http_status_as_error(false)
                    .build()
                    .into(),
            })
            .collect::<Vec<_>>();
        let rooms = clients
            .iter()
            .map(|api| {
                api.call(
                    "POST",
                    "/v1/matchmaking",
                    Some(json!({"mode":"2v2","build":"native-p2p-fixture"})),
                )
                .unwrap()
                .1
            })
            .collect::<Vec<_>>();
        let id = rooms[0]["id"].as_str().unwrap();
        assert!(rooms.iter().all(|r| r["id"] == id));
        let mut lobbies = (0..4)
            .map(|_| Lobby::new(0, 0, false).unwrap())
            .collect::<Vec<_>>();
        let addresses = lobbies
            .iter()
            .map(|l| format!("127.0.0.1:{}", l.port()).parse().unwrap())
            .collect::<Vec<SocketAddr>>();
        for (slot, api) in clients.iter().enumerate() {
            api.call("POST",&format!("/v1/rooms/{id}/signal"),Some(json!({"build":"native-p2p-fixture","character":0,"ready":false,"candidates":[addresses[slot].to_string()]}))).unwrap();
        }
        let state = clients[0]
            .call("GET", &format!("/v1/rooms/{id}/state"), None)
            .unwrap()
            .1;
        assert_eq!(state["players"].as_array().unwrap().len(), 4);
        let mut seen = [[false; 4]; 4];
        let started = Instant::now();
        while (0..4).any(|i| (0..4).any(|j| i != j && !seen[i][j]))
            && started.elapsed() < Duration::from_secs(3)
        {
            for (i, lobby) in lobbies.iter_mut().enumerate() {
                for j in 0..4 {
                    if i != j {
                        lobby.probe(id, i, addresses[j]);
                    }
                }
                for (from, p) in lobby.poll_probes() {
                    if p.room == id && p.slot < 4 && from == addresses[p.slot] {
                        seen[i][p.slot] = true;
                    }
                }
            }
            std::thread::sleep(Duration::from_millis(2));
        }
        assert!((0..4).all(|i| (0..4).all(|j| i == j || seen[i][j])));
        for api in &clients {
            api.call("POST",&format!("/v1/rooms/{id}/signal"),Some(json!({"build":"native-p2p-fixture","character":0,"ready":true,"candidates":["127.0.0.1:7777"]}))).unwrap();
        }
        assert_eq!(
            clients[0]
                .call("GET", &format!("/v1/rooms/{id}/state"), None)
                .unwrap()
                .1["playing"],
            true
        );
        // Close the discovery room before starting combat: no backend connection is needed now.
        clients[0]
            .call("DELETE", &format!("/v1/rooms/{id}"), None)
            .unwrap();
        let mut sessions = lobbies
            .into_iter()
            .enumerate()
            .map(|(slot, l)| net::start_mesh(l.into_direct_socket(), slot, &addresses).unwrap())
            .collect::<Vec<_>>();
        let mut states = (0..4).map(|_| GameState::team_match()).collect::<Vec<_>>();
        let c =
            CharacterData::from_ron(&std::fs::read_to_string("assets/characters/ayz.ron").unwrap())
                .unwrap();
        let started = Instant::now();
        while states.iter().any(|s| s.frame < 180) && started.elapsed() < Duration::from_secs(15) {
            for (slot, session) in sessions.iter_mut().enumerate() {
                session.poll_remote_clients();
                for e in session.events() {
                    assert!(!matches!(
                        e,
                        GgrsEvent::DesyncDetected { .. } | GgrsEvent::Disconnected { .. }
                    ));
                }
                if session.current_state() == SessionState::Running && states[slot].frame < 180 {
                    session
                        .add_local_input(slot, NetInput(Input::RIGHT))
                        .unwrap();
                    if let Ok(requests) = session.advance_frame() {
                        net::handle_requests(&mut states[slot], requests, [&c; 4]);
                    }
                }
            }
            std::thread::sleep(Duration::from_millis(2));
        }
        assert!(states.iter().all(|s| s.frame == 180));
    }
}

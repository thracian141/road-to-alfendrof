//! Friends, discovery and the pre-match UDP rendezvous. Combat is exclusively peer to peer.
use crate::{AppState, Mode, Roster, Selection};
use bevy::input::{keyboard::KeyboardInput, ButtonState};
use bevy::prelude::*;
use serde_json::{json, Value};
use std::{
    net::SocketAddr,
    sync::{mpsc, Mutex},
    time::{Duration, Instant},
};
use t2f::net::{
    self,
    lobby::Lobby,
    social::{Command, Service},
};

pub struct SocialPlugin;
impl Plugin for SocialPlugin {
    fn build(&self, app: &mut App) {
        app.init_resource::<Social>()
            .add_systems(OnEnter(AppState::Social), spawn)
            .add_systems(
                Update,
                (drive, screen.run_if(in_state(AppState::Social))).chain(),
            )
            .add_systems(OnEnter(AppState::Title), leave_on_title);
    }
}
#[derive(Clone)]
enum Page {
    Home,
    Friends,
    Invites,
    Friend(Value),
}
struct Room {
    id: String,
    slot: usize,
    count: usize,
    peers: Vec<Value>,
    names: [String; 4],
    addresses: [Option<SocketAddr>; 4],
    aliases: [Vec<SocketAddr>; 4],
    udp: Option<Lobby>,
    opening: Option<Mutex<mpsc::Receiver<std::io::Result<Lobby>>>>,
    last_signal: Value,
    playing: bool,
}
#[derive(Resource)]
pub struct Social {
    service: Service,
    me: Option<Value>,
    friends: Vec<Value>,
    invites: Vec<Value>,
    room: Option<Room>,
    page: Page,
    cursor: usize,
    status: String,
    typed: String,
    editing: bool,
    palette: usize,
    last_poll: Instant,
    last_probe: Instant,
    pending_pick: Option<usize>,
    picked_at: Option<Instant>,
    busy: bool,
    generation: u64,
}
impl Default for Social {
    fn default() -> Self {
        Self {
            service: {
                let service = Service::new();
                if std::env::args().any(|a| a == "--discord-login") {
                    service.send(Command::Login);
                }
                service
            },
            me: None,
            friends: vec![],
            invites: vec![],
            room: None,
            page: Page::Home,
            cursor: 0,
            status: String::new(),
            typed: String::new(),
            editing: false,
            palette: 0,
            last_poll: Instant::now() - Duration::from_secs(10),
            last_probe: Instant::now(),
            pending_pick: None,
            picked_at: None,
            busy: false,
            generation: 0,
        }
    }
}
impl Social {
    pub fn in_room(&self) -> bool {
        self.room.is_some()
    }
    pub fn pick(&mut self, index: usize) {
        self.pending_pick = Some(index);
        self.picked_at = Some(Instant::now());
        self.status = "Connecting directly to players...".into();
    }
    pub fn leave(&mut self) {
        self.generation += 1;
        if let Some(r) = self.room.take() {
            self.service
                .call("left", "POST", format!("/v1/rooms/{}/leave", r.id), None);
        }
        self.pending_pick = None;
        self.picked_at = None;
        self.busy = false;
        self.page = Page::Home;
        self.cursor = 0;
    }
    fn refresh(&self) {
        self.service.call("friends", "GET", "/v1/friends", None);
        self.service.call("invites", "GET", "/v1/invites", None);
    }
}
fn leave_on_title(mut social: ResMut<Social>) {
    social.leave();
}
#[derive(Component)]
struct SocialText(usize);
fn spawn(
    mut commands: Commands,
    assets: Res<AssetServer>,
    mut social: ResMut<Social>,
    mut info: ResMut<crate::online::OnlineInfo>,
) {
    if social.room.as_ref().is_some_and(|r| r.udp.is_none()) {
        social.leave();
    }
    if !info.message.is_empty() {
        social.status = std::mem::take(&mut info.message);
    }
    crate::menus::spawn_backdrop(&mut commands, AppState::Social, &assets);
    crate::menus::spawn_panel(&mut commands, AppState::Social);
    for i in 0..9 {
        commands.spawn((
            DespawnOnExit(AppState::Social),
            SocialText(i),
            Text2d::new(""),
            crate::pixel_font(if i == 0 { 14.0 } else { 8.0 }),
            bevy::text::TextLayout::new(bevy::text::Justify::Center, bevy::text::LineBreak::NoWrap),
            TextColor(if i == 0 {
                Color::srgb(1.0, 0.9, 0.4)
            } else {
                Color::WHITE
            }),
            Transform::from_xyz(
                0.0,
                if i == 0 {
                    82.0
                } else if i == 1 {
                    65.0
                } else if i < 8 {
                    44.0 - (i - 2) as f32 * 16.0
                } else if i == 8 {
                    -65.0
                } else {
                    -82.0
                },
                6.0,
            ),
        ));
    }
    crate::menus::spawn_text(
        &mut commands,
        AppState::Social,
        "Enter: select    Esc: back    Ctrl/Cmd+C: copy code".into(),
        8.0,
        Color::srgb(0.65, 0.65, 0.75),
        -93.0,
    );
}
#[derive(Clone)]
enum Action {
    Login,
    Logout,
    Lan,
    Back,
    Find(&'static str),
    Host(&'static str),
    Friends,
    Invites,
    Add,
    Friend(Value),
    Accept(String),
    Remove(String),
    Block(String),
    Invite(String),
    Join(String),
    Pick,
    Leave,
}
fn rows(s: &Social) -> Vec<(String, Action)> {
    if s.me.is_none() {
        return vec![
            ("Sign in with Discord".into(), Action::Login),
            ("Direct connection / LAN".into(), Action::Lan),
            ("Back".into(), Action::Back),
        ];
    }
    match &s.page {
        Page::Friends => {
            let mut r = vec![(
                if s.editing {
                    format!(
                        "Friend code: {} [{}]",
                        s.typed, b"0123456789ABCDEF"[s.palette] as char
                    )
                } else {
                    "Add friend by code".into()
                },
                Action::Add,
            )];
            for f in &s.friends {
                let incoming =
                    f["state"] == "pending" && f["requester"] != s.me.as_ref().unwrap()["id"];
                r.push((
                    format!(
                        "{} {}",
                        if incoming {
                            "Accept:"
                        } else if f["state"] == "pending" {
                            "Sent:"
                        } else {
                            if f["online"].as_bool().unwrap_or(false) {
                                "Online:"
                            } else {
                                "Offline:"
                            }
                        },
                        net::lobby::clean_name(f["name"].as_str().unwrap_or("Player"))
                    ),
                    if incoming {
                        Action::Accept(f["id"].as_str().unwrap_or("").into())
                    } else {
                        Action::Friend(f.clone())
                    },
                ));
            }
            r.push(("Back".into(), Action::Back));
            r
        }
        Page::Invites => {
            let mut r = s
                .invites
                .iter()
                .map(|v| {
                    (
                        format!("Join {} invitation", v["mode"].as_str().unwrap_or("")),
                        Action::Join(v["room_id"].as_str().unwrap_or("").into()),
                    )
                })
                .collect::<Vec<_>>();
            r.push(("Back".into(), Action::Back));
            r
        }
        Page::Friend(v) => {
            let id = v["id"].as_str().unwrap_or("").to_string();
            vec![
                ("Invite to my room".into(), Action::Invite(id.clone())),
                ("Remove friend / request".into(), Action::Remove(id.clone())),
                ("Block player".into(), Action::Block(id)),
                ("Back".into(), Action::Back),
            ]
        }
        Page::Home => {
            if s.room.is_some() {
                vec![
                    ("Choose fighter and ready".into(), Action::Pick),
                    ("Invite a friend".into(), Action::Friends),
                    ("Leave room".into(), Action::Leave),
                ]
            } else {
                vec![
                    ("Find players: 1v1".into(), Action::Find("1v1")),
                    ("Find players: 2v2".into(), Action::Find("2v2")),
                    ("Host private 1v1".into(), Action::Host("1v1")),
                    ("Host private 2v2".into(), Action::Host("2v2")),
                    ("Friends".into(), Action::Friends),
                    (
                        format!("Invitations ({})", s.invites.len()),
                        Action::Invites,
                    ),
                    ("Sign out".into(), Action::Logout),
                    ("Direct connection / LAN".into(), Action::Lan),
                    ("Back".into(), Action::Back),
                ]
            }
        }
    }
}
fn screen(
    mut s: ResMut<Social>,
    nav: Res<crate::MenuInput>,
    keys: Res<ButtonInput<KeyCode>>,
    mut typing: MessageReader<KeyboardInput>,
    roster: Res<Roster>,
    mut mode: ResMut<Mode>,
    mut info: ResMut<crate::online::OnlineInfo>,
    mut next: ResMut<NextState<AppState>>,
    mut labels: Query<(&SocialText, &mut Text2d)>,
) {
    let input = &nav.0;
    let entries = rows(&s);
    s.cursor = s.cursor.min(entries.len().saturating_sub(1));
    if s.editing {
        for ev in typing.read() {
            if ev.state != ButtonState::Pressed {
                continue;
            }
            if ev.key_code == KeyCode::Backspace {
                s.typed.pop();
            } else if let Some(t) = &ev.text {
                for c in t.chars().filter(|c| c.is_ascii_hexdigit()) {
                    if s.typed.len() < 12 {
                        s.typed.push(c.to_ascii_uppercase());
                    }
                }
            }
        }
        if input.just_pressed(KeyCode::ArrowUp) {
            s.palette = (s.palette + 1) % 16;
        }
        if input.just_pressed(KeyCode::ArrowDown) {
            s.palette = (s.palette + 15) % 16;
        }
        if input.just_pressed(KeyCode::ArrowRight) && s.typed.len() < 12 {
            let c = b"0123456789ABCDEF"[s.palette] as char;
            s.typed.push(c);
        }
        if input.just_pressed(KeyCode::ArrowLeft) {
            s.typed.pop();
        }
        if (keys.pressed(KeyCode::ControlLeft) || keys.pressed(KeyCode::SuperLeft))
            && keys.just_pressed(KeyCode::KeyV)
        {
            if let Ok(mut clip) = arboard::Clipboard::new() {
                if let Ok(t) = clip.get_text() {
                    s.typed = t
                        .chars()
                        .filter(|c| c.is_ascii_hexdigit())
                        .take(12)
                        .map(|c| c.to_ascii_uppercase())
                        .collect();
                }
            }
        }
    } else {
        if input.just_pressed(KeyCode::ArrowUp) || input.just_pressed(KeyCode::KeyW) {
            s.cursor = (s.cursor + entries.len() - 1) % entries.len();
        }
        if input.just_pressed(KeyCode::ArrowDown) || input.just_pressed(KeyCode::KeyS) {
            s.cursor = (s.cursor + 1) % entries.len();
        }
    }
    if crate::menus::back_pressed(input) {
        if s.editing {
            s.editing = false;
        } else if matches!(s.page, Page::Home) {
            s.leave();
            next.set(AppState::Title);
        } else {
            s.page = Page::Home;
            s.cursor = 0;
        }
    } else if crate::menus::confirm_pressed(input) && !s.busy {
        let action = entries[s.cursor].1.clone();
        let build = build_of(&roster);
        match action {
            Action::Login => {
                s.service.send(Command::Login);
                s.status = "Approve Discord sign-in in your browser.".into();
            }
            Action::Logout => {
                s.leave();
                s.service.send(Command::Logout);
            }
            Action::Lan => {
                s.leave();
                *mode = Mode::Online;
                next.set(AppState::Online);
            }
            Action::Back => {
                if matches!(s.page, Page::Home) {
                    next.set(AppState::Title);
                } else {
                    s.page = Page::Home;
                    s.cursor = 0;
                }
            }
            Action::Find(mode) | Action::Host(mode) => {
                let path = if matches!(action, Action::Find(_)) {
                    "/v1/matchmaking"
                } else {
                    "/v1/rooms"
                };
                s.generation += 1;
                s.busy = s.service.call(
                    format!("room:{}", s.generation),
                    "POST",
                    path,
                    Some(json!({"mode":mode,"build":build})),
                );
                s.status = "Finding players...".into();
            }
            Action::Friends => {
                s.page = Page::Friends;
                s.cursor = 0;
                s.refresh();
            }
            Action::Invites => {
                s.page = Page::Invites;
                s.cursor = 0;
                s.refresh();
            }
            Action::Add => {
                if s.editing {
                    if s.typed.len() == 12 {
                        s.service.call(
                            "changed",
                            "POST",
                            "/v1/friends",
                            Some(json!({"friend_code":s.typed})),
                        );
                        s.editing = false;
                        s.typed.clear();
                    } else {
                        s.status = "Enter all 12 characters of the friend code.".into();
                    }
                } else {
                    s.editing = true;
                }
            }
            Action::Friend(v) => {
                s.page = Page::Friend(v);
                s.cursor = 0;
            }
            Action::Accept(id) => {
                s.service
                    .call("changed", "POST", format!("/v1/friends/{id}/accept"), None);
            }
            Action::Remove(id) => {
                s.service
                    .call("changed", "DELETE", format!("/v1/friends/{id}"), None);
                s.page = Page::Friends;
                s.cursor = 0;
            }
            Action::Block(id) => {
                s.service
                    .call("changed", "POST", "/v1/blocks", Some(json!({"user_id":id})));
                s.page = Page::Friends;
                s.cursor = 0;
            }
            Action::Invite(id) => {
                if let Some(room) = &s.room {
                    s.service.call(
                        "invited",
                        "POST",
                        format!("/v1/rooms/{}/invite", room.id),
                        Some(json!({"user_id":id})),
                    );
                } else {
                    s.status = "Host a private room first.".into();
                }
            }
            Action::Join(id) => {
                s.generation += 1;
                s.busy = s.service.call(
                    format!("room:{}", s.generation),
                    "POST",
                    format!("/v1/rooms/{id}/join"),
                    None,
                );
            }
            Action::Pick => {
                *mode = Mode::Online;
                info.locked = false;
                next.set(AppState::CharSelect);
            }
            Action::Leave => s.leave(),
        }
    }
    if (keys.pressed(KeyCode::ControlLeft) || keys.pressed(KeyCode::SuperLeft))
        && keys.just_pressed(KeyCode::KeyC)
    {
        if let Some(code) = s.me.as_ref().and_then(|v| v["friend_code"].as_str()) {
            if let Ok(mut c) = arboard::Clipboard::new() {
                let _ = c.set_text(code);
            }
        }
    }
    let entries = rows(&s);
    let first = s.cursor / 6 * 6;
    let header = if let Some(r) = &s.room {
        format!(
            "{} room - Player {} - {}/{} players found",
            if r.count == 4 { "2v2" } else { "1v1" },
            r.slot + 1,
            r.peers.len(),
            r.count
        )
    } else {
        s.me.as_ref()
            .map(|m| {
                format!(
                    "{}  Friend code: {}",
                    net::lobby::clean_name(m["name"].as_str().unwrap_or("Player")),
                    m["friend_code"].as_str().unwrap_or("")
                )
            })
            .unwrap_or_else(|| "Play with friends or find opponents".into())
    };
    let header = format!(
        "{header} [{}/{}]",
        s.cursor / 6 + 1,
        entries.len().div_ceil(6)
    );
    for (label, mut t) in &mut labels {
        t.0 = single_line(
            &match label.0 {
                0 => "Online - peer to peer".into(),
                1 => header.clone(),
                2..=7 => entries
                    .get(first + label.0 - 2)
                    .map(|(name, _)| {
                        format!(
                            "{} {name}",
                            if first + label.0 - 2 == s.cursor {
                                ">"
                            } else {
                                " "
                            }
                        )
                    })
                    .unwrap_or_default(),
                8 => s.status.clone(),
                _ => {
                    if s.editing {
                        "Type code / paste | Pad: up/down choose, right add".into()
                    } else {
                        format!(
                            "Enter: select  Esc: back  Ctrl/Cmd+C: copy code  {}/{}",
                            s.cursor + 1,
                            entries.len()
                        )
                    }
                }
            },
            52,
        );
    }
}
fn single_line(text: &str, max: usize) -> String {
    if text.chars().count() <= max {
        text.into()
    } else {
        text.chars().take(max - 3).collect::<String>() + "..."
    }
}
fn build_of(roster: &Roster) -> String {
    let mut parts = vec![
        env!("CARGO_PKG_VERSION").to_string(),
        "direct-udp-v2".into(),
    ];
    parts.extend(roster.0.iter().map(|c| format!("{c:?}")));
    format!(
        "{:08x}",
        net::lobby::build_id(&parts.iter().map(String::as_str).collect::<Vec<_>>())
    )
}
fn drive(
    mut s: ResMut<Social>,
    state: Res<State<AppState>>,
    roster: Res<Roster>,
    mut selection: ResMut<Selection>,
    mut names: ResMut<crate::online::PlayerNames>,
    mut info: ResMut<crate::online::OnlineInfo>,
    mut next: ResMut<NextState<AppState>>,
    mut commands: Commands,
    mut fingerprint: Local<Option<String>>,
) {
    for reply in s.service.drain() {
        let (tag, context) = reply.tag.split_once(':').unwrap_or((&reply.tag, ""));
        if matches!(tag, "state" | "signal" | "metadata")
            && !s.room.as_ref().is_some_and(|r| r.id == context)
        {
            continue;
        }
        if tag == "room" && context.parse::<u64>().ok() != Some(s.generation) {
            if let Ok(v) = reply.result {
                if let Some(id) = v["id"].as_str() {
                    s.service
                        .call("left", "POST", format!("/v1/rooms/{id}/leave"), None);
                }
            }
            continue;
        }

        let v = match reply.result {
            Ok(v) => v,
            Err(e) => {
                s.busy = false;
                s.status = e;
                if tag == "signal" {
                    if let Some(r) = s.room.as_mut() {
                        r.last_signal = Value::Null;
                    }
                }
                if tag == "state" && s.status.starts_with("HTTP 404:") {
                    s.leave();
                    info.locked = false;
                    next.set(AppState::Social);
                }
                if tag == "me" {
                    s.me = None;
                }
                continue;
            }
        };
        match tag {
            "browser" => {
                s.status = "Approve Discord sign-in in your browser.".into();
                if let Some(uri) = v["uri"].as_str() {
                    let mut command = if cfg!(target_os = "macos") {
                        std::process::Command::new("open")
                    } else if cfg!(windows) {
                        let mut c = std::process::Command::new("cmd");
                        c.args(["/C", "start", ""]);
                        c
                    } else {
                        std::process::Command::new("xdg-open")
                    };
                    let _ = command.arg(uri).spawn();
                }
            }
            "me" => {
                info!("Discord game session established");
                s.me = Some(v);
                s.status = "Signed in. Find players or invite friends.".into();
                s.refresh();
            }
            "logout" => {
                s.me = None;
                s.friends.clear();
                s.invites.clear();
                s.leave();
            }
            "friends" => s.friends = v["friends"].as_array().cloned().unwrap_or_default(),
            "invites" => s.invites = v["invites"].as_array().cloned().unwrap_or_default(),
            "changed" => {
                s.refresh();
                s.status = "Friend list updated.".into();
            }
            "invited" => s.status = "Invitation sent.".into(),
            "room" => {
                s.busy = false;
                if let (Some(id), Some(slot)) = (v["id"].as_str(), v["slot"].as_u64()) {
                    s.leave();
                    let (tx, rx) = mpsc::channel();
                    std::thread::spawn(move || {
                        let _ = tx.send(
                            Lobby::new(net::DEFAULT_PORT, 0, true)
                                .or_else(|_| Lobby::new(0, 0, true)),
                        );
                    });
                    s.room = Some(Room {
                        id: id.into(),
                        slot: slot as usize,
                        count: 2,
                        peers: vec![],
                        names: Default::default(),
                        addresses: [None; 4],
                        aliases: Default::default(),
                        udp: None,
                        opening: Some(Mutex::new(rx)),
                        last_signal: Value::Null,
                        playing: false,
                    });
                    s.service.call(
                        format!("metadata:{id}"),
                        "GET",
                        format!("/v1/rooms/{id}"),
                        None,
                    );
                    s.page = Page::Home;
                    s.cursor = 0;
                    s.status = "Finding UDP addresses...".into();
                }
            }
            "metadata" => {
                if let Some(r) = s.room.as_mut() {
                    r.count = if v["mode"] == "2v2" { 4 } else { 2 };
                }
            }
            "state" | "signal" => {
                if let Some(r) = s.room.as_mut() {
                    let peers = v["players"].as_array().cloned().unwrap_or_default();
                    for peer in &peers {
                        if let Some(slot) = peer["slot"].as_u64().filter(|n| *n < 4) {
                            let slot = slot as usize;
                            if r.peers
                                .iter()
                                .find(|p| p["slot"] == peer["slot"])
                                .is_some_and(|old| old["user"] != peer["user"])
                            {
                                r.addresses[slot] = None;
                                r.aliases[slot].clear();
                            }
                        }
                    }
                    r.peers = peers;
                    r.playing = v["playing"].as_bool().unwrap_or(false);
                    if let Some(members) = v["members"].as_array() {
                        for m in members {
                            if let Some(slot) = m["slot"].as_u64().filter(|n| *n < 4) {
                                r.names[slot as usize] =
                                    net::lobby::clean_name(m["name"].as_str().unwrap_or("Player"));
                            }
                        }
                    }
                }
            }
            _ => {}
        }
    }
    if !matches!(state.get(), AppState::Social | AppState::CharSelect) {
        return;
    }
    if s.room.is_none() {
        if s.me.is_some() && s.last_poll.elapsed() > Duration::from_secs(8) {
            s.last_poll = Instant::now();
            s.refresh();
        }
        return;
    }
    let mut open_failed = false;
    if let Some(r) = s.room.as_mut() {
        let result = r
            .opening
            .as_ref()
            .and_then(|rx| rx.lock().ok()?.try_recv().ok());
        if let Some(result) = result {
            r.opening = None;
            match result {
                Ok(udp) => r.udp = Some(udp),
                Err(_) => open_failed = true,
            }
        }
    }
    if open_failed {
        s.leave();
        info.locked = false;
        s.status = "Could not open a UDP port.".into();
        next.set(AppState::Social);
        return;
    }
    let send_probe = s.last_probe.elapsed() > Duration::from_millis(200);
    if send_probe {
        s.last_probe = Instant::now();
    }
    let poll = s.last_poll.elapsed() > Duration::from_millis(1500);
    if poll {
        s.last_poll = Instant::now();
    }
    let pick = s.pending_pick;
    let build = fingerprint.get_or_insert_with(|| build_of(&roster)).clone();
    let mut start = None;
    let mut signal = None;
    let mut state_path = None;
    if let Some(r) = s.room.as_mut() {
        if let Some(udp) = r.udp.as_mut() {
            for (from, probe) in udp.poll_probes() {
                if probe.room == r.id && probe.slot < r.count && probe.slot != r.slot {
                    if !r.aliases[probe.slot].contains(&from) {
                        r.aliases[probe.slot].push(from);
                    }
                    if r.addresses[probe.slot].is_none() {
                        r.addresses[probe.slot] = Some(from);
                    }
                }
            }
            if send_probe {
                for peer in &r.peers {
                    let slot = peer["slot"].as_u64().unwrap_or(99) as usize;
                    if slot == r.slot {
                        continue;
                    }
                    if let Some(candidates) = peer["candidates"].as_array() {
                        for candidate in candidates {
                            if let Some(address) = candidate.as_str().and_then(|s| s.parse().ok()) {
                                udp.probe(&r.id, r.slot, address);
                            }
                        }
                    }
                    if let Some(address) = r.addresses.get(slot).copied().flatten() {
                        udp.probe(&r.id, r.slot, address);
                    }
                }
            }
            let candidates = udp.candidates();
            let connected = (0..r.count).all(|slot| slot == r.slot || r.addresses[slot].is_some());
            let value = json!({"build":build,"character":pick.unwrap_or(0),"ready":pick.is_some()&&connected,"candidates":candidates.iter().map(ToString::to_string).collect::<Vec<_>>()});
            if poll && !candidates.is_empty() && value != r.last_signal && !r.playing {
                r.last_signal = value.clone();
                signal = Some((format!("/v1/rooms/{}/signal", r.id), value));
            }
            if poll {
                state_path = Some(format!("/v1/rooms/{}/state", r.id));
            }
            if r.playing && connected && pick.is_some() {
                start = Some((
                    r.slot,
                    r.count,
                    r.addresses,
                    r.peers.clone(),
                    r.names.clone(),
                ));
            }
        }
    }
    if let Some((path, value)) = signal {
        let id = s.room.as_ref().unwrap().id.clone();
        s.service
            .call(format!("signal:{id}"), "POST", path, Some(value));
    }
    if let Some(path) = state_path {
        let id = s.room.as_ref().unwrap().id.clone();
        s.service.call(format!("state:{id}"), "GET", path, None);
    }
    let waiting_connection = s.room.as_ref().is_some_and(|r| {
        r.peers.len() == r.count && (0..r.count).any(|i| i != r.slot && r.addresses[i].is_none())
    });
    if !waiting_connection {
        s.picked_at = None;
    } else if s.pending_pick.is_some() && s.picked_at.is_none() {
        s.picked_at = Some(Instant::now());
    }
    if s.picked_at
        .is_some_and(|t| t.elapsed() > Duration::from_secs(30))
        && start.is_none()
    {
        s.leave();
        info.locked = false;
        s.status = "Direct connection failed. Check NAT / port forwarding.".into();
        next.set(AppState::Social);
        return;
    }
    if let Some((local, count, addresses, peers, player_names)) = start {
        let r = s.room.as_mut().unwrap();
        let routes = (0..count)
            .filter(|slot| *slot != local)
            .map(|slot| (addresses[slot].unwrap(), r.aliases[slot].clone()))
            .collect();
        let socket = r
            .udp
            .take()
            .unwrap()
            .into_direct_socket()
            .with_routes(routes);
        let addresses = addresses
            .iter()
            .take(count)
            .map(|a| a.unwrap_or_else(|| "127.0.0.1:1".parse().unwrap()))
            .collect::<Vec<_>>();
        match net::start_mesh(socket, local, &addresses) {
            Ok(session) => {
                for p in peers {
                    let slot = p["slot"].as_u64().unwrap_or(99) as usize;
                    let fighter = p["character"].as_u64().unwrap_or(999) as usize;
                    if slot >= count || fighter >= roster.0.len() {
                        s.leave();
                        s.status = "Invalid fighter selection from peer.".into();
                        next.set(AppState::Social);
                        return;
                    }
                    selection.chars[slot] = fighter;
                }
                selection.online_teams = count == 4;
                selection.stage = 0;
                names.0 = player_names;
                info.local = local;
                commands.insert_resource(crate::online::NetSession {
                    session,
                    local,
                    cloud: true,
                    waiting: true,
                    waited: 0,
                });
                s.pending_pick = None;
                s.picked_at = None;
                next.set(AppState::Fight);
            }
            Err(_) => {
                s.leave();
                s.status = "Could not start direct netcode.".into();
                next.set(AppState::Social);
            }
        }
    }
}

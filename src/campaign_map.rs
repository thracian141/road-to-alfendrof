//! The campaign screen: maps you scroll between, each with its levels as circles, and the rules for starting and ending a level.

use bevy::prelude::*;
use t2f::brain::Difficulty;
use t2f::campaign::{rival_for, CampaignData, MapData, Progress};
use t2f::sim::Phase;

use crate::menus::{back_pressed, confirm_pressed, spawn_panel_sized, spawn_text, FillView};
use crate::sfx::UiSound;
use crate::{AppState, Mode, Roster, Selection, Sim, Stages};

/// Maps and levels from `assets/campaign/campaign.ron`.
#[derive(Resource)]
pub struct Maps(pub CampaignData);

/// How far the player has got, saved beside the settings.
#[derive(Resource)]
pub struct Saved(pub Progress);

/// Where the campaign is: choosing a fighter, on the map, or in a fight.
#[derive(Resource, Default)]
pub struct Campaign {
    /// The character select is for the campaign: one pick, then the map.
    pub picking: bool,
    /// The map and level being fought.
    pub active: Option<(usize, usize)>,
    /// The map and level the cursor is on.
    pub map: usize,
    pub level: usize,
    /// The fighter picked (index in the roster).
    pub player: usize,
    /// How the last fight went: `Some(true)` for a win.
    pub won: Option<bool>,
}

pub struct CampaignPlugin;

impl Plugin for CampaignPlugin {
    fn build(&self, app: &mut App) {
        let text = std::fs::read_to_string(crate::assets_dir().join("campaign/campaign.ron")).expect("assets/campaign/campaign.ron");
        let data = CampaignData::from_ron(&text).unwrap_or_else(|e| panic!("campaign.ron: {e}"));
        let progress = std::fs::read_to_string(crate::settings::data_file("campaign.ron")).map(|t| Progress::from_ron(&t)).unwrap_or_default();
        app.insert_resource(Maps(data))
            .insert_resource(Saved(progress))
            .init_resource::<Campaign>()
            .add_systems(OnEnter(AppState::Title), |mut campaign: ResMut<Campaign>| {
                campaign.picking = false;
                campaign.active = None;
                campaign.won = None;
            })
            .add_systems(OnEnter(AppState::Campaign), spawn_campaign)
            .add_systems(
                Update,
                (
                    campaign_input.run_if(in_state(AppState::Campaign)),
                    campaign_view.after(campaign_input).run_if(in_state(AppState::Campaign)),
                    campaign_result.run_if(in_state(AppState::Fight)),
                ),
            );
    }
}

/// Distance between two maps side by side, in map units.
const MAP_STEP: f32 = 600.0;
const MAP_W: f32 = 384.0;
const MAP_H: f32 = 224.0;

#[derive(Component)]
struct MapRoot;
#[derive(Component)]
struct Node(usize, usize);
#[derive(Component)]
struct Ring(usize);
#[derive(Component)]
struct MapTitle;
#[derive(Component)]
struct InfoName;
#[derive(Component)]
struct InfoLine;
#[derive(Component)]
struct InfoPortrait;

/// The map picture is bigger than it is shown, so it is scaled smoothly instead of by nearest pixel.
fn smooth(assets: &AssetServer, path: String) -> Handle<Image> {
    assets.load_builder().with_settings(|s: &mut bevy::image::ImageLoaderSettings| s.sampler = bevy::image::ImageSampler::linear()).load(path)
}

fn node_image(map: &MapData, level: usize, progress: &Progress) -> &'static str {
    if map.levels[level].boss && progress.is_unlocked(map, level) && !progress.is_beaten(map, level) {
        "ui/campaign/node_boss.png"
    } else if progress.is_beaten(map, level) {
        "ui/campaign/node_done.png"
    } else if progress.is_unlocked(map, level) {
        "ui/campaign/node_open.png"
    } else {
        "ui/campaign/node_locked.png"
    }
}

fn spawn_campaign(
    mut commands: Commands,
    assets: Res<AssetServer>,
    maps: Res<Maps>,
    saved: Res<Saved>,
    mut campaign: ResMut<Campaign>,
) {
    let state = AppState::Campaign;
    // coming back from a fight that was won, the cursor goes on to the next level
    campaign.picking = false;
    let map = &maps.0.maps[campaign.map.min(maps.0.maps.len() - 1)];
    if !map.levels.is_empty() {
        campaign.level = if campaign.won == Some(true) || campaign.level >= map.levels.len() { saved.0.current(map) } else { campaign.level };
    }
    campaign.won = None;
    campaign.active = None;

    commands.spawn((
        DespawnOnExit(state.clone()),
        FillView,
        Sprite::from_color(Color::srgb(0.04, 0.05, 0.1), Vec2::new(MAP_W, MAP_H)),
        Transform::from_xyz(0.0, 0.0, -9.0),
    ));
    let at = |p: (i32, i32)| Vec3::new(p.0 as f32 - MAP_W / 2.0, MAP_H / 2.0 - p.1 as f32, 0.0);
    commands
        .spawn((DespawnOnExit(state.clone()), MapRoot, Transform::default(), Visibility::default()))
        .with_children(|root| {
            for (m, map) in maps.0.maps.iter().enumerate() {
                let x = m as f32 * MAP_STEP;
                root.spawn((
                    Sprite { image: smooth(&assets, map.image.clone()), custom_size: Some(Vec2::new(MAP_W, MAP_H)), ..default() },
                    Transform::from_xyz(x, 0.0, -5.0),
                ));
                // a dotted trail from level to level
                for pair in map.levels.windows(2) {
                    let (a, b) = (at(pair[0].at), at(pair[1].at));
                    let steps = (a.distance(b) / 5.0).floor().max(1.0) as i32;
                    for k in 1..steps {
                        let p = a.lerp(b, k as f32 / steps as f32);
                        root.spawn((Sprite::from_color(Color::srgb(1.0, 0.95, 0.7), Vec2::splat(2.0)), Transform::from_xyz(x + p.x, p.y, -3.0)));
                    }
                }
                for (l, level) in map.levels.iter().enumerate() {
                    let p = at(level.at);
                    let size = if level.boss { 18.0 } else { 14.0 };
                    root.spawn((
                        Node(m, l),
                        Sprite { image: assets.load("ui/campaign/node_locked.png"), custom_size: Some(Vec2::splat(size)), ..default() },
                        Transform::from_xyz(x + p.x, p.y, -2.0),
                    ));
                }
                root.spawn((
                    Ring(m),
                    Sprite { image: assets.load("ui/campaign/node_select_0.png"), custom_size: Some(Vec2::splat(22.0)), ..default() },
                    Transform::from_xyz(x, 0.0, -1.0),
                    Visibility::Hidden,
                ));
            }
        });

    // the name of the map, and the level below
    let title = spawn_text(&mut commands, state.clone(), String::new(), 16.0, Color::srgb(1.0, 0.9, 0.4), 94.0);
    commands.entity(title).insert((MapTitle, Transform::from_xyz(0.0, 94.0, 8.0)));
    spawn_panel_sized(&mut commands, state.clone(), Vec2::new(372.0, 40.0), Vec2::new(0.0, -86.0));
    commands.spawn((
        DespawnOnExit(state.clone()),
        InfoPortrait,
        Sprite::from_color(Color::srgb(0.2, 0.2, 0.3), Vec2::splat(30.0)),
        Transform::from_xyz(-160.0, -86.0, 8.0),
    ));
    let name = spawn_text(&mut commands, state.clone(), String::new(), 16.0, Color::WHITE, -80.0);
    commands.entity(name).insert((InfoName, Transform::from_xyz(8.0, -79.0, 8.0)));
    let line = spawn_text(&mut commands, state.clone(), String::new(), 8.0, Color::srgb(0.75, 0.7, 0.95), -92.0);
    commands.entity(line).insert((InfoLine, Transform::from_xyz(8.0, -92.0, 8.0)));
    let hint = spawn_text(&mut commands, state, "A/D: map    W/S: level    Enter: fight    Esc: back".into(), 8.0, Color::srgb(0.6, 0.6, 0.7), -104.0);
    commands.entity(hint).insert(Transform::from_xyz(0.0, -104.0, 8.0));
}

fn campaign_input(
    keys: Res<crate::MenuInput>,
    maps: Res<Maps>,
    saved: Res<Saved>,
    roster: Res<Roster>,
    stages: Res<Stages>,
    mut campaign: ResMut<Campaign>,
    mut sel: ResMut<Selection>,
    mut next: ResMut<NextState<AppState>>,
    mut ui: MessageWriter<UiSound>,
) {
    if back_pressed(&keys.0) {
        next.set(AppState::Title);
        return;
    }
    let pressed = |a: KeyCode, b: KeyCode| keys.just_pressed(a) || keys.just_pressed(b);
    let turn = pressed(KeyCode::KeyD, KeyCode::ArrowRight) as i32 - pressed(KeyCode::KeyA, KeyCode::ArrowLeft) as i32;
    if turn != 0 {
        let to = (campaign.map as i32 + turn).clamp(0, maps.0.maps.len() as i32 - 1) as usize;
        if to != campaign.map {
            campaign.map = to;
            let map = &maps.0.maps[to];
            campaign.level = if map.levels.is_empty() { 0 } else { saved.0.current(map) };
            ui.write(UiSound::Move);
        }
    }
    let map = &maps.0.maps[campaign.map];
    if map.levels.is_empty() {
        return;
    }
    let step = pressed(KeyCode::KeyS, KeyCode::ArrowDown) as i32 - pressed(KeyCode::KeyW, KeyCode::ArrowUp) as i32;
    if step != 0 {
        // (down goes back along the path, up goes on)
        let to = saved.0.step(map, campaign.level, -step);
        if to != campaign.level {
            campaign.level = to;
            ui.write(UiSound::Move);
        }
    }
    if confirm_pressed(&keys.0) && saved.0.is_unlocked(map, campaign.level) {
        let level = &map.levels[campaign.level];
        let player_name = roster.0[campaign.player].name.clone();
        let rival = rival_for(level, &player_name);
        let (Some(rival), Some(stage)) = (roster.0.iter().position(|c| c.name == rival), stages.0.iter().position(|s| s.name == level.stage)) else {
            warn!("level {}: rival or stage not found", level.name);
            return;
        };
        sel.chars[0] = campaign.player;
        sel.chars[1] = rival;
        sel.stage = stage;
        campaign.active = Some((campaign.map, campaign.level));
        campaign.won = None;
        next.set(AppState::Fight);
    }
}

fn campaign_view(
    time: Res<Time>,
    maps: Res<Maps>,
    saved: Res<Saved>,
    roster: Res<Roster>,
    assets: Res<AssetServer>,
    campaign: Res<Campaign>,
    mut root: Single<&mut Transform, With<MapRoot>>,
    mut nodes: Query<(&Node, &mut Sprite), (Without<Ring>, Without<InfoPortrait>)>,
    mut rings: Query<(&Ring, &mut Sprite, &mut Transform, &mut Visibility), (Without<Node>, Without<MapRoot>, Without<InfoPortrait>)>,
    mut title: Single<&mut Text2d, (With<MapTitle>, Without<InfoName>, Without<InfoLine>)>,
    mut name: Single<&mut Text2d, (With<InfoName>, Without<MapTitle>, Without<InfoLine>)>,
    mut line: Single<&mut Text2d, (With<InfoLine>, Without<MapTitle>, Without<InfoName>)>,
    mut portrait: Single<&mut Sprite, (With<InfoPortrait>, Without<Node>, Without<Ring>)>,
    mut shown: Local<Option<(usize, usize, usize)>>,
) {
    let ease = 1.0 - (-14.0 * time.delta_secs()).exp();
    let want = -(campaign.map as f32) * MAP_STEP;
    root.translation.x += (want - root.translation.x) * ease;

    let map = &maps.0.maps[campaign.map];
    let level = (!map.levels.is_empty()).then(|| &map.levels[campaign.level]);
    for (Node(m, l), mut sprite) in &mut nodes {
        let map = &maps.0.maps[*m];
        let path = node_image(map, *l, &saved.0);
        if sprite.image != assets.load::<Image>(path) {
            sprite.image = assets.load(path);
        }
    }
    let pulse = (time.elapsed_secs() * 2.5) as i32 % 2;
    for (Ring(m), mut sprite, mut tf, mut visibility) in &mut rings {
        let here = *m == campaign.map && level.is_some();
        let want = if here { Visibility::Inherited } else { Visibility::Hidden };
        if *visibility != want {
            *visibility = want;
        }
        if let (true, Some(level)) = (here, level) {
            tf.translation.x = *m as f32 * MAP_STEP + level.at.0 as f32 - MAP_W / 2.0;
            tf.translation.y = MAP_H / 2.0 - level.at.1 as f32;
            let image = assets.load(format!("ui/campaign/node_select_{pulse}.png"));
            if sprite.image != image {
                sprite.image = image;
            }
        }
    }

    let new_title = format!("{}{}{}", if campaign.map > 0 { "< " } else { "  " }, map.name, if campaign.map + 1 < maps.0.maps.len() { " >" } else { "  " });
    if title.0 != new_title {
        title.0 = new_title;
    }
    let (new_name, new_line) = match level {
        None => ("Coming soon".to_string(), String::new()),
        Some(level) => {
            let rival = rival_for(level, &roster.0[campaign.player].name);
            let state = if saved.0.is_beaten(map, campaign.level) { "cleared" } else { "open" };
            (level.name.clone(), format!("vs {rival}    {}    {}", "*".repeat(level.difficulty as usize), state))
        }
    };
    if name.0 != new_name {
        name.0 = new_name;
    }
    if line.0 != new_line {
        line.0 = new_line;
    }
    let key = (campaign.map, campaign.level, campaign.player);
    if *shown != Some(key) {
        *shown = Some(key);
        match level {
            None => portrait.color = Color::srgb(0.2, 0.2, 0.3),
            Some(level) => {
                let rival = rival_for(level, &roster.0[campaign.player].name);
                if let Some(c) = roster.0.iter().find(|c| c.name == rival) {
                    let folder = c.sprites.clone().unwrap_or_else(|| c.name.to_lowercase());
                    if crate::assets_dir().join(format!("portraits/{folder}.png")).exists() {
                        portrait.image = assets.load(format!("portraits/{folder}.png"));
                        portrait.color = Color::WHITE;
                    } else {
                        portrait.color = Color::srgb(c.color.0, c.color.1, c.color.2);
                    }
                }
            }
        }
    }
}

/// The level fought ends when the match does: a win is saved and opens the next level.
fn campaign_result(sim: Res<Sim>, maps: Res<Maps>, mut saved: ResMut<Saved>, mut campaign: ResMut<Campaign>, mut was_over: Local<bool>) {
    let over = sim.0.phase == Phase::MatchOver;
    let just_ended = over && !*was_over;
    *was_over = over;
    let (true, Some((m, l))) = (just_ended, campaign.active) else { return };
    let won = sim.0.match_winner() == Some(0);
    campaign.won = Some(won);
    if won && saved.0.beat(&maps.0.maps[m], l) {
        let path = crate::settings::data_file("campaign.ron");
        if let Err(e) = crate::settings::write_file(&path, &saved.0.to_ron()) {
            warn!("could not save progress to {}: {e}", path.display());
        }
    }
}

/// The campaign's say in the end-of-match line, if a level is being fought.
pub fn banner_line(campaign: &Campaign, mode: Mode) -> Option<&'static str> {
    if mode != Mode::VsCpu || campaign.active.is_none() {
        return None;
    }
    Some(match campaign.won {
        Some(true) => "Level cleared    Enter: map",
        _ => "Enter: retry    Esc: map",
    })
}

/// The CPU's skill for the level being fought (what it always was outside the campaign).
pub fn difficulty(campaign: &Campaign, maps: &Maps) -> Difficulty {
    match campaign.active {
        Some((m, l)) => Difficulty::level(maps.0.maps[m].levels[l].difficulty),
        None => Difficulty::NORMAL,
    }
}

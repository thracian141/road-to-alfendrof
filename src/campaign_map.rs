//! The campaign screen: maps you scroll between, each with its levels as circles, and the rules for starting and ending a level.

use bevy::prelude::*;
use bevy::asset::RenderAssetUsages;
use bevy::render::render_resource::{Extent3d, TextureDimension, TextureFormat};
use bevy::sprite::SpriteImageMode;
use t2f::brain::Difficulty;
use t2f::campaign::{rival_for, CampaignData, MapTheme, Progress};
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
    /// The fighter picked for the last level (index in the roster), if there was one.
    pub player: Option<usize>,
    /// How the last fight went: `Some(true)` for a win.
    pub won: Option<bool>,
    /// Roster indices: preliminary opponents followed by the level's real rival.
    pub opponents: Vec<usize>,
    pub encounter: usize,
}

impl Campaign {
    /// Preliminary victories and losses never change persistent level progress.
    fn record_result(&mut self, won: bool, maps: &CampaignData, progress: &mut Progress) -> bool {
        self.won = Some(won);
        match self.active {
            Some((m, l)) if won && self.last_encounter() => progress.beat(&maps.maps[m], l),
            _ => false,
        }
    }

    pub fn last_encounter(&self) -> bool {
        !self.opponents.is_empty() && self.encounter + 1 == self.opponents.len()
    }

    pub fn advance(&mut self, sel: &mut Selection) -> bool {
        if self.won != Some(true) || self.last_encounter() { return false; }
        let Some(&opponent) = self.opponents.get(self.encounter + 1) else { return false; };
        self.encounter += 1;
        self.won = None;
        sel.chars[1] = opponent;
        true
    }
}

pub struct CampaignPlugin;

impl Plugin for CampaignPlugin {
    fn build(&self, app: &mut App) {
        let text = std::fs::read_to_string(crate::assets_dir().join("campaign/campaign.ron")).expect("assets/campaign/campaign.ron");
        let data = CampaignData::from_ron(&text).unwrap_or_else(|e| panic!("campaign.ron: {e}"));
        let progress = std::fs::read_to_string(crate::settings::data_file("campaign.ron")).map(|t| Progress::from_ron(&t)).unwrap_or_default();
        let initial_map = progress.last_campaign(&data);
        app.insert_resource(Maps(data))
            .insert_resource(Saved(progress))
            .insert_resource(Campaign { map: initial_map, ..default() })
            .add_systems(OnEnter(AppState::Title), |mut campaign: ResMut<Campaign>| {
                campaign.picking = false;
                campaign.active = None;
                campaign.won = None;
            })
            .add_systems(OnEnter(AppState::Campaign), spawn_campaign)
            // Leaving Fight clears its sprites and HUD before the next opponent is spawned.
            .add_systems(OnEnter(AppState::CampaignEncounter), |mut next: ResMut<NextState<AppState>>| {
                next.set(AppState::Fight);
            })
            .add_systems(
                Update,
                (
                    campaign_input.run_if(in_state(AppState::Campaign)),
                    campaign_view.after(campaign_input).run_if(in_state(AppState::Campaign)),
                    update_fight_squares.run_if(in_state(AppState::Campaign)),
                    campaign_result.run_if(in_state(AppState::Fight)),
                ),
            );
    }
}

/// Distance between two maps side by side, in map units.
const MAP_STEP: f32 = 600.0;
const MAP_W: f32 = 384.0;
const MAP_H: f32 = 224.0;
const MAP_Y: f32 = 16.0;
/// Space for the complete framed map, its title, and the level panel below it.
pub(crate) const VIEW_SIZE: Vec2 = Vec2::new(416.0, 320.0);

pub(crate) fn view_size(aspect: f32) -> Vec2 {
    Vec2::new(VIEW_SIZE.x.max(VIEW_SIZE.y * aspect), VIEW_SIZE.y.max(VIEW_SIZE.x / aspect))
}

#[derive(Component)]
struct MapRoot;
#[derive(Component)]
struct MapCard(usize);
#[derive(Component)]
struct Node(usize, usize);
#[derive(Component)]
struct FightSquare(usize, usize, usize);

fn fight_square_color(m: usize, l: usize, fight: usize, campaign: &Campaign, maps: &CampaignData, progress: &Progress) -> Color {
    let completed = if campaign.active == Some((m, l)) {
        campaign.encounter + usize::from(campaign.won == Some(true))
    } else if progress.is_beaten(&maps.maps[m], l) {
        maps.maps[m].preliminary_count(l) + 1
    } else { 0 };
    if fight < completed {
        Color::srgb(0.4, 0.8, 0.5)
    } else if fight == completed && progress.can_play(maps, m, l) {
        Color::srgb(1.0, 0.85, 0.3)
    } else {
        Color::srgb(0.25, 0.27, 0.32)
    }
}

fn update_fight_squares(maps: Res<Maps>, saved: Res<Saved>, campaign: Res<Campaign>, mut squares: Query<(&FightSquare, &mut Sprite)>) {
    for (FightSquare(m, l, fight), mut sprite) in &mut squares {
        sprite.color = fight_square_color(*m, *l, *fight, &campaign, &maps.0, &saved.0);
    }
}
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

/// Preserve the native pixels when campaign artwork is scaled to its map size.
pub(crate) fn map_image(assets: &AssetServer, path: String) -> Handle<Image> {
    assets.load_builder().with_settings(|s: &mut bevy::image::ImageLoaderSettings| s.sampler = bevy::image::ImageSampler::nearest()).load(path)
}

/// A quiet, seamless geometric tile, drawn on the same pixel grid as the map.
fn surround_pattern(theme: MapTheme) -> Image {
    let rows = match theme {
        MapTheme::Istanbul => [
        ".......++.......", "......+..+......", "....++....++....", "....+..oo..+....",
        "..++..o..o..++..", "..+..o....o..+..", ".+..o..++..o..+.", "+..o..+..+..o..+",
        "+..o..+..+..o..+", ".+..o..++..o..+.", "..+..o....o..+..", "..++..o..o..++..",
        "....+..oo..+....", "....++....++....", "......+..+......", ".......++.......",
        ],
        MapTheme::ForeignLands => [
            "................", "...+........+...", "..+o+......+o+..", ".+o.o+....+o.o+.",
            "..+o+..++..+o+..", "...+..+oo+..+...", ".....+o..o+.....", "....+o.oo.o+....",
            "....+o.oo.o+....", ".....+o..o+.....", "...+..+oo+..+...", "..+o+..++..+o+..",
            ".+o.o+....+o.o+.", "..+o+......+o+..", "...+........+...", "................",
        ],
        MapTheme::SnowForests => [
            ".......+........", "....+..+..+.....", ".....+.+.+......", "......+++.......",
            "..+....+....+...", "...+...+...+....", "....+..+..+.....", "+++++++++++++++.",
            "....+..+..+.....", "...+...+...+....", "..+....+....+...", "......+++.......",
            ".....+.+.+......", "....+..+..+.....", ".......+........", "................",
        ],
    };
    let palette = match theme {
        MapTheme::Istanbul => [[15, 36, 45, 255], [27, 55, 64, 255], [36, 65, 70, 255]],
        MapTheme::ForeignLands => [[31, 34, 35, 255], [64, 62, 58, 255], [92, 64, 57, 255]],
        MapTheme::SnowForests => [[17, 31, 49, 255], [34, 56, 77, 255], [70, 97, 119, 255]],
    };
    let pixels = rows.iter().flat_map(|row| row.bytes()).flat_map(|pixel| match pixel {
        b'+' => palette[1],
        b'o' => palette[2],
        _ => palette[0],
    }).collect();
    let mut image = Image::new(
        Extent3d { width: 16, height: 16, depth_or_array_layers: 1 },
        TextureDimension::D2, pixels, TextureFormat::Rgba8UnormSrgb, RenderAssetUsages::default(),
    );
    image.sampler = bevy::image::ImageSampler::nearest();
    image
}

/// Copper and gold trim with stepped corner stars; everything stays outside
/// the map rectangle, so the frame never covers coastline or level markers.
pub(crate) fn frame_parts(theme: MapTheme) -> Vec<(Sprite, Vec3)> {
    let colors = match theme {
        MapTheme::Istanbul => [(11, 30, 39), (167, 107, 65), (222, 186, 119), (33, 69, 80)],
        MapTheme::ForeignLands => [(22, 25, 27), (99, 81, 70), (175, 169, 148), (55, 62, 61)],
        MapTheme::SnowForests => [(13, 25, 42), (75, 112, 143), (184, 219, 232), (36, 61, 84)],
    };
    let [ink, copper, gold, inset] = colors.map(|(r, g, b)| Color::srgb_u8(r, g, b));
    let mut parts = Vec::new();
    for (grow, color, z) in [(20.0, ink, -7.0), (16.0, copper, -6.9), (12.0, gold, -6.8), (8.0, inset, -6.7)] {
        parts.push((Sprite::from_color(color, Vec2::new(MAP_W + grow, MAP_H + grow)), Vec3::new(0.0, 0.0, z)));
    }
    for side in [-1.0, 1.0] {
        for x in (-176..=176).step_by(16) {
            if theme == MapTheme::SnowForests {
                for (dx, dy) in [(-3.0, 0.0), (-2.0, 0.0), (-1.0, 0.0), (0.0, 0.0), (1.0, 0.0), (2.0, 0.0), (3.0, 0.0), (0.0, -3.0), (0.0, -2.0), (0.0, -1.0), (0.0, 1.0), (0.0, 2.0), (0.0, 3.0), (-1.0, -1.0), (1.0, 1.0), (-1.0, 1.0), (1.0, -1.0)] {
                    parts.push((Sprite::from_color(gold, Vec2::ONE), Vec3::new(x as f32 + dx, side * 116.0 + dy, -4.5)));
                }
                continue;
            }
            if theme == MapTheme::ForeignLands {
                let stitch = Color::srgb_u8(121, 72, 61);
                for (dx, dy) in [(-4.0, 0.0), (-3.0, 1.0), (-2.0, 2.0), (-1.0, 1.0), (0.0, 0.0), (1.0, -1.0), (2.0, -2.0), (3.0, -1.0), (4.0, 0.0)] {
                    parts.push((Sprite::from_color(stitch, Vec2::ONE), Vec3::new(x as f32 + dx, side * 116.0 + dy, -4.5)));
                }
                continue;
            }
            for (dx, dy) in [(0.0, -1.0), (-1.0, 0.0), (1.0, 0.0), (0.0, 1.0)] {
                parts.push((Sprite::from_color(gold, Vec2::ONE), Vec3::new(x as f32 + dx, side * 116.0 + dy, -4.5)));
            }
        }
        for y in (-96..=96).step_by(16) {
            parts.push((Sprite::from_color(gold, Vec2::splat(2.0)), Vec3::new(side * 196.0, y as f32, -4.5)));
        }
        for other in [-1.0, 1.0] {
            let corners = match theme {
                MapTheme::SnowForests => &[(0.0, 0.0), (-4.0, 0.0), (-3.0, 0.0), (-2.0, 0.0), (-1.0, 0.0), (1.0, 0.0), (2.0, 0.0), (3.0, 0.0), (4.0, 0.0), (0.0, -4.0), (0.0, -3.0), (0.0, -2.0), (0.0, -1.0), (0.0, 1.0), (0.0, 2.0), (0.0, 3.0), (0.0, 4.0), (-2.0, -2.0), (2.0, 2.0), (-2.0, 2.0), (2.0, -2.0)][..],
                MapTheme::Istanbul => &[(0.0, 0.0), (0.0, 3.0), (0.0, -3.0), (3.0, 0.0), (-3.0, 0.0), (2.0, 2.0), (-2.0, 2.0), (2.0, -2.0), (-2.0, -2.0)][..],
                MapTheme::ForeignLands => &[(-3.0, -3.0), (-2.0, -2.0), (-1.0, -1.0), (0.0, 0.0), (1.0, 1.0), (2.0, 2.0), (3.0, 3.0), (-3.0, 3.0), (-2.0, 2.0), (-1.0, 1.0), (1.0, -1.0), (2.0, -2.0), (3.0, -3.0)][..],
            };
            for &(dx, dy) in corners {
                parts.push((Sprite::from_color(gold, Vec2::ONE), Vec3::new(side * 198.0 + dx, other * 118.0 + dy, -4.4)));
            }
        }
    }
    parts
}

pub(crate) fn spawn_surround(commands: &mut Commands, state: AppState, images: &mut Assets<Image>, theme: MapTheme) -> Entity {
    commands.spawn((
        DespawnOnExit(state),
        FillView,
        Sprite {
            image: images.add(surround_pattern(theme)),
            custom_size: Some(VIEW_SIZE),
            image_mode: SpriteImageMode::Tiled { tile_x: true, tile_y: true, stretch_value: 1.0 },
            ..default()
        },
        Transform::from_xyz(0.0, 0.0, -9.0),
    )).id()
}

fn save_progress(progress: &Progress) {
    let path = crate::settings::data_file("campaign.ron");
    if let Err(e) = crate::settings::write_file(&path, &progress.to_ron()) {
        warn!("could not save progress to {}: {e}", path.display());
    }
}

fn node_image(data: &CampaignData, m: usize, level: usize, progress: &Progress) -> &'static str {
    let map = &data.maps[m];
    if !progress.can_play(data, m, level) {
        "ui/campaign/node_locked.png"
    } else if map.levels[level].boss && !progress.is_beaten(map, level) {
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
    mut images: ResMut<Assets<Image>>,
    maps: Res<Maps>,
    mut saved: ResMut<Saved>,
    mut campaign: ResMut<Campaign>,
) {
    let state = AppState::Campaign;
    // coming back from a fight that was won, the cursor goes on to the next level
    campaign.picking = false;
    let map = &maps.0.maps[campaign.map.min(maps.0.maps.len() - 1)];
    if !map.levels.is_empty() {
        campaign.level = if (campaign.won == Some(true) && campaign.last_encounter()) || campaign.level >= map.levels.len() { saved.0.current(map) } else { campaign.level };
    }
    // Keep the current sequence while browsing the map, so its squares and resume
    // action refer to the same encounter.
    if saved.0.visit(map) { save_progress(&saved.0); }

    for (m, map) in maps.0.maps.iter().enumerate() {
        let backdrop = spawn_surround(&mut commands, state.clone(), &mut images, map.theme);
        commands.entity(backdrop).insert((MapCard(m), if m == campaign.map { Visibility::Inherited } else { Visibility::Hidden }));
    }
    let at = |p: (i32, i32)| Vec3::new(p.0 as f32 - MAP_W / 2.0, MAP_H / 2.0 - p.1 as f32, 0.0);
    commands
        .spawn((DespawnOnExit(state.clone()), MapRoot, Transform::from_xyz(-(campaign.map as f32) * MAP_STEP, MAP_Y, 0.0), Visibility::default()))
        .with_children(|root| {
            for (m, map) in maps.0.maps.iter().enumerate() {
                let x = m as f32 * MAP_STEP;
                root.spawn((MapCard(m), Transform::from_xyz(x, 0.0, 0.0), if m == campaign.map { Visibility::Inherited } else { Visibility::Hidden }))
                    .with_children(|root| {
                        for (sprite, position) in frame_parts(map.theme) {
                            root.spawn((sprite, Transform::from_translation(position)));
                        }
                        root.spawn((
                            Sprite { image: map_image(&assets, map.image.clone()), custom_size: Some(Vec2::new(MAP_W, MAP_H)), ..default() },
                            Transform::from_xyz(0.0, 0.0, -5.0),
                        ));
                        // a dotted trail from level to level
                        for pair in map.levels.windows(2) {
                            let (a, b) = (at(pair[0].at), at(pair[1].at));
                            let steps = (a.distance(b) / 5.0).floor().max(1.0) as i32;
                            for k in 1..steps {
                                let p = a.lerp(b, k as f32 / steps as f32);
                                root.spawn((Sprite::from_color(Color::srgb(1.0, 0.95, 0.7), Vec2::splat(2.0)), Transform::from_xyz(p.x, p.y, -3.0)));
                            }
                        }
                        for (l, level) in map.levels.iter().enumerate() {
                            let p = at(level.at);
                            let size = if level.boss { 18.0 } else { 14.0 };
                            root.spawn((
                                Node(m, l),
                                Sprite { image: assets.load("ui/campaign/node_locked.png"), custom_size: Some(Vec2::splat(size)), ..default() },
                                Transform::from_xyz(p.x, p.y, -2.0),
                            ));
                            let fights = map.preliminary_count(l) + 1;
                            for fight in 0..fights {
                                let x = p.x + fight as f32 * 7.0 - (fights - 1) as f32 * 3.5;
                                let y = p.y - 16.0;
                                root.spawn((Sprite::from_color(Color::srgb(0.07, 0.06, 0.1), Vec2::splat(6.0)), Transform::from_xyz(x, y, -1.0)));
                                root.spawn((FightSquare(m, l, fight), Sprite::from_color(fight_square_color(m, l, fight, &campaign, &maps.0, &saved.0), Vec2::splat(4.0)), Transform::from_xyz(x, y, -0.9)));
                            }
                        }
                        root.spawn((
                            Ring(m),
                            Sprite { image: assets.load("ui/campaign/node_select_0.png"), custom_size: Some(Vec2::splat(22.0)), ..default() },
                            Transform::from_xyz(0.0, 0.0, -1.0),
                            Visibility::Hidden,
                        ));
                    });
            }
        });

    // the name of the map, and the level below
    let title = spawn_text(&mut commands, state.clone(), String::new(), 14.0, Color::srgb(1.0, 0.9, 0.4), 148.0);
    commands.entity(title).insert((MapTitle, Transform::from_xyz(0.0, 148.0, 8.0)));
    commands.spawn((DespawnOnExit(state.clone()), Sprite::from_color(Color::srgba(0.03, 0.02, 0.08, 0.8), Vec2::new(150.0, 16.0)), Transform::from_xyz(0.0, 148.0, 7.0)));
    spawn_panel_sized(&mut commands, state.clone(), Vec2::new(396.0, 40.0), Vec2::new(0.0, -128.0));
    commands.spawn((
        DespawnOnExit(state.clone()),
        InfoPortrait,
        Sprite::from_color(Color::srgb(0.2, 0.2, 0.3), Vec2::splat(30.0)),
        Transform::from_xyz(-176.0, -128.0, 8.0),
    ));
    let name = spawn_text(&mut commands, state.clone(), String::new(), 16.0, Color::WHITE, -80.0);
    commands.entity(name).insert((InfoName, Transform::from_xyz(8.0, -121.0, 8.0)));
    let line = spawn_text(&mut commands, state.clone(), String::new(), 8.0, Color::srgb(0.75, 0.7, 0.95), -92.0);
    commands.entity(line).insert((InfoLine, Transform::from_xyz(8.0, -134.0, 8.0)));
    let hint = spawn_text(&mut commands, state, "Arrows: browse    Enter: fight    Esc: back".into(), 8.0, Color::srgb(0.6, 0.6, 0.7), -104.0);
    commands.entity(hint).insert(Transform::from_xyz(0.0, -154.0, 8.0));
}

fn campaign_input(
    keys: Res<crate::MenuInput>,
    maps: Res<Maps>,
    mut saved: ResMut<Saved>,
    mut campaign: ResMut<Campaign>,
    mut mode: ResMut<Mode>,
    mut next: ResMut<NextState<AppState>>,
    mut ui: MessageWriter<UiSound>,
) {
    if back_pressed(&keys.0) {
        next.set(AppState::Title);
        return;
    }
    // every arrow (and WASD) moves along the levels; past the last one of a map it goes on to the next map
    let pressed = |a: KeyCode, b: KeyCode| keys.just_pressed(a) || keys.just_pressed(b);
    let forward = pressed(KeyCode::KeyD, KeyCode::ArrowRight) || pressed(KeyCode::KeyS, KeyCode::ArrowDown);
    let back = pressed(KeyCode::KeyA, KeyCode::ArrowLeft) || pressed(KeyCode::KeyW, KeyCode::ArrowUp);
    let dir = forward as i32 - back as i32;
    if dir != 0 {
        let (from_map, from_level) = (campaign.map, campaign.level);
        (campaign.map, campaign.level) = maps.0.browse(campaign.map, campaign.level, dir);
        if (campaign.map, campaign.level) != (from_map, from_level) {
            if saved.0.visit(&maps.0.maps[campaign.map]) { save_progress(&saved.0); }
            ui.write(UiSound::Move);
        }
        return;
    }
    if confirm_pressed(&keys.0) && saved.0.can_play(&maps.0, campaign.map, campaign.level) {
        // the fighter is chosen for each level; the fight starts from there (see `begin_level`)
        *mode = Mode::VsCpu;
        campaign.picking = true;
        next.set(AppState::CharSelect);
    }
}

/// Starts the level the cursor is on with the fighter just picked. Returns false if its rival or stage can't be found.
pub fn begin_level(campaign: &mut Campaign, player: usize, maps: &Maps, roster: &Roster, stages: &Stages, sel: &mut Selection) -> bool {
    let level = &maps.0.maps[campaign.map].levels[campaign.level];
    let rival = rival_for(level, &roster.0[player].name);
    let (Some(rival), Some(stage)) = (roster.0.iter().position(|c| c.name == rival), stages.0.iter().position(|s| s.name == level.stage)) else {
        warn!("level {}: rival or stage not found", level.name);
        return false;
    };
    if campaign.active == Some((campaign.map, campaign.level)) && campaign.player == Some(player)
        && !campaign.opponents.is_empty() && !(campaign.won == Some(true) && campaign.last_encounter()) {
        sel.chars[0] = player;
        sel.chars[1] = campaign.opponents[campaign.encounter];
        sel.stage = stage;
        campaign.advance(sel);
        campaign.won = None;
        campaign.picking = false;
        return true;
    }
    let generics: Vec<usize> = roster.0.iter().enumerate().filter_map(|(i, c)| c.campaign_only.then_some(i)).collect();
    let count = maps.0.maps[campaign.map].preliminary_count(campaign.level);
    if generics.len() < count {
        warn!("level {}: not enough generic opponents", level.name);
        return false;
    }
    // Stable rotation gives each level a different group, with no repeats within a level.
    let offset = campaign.map * 3 + campaign.level * 2;
    campaign.opponents = (0..count).map(|i| generics[(offset + i) % generics.len()]).chain(std::iter::once(rival)).collect();
    campaign.encounter = 0;
    campaign.player = Some(player);
    sel.chars[0] = player;
    sel.chars[1] = campaign.opponents[0];
    sel.stage = stage;
    campaign.active = Some((campaign.map, campaign.level));
    campaign.won = None;
    campaign.picking = false;
    true
}

/// The rival's name as the map shows it: the level's own until a fighter has been picked.
fn shown_rival<'a>(level: &'a t2f::campaign::LevelData, roster: &Roster, campaign: &Campaign) -> &'a str {
    match campaign.player {
        Some(p) => rival_for(level, &roster.0[p].name),
        None => &level.rival,
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
    mut cards: Query<(&MapCard, &mut Visibility), Without<Ring>>,
    mut nodes: Query<(&Node, &mut Sprite), (Without<Ring>, Without<InfoPortrait>)>,
    mut rings: Query<(&Ring, &mut Sprite, &mut Transform, &mut Visibility), (Without<Node>, Without<MapRoot>, Without<InfoPortrait>)>,
    mut title: Single<&mut Text2d, (With<MapTitle>, Without<InfoName>, Without<InfoLine>)>,
    mut name: Single<&mut Text2d, (With<InfoName>, Without<MapTitle>, Without<InfoLine>)>,
    mut line: Single<&mut Text2d, (With<InfoLine>, Without<MapTitle>, Without<InfoName>)>,
    mut portrait: Single<&mut Sprite, (With<InfoPortrait>, Without<Node>, Without<Ring>)>,
    mut shown: Local<Option<(usize, usize, Option<usize>)>>,
    mut keep: Local<Vec<Handle<Image>>>,
) {
    // the circle pictures stay loaded: swapping a ring for the other frame would otherwise drop the one it leaves, and it
    // would have to load again (a flash) the next time round
    if keep.is_empty() {
        for name in ["node_open", "node_done", "node_locked", "node_boss", "node_select_0", "node_select_1"] {
            keep.push(assets.load(format!("ui/campaign/{name}.png")));
        }
    }
    let want = -(campaign.map as f32) * MAP_STEP;
    root.translation.x = want;
    for (MapCard(m), mut visibility) in &mut cards {
        let want = if *m == campaign.map { Visibility::Inherited } else { Visibility::Hidden };
        if *visibility != want { *visibility = want; }
    }

    let map = &maps.0.maps[campaign.map];
    let level = (!map.levels.is_empty()).then(|| &map.levels[campaign.level]);
    for (Node(m, l), mut sprite) in &mut nodes {
        let path = node_image(&maps.0, *m, *l, &saved.0);
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
            tf.translation.x = level.at.0 as f32 - MAP_W / 2.0;
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
            let rival = shown_rival(level, &roster, &campaign);
            let state = if !saved.0.campaign_unlocked(&maps.0, campaign.map) { "campaign locked" }
                else if !saved.0.can_play(&maps.0, campaign.map, campaign.level) { "locked" }
                else if saved.0.is_beaten(map, campaign.level) { "cleared" } else { "open" };
            (level.name.clone(), format!("{} fights > {rival}    {}    {}", map.preliminary_count(campaign.level), "*".repeat(level.difficulty as usize), state))
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
                let rival = shown_rival(level, &roster, &campaign);
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
    let (true, Some(_)) = (just_ended, campaign.active) else { return };
    let won = sim.0.match_winner() == Some(0);
    if campaign.record_result(won, &maps.0, &mut saved.0) {
        save_progress(&saved.0);
    }
}

/// The campaign's say in the end-of-match line, if a level is being fought.
pub fn banner_line(campaign: &Campaign, mode: Mode) -> Option<&'static str> {
    if mode != Mode::VsCpu || campaign.active.is_none() {
        return None;
    }
    Some(match campaign.won {
        Some(true) if campaign.last_encounter() => "Level cleared    Enter: map",
        Some(true) => "Enter: next opponent    Esc: map",
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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn every_level_fights_generics_before_its_real_rival_and_only_then_unlocks() {
        let maps = Maps(CampaignData::from_ron(include_str!("../assets/campaign/campaign.ron")).unwrap());
        let roster = Roster(crate::load_dir("characters", t2f::sim::CharacterData::from_ron));
        let stages = Stages(crate::load_dir("stages", t2f::stage::StageData::from_ron));
        let player = roster.0.iter().position(|c| c.name == "Katmata").unwrap();
        for (m, map) in maps.0.maps.iter().enumerate() {
            for (l, level) in map.levels.iter().enumerate() {
                let mut campaign = Campaign { map: m, level: l, ..default() };
                let mut selection = Selection::default();
                let mut progress = Progress::default();
                assert!(begin_level(&mut campaign, player, &maps, &roster, &stages, &mut selection));
                let count = if l + 1 == map.levels.len() { 3 } else { 2 };
                assert_eq!(campaign.opponents.len(), count + 1);
                for i in 0..count {
                    assert_eq!(campaign.encounter, i);
                    assert!(roster.0[selection.chars[1]].campaign_only);
                    assert!(roster.0[selection.chars[1]].name.is_empty());
                    assert!(!campaign.opponents[..i].contains(&selection.chars[1]));
                    // A defeat keeps this opponent and never grants progress.
                    assert!(!campaign.record_result(false, &maps.0, &mut progress));
                    assert!(!campaign.advance(&mut selection));
                    assert_eq!(campaign.encounter, i);
                    assert!(!campaign.record_result(true, &maps.0, &mut progress));
                    assert!(!progress.is_beaten(map, l));
                    assert_eq!(fight_square_color(m, l, i, &campaign, &maps.0, &progress), Color::srgb(0.4, 0.8, 0.5));
                    // Returning via the map resumes at the next fight.
                    assert!(begin_level(&mut campaign, player, &maps, &roster, &stages, &mut selection));
                    assert_eq!(campaign.encounter, i + 1);
                    assert_eq!(campaign.won, None);
                }
                assert_eq!(roster.0[selection.chars[1]].name, rival_for(level, &roster.0[player].name));
                assert!(campaign.last_encounter());
                assert!(!campaign.record_result(false, &maps.0, &mut progress));
                assert!(!progress.is_beaten(map, l));
                assert!(campaign.record_result(true, &maps.0, &mut progress));
                assert!(progress.is_beaten(map, l));
                assert!(!campaign.advance(&mut selection));
                // Re-entering even a cleared level starts its preliminary sequence again.
                assert!(begin_level(&mut campaign, player, &maps, &roster, &stages, &mut selection));
                assert_eq!(campaign.encounter, 0);
                assert!(roster.0[selection.chars[1]].campaign_only);
            }
        }
    }

    #[test]
    fn confirming_a_locked_campaign_does_not_open_character_select() {
        let data = CampaignData::from_ron(include_str!("../assets/campaign/campaign.ron")).unwrap();
        assert_eq!(node_image(&data, 2, 0, &Progress::default()), "ui/campaign/node_locked.png");
        let mut app = App::new();
        let mut keys = crate::MenuInput::default();
        keys.0.press(KeyCode::Enter);
        app.insert_resource(keys)
            .insert_resource(Maps(data))
            .insert_resource(Saved(Progress::default()))
            .insert_resource(Campaign { map: 2, ..default() })
            .insert_resource(Mode::VsCpu)
            .insert_resource(NextState::<AppState>::default())
            .add_message::<UiSound>()
            .add_systems(Update, campaign_input);
        app.update();
        assert!(!app.world().resource::<Campaign>().picking);
        assert!(matches!(app.world().resource::<NextState<AppState>>(), NextState::Unchanged));
        app.world_mut().resource_mut::<Campaign>().map = 0;
        app.update();
        assert!(app.world().resource::<Campaign>().picking);
        assert!(matches!(app.world().resource::<NextState<AppState>>(), NextState::Pending(AppState::CharSelect)));
    }

    #[test]
    fn campaign_view_queries_can_be_initialized_together() {
        let mut world = World::new();
        let mut system = IntoSystem::into_system(campaign_view);
        system.initialize(&mut world);
        let tile = surround_pattern(MapTheme::ForeignLands);
        assert_eq!((tile.width(), tile.height()), (16, 16));
    }

    #[test]
    fn complete_map_and_surround_fit_portrait_through_ultrawide() {
        for (w, h) in [(320.0, 240.0), (640.0, 480.0), (1280.0, 720.0), (1920.0, 1080.0), (1080.0, 1920.0), (2560.0, 1080.0), (5120.0, 1440.0)] {
            let view = view_size(w / h);
            assert!((view.x / view.y - w / h).abs() < 0.001);
            assert!(view.x / 2.0 >= MAP_W / 2.0);
            assert!(view.y / 2.0 >= MAP_Y + MAP_H / 2.0);
            assert!(-view.y / 2.0 <= MAP_Y - MAP_H / 2.0);
            // All decorative pieces, the title and the bottom hint fit too.
            for (sprite, position) in frame_parts(MapTheme::Istanbul).into_iter().chain(frame_parts(MapTheme::ForeignLands)).chain(frame_parts(MapTheme::SnowForests)) {
                let half = sprite.custom_size.unwrap() / 2.0;
                assert!(position.x.abs() + half.x <= view.x / 2.0);
                assert!((position.y + MAP_Y).abs() + half.y <= view.y / 2.0);
            }
            assert!(view.y / 2.0 >= 158.0);
            assert!(view.y / 2.0 >= 156.0);
        }
    }

    #[test]
    fn title_and_level_panel_do_not_cover_the_map_or_frame() {
        let frame_top = MAP_Y + (MAP_H + 20.0) / 2.0;
        let frame_bottom = MAP_Y - (MAP_H + 20.0) / 2.0;
        assert!(148.0 - 8.0 > frame_top);
        assert!(-128.0 + 20.0 < frame_bottom);
    }
}

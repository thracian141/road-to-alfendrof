//! Footprints in the snow: on a stage with a `footprints` picture, every step a fighter takes leaves a dent in the floor
//! (the feet take turns), and where they land after a jump there is a bigger one. The dents stay a good while, then
//! soften and fade.

use bevy::prelude::*;
use t2f::sim::{FighterState, PX};

use crate::{AppState, Sim, GROUND_Y};

/// The footprint picture of the stage being fought on (none: no footprints).
#[derive(Resource, Default)]
pub struct FootprintImage(pub Option<Handle<Image>>);

#[derive(Component)]
pub struct Footprint {
    born: f32,
}

/// Frames of walking between two steps (the same beat as the footstep sound).
const STEP_FRAMES: u32 = 14;
/// How long a dent lasts, in seconds, and how many can be on the floor at once.
const LIFE: f32 = 25.0;
const MAX_PRINTS: usize = 90;
/// How far apart the two feet are, in pixels.
const FOOT_OFFSET: f32 = 3.0;

#[derive(Default, Clone, Copy)]
pub struct Memory {
    walking: bool,
    step: u32,
    airborne: bool,
    right_foot: bool,
}

fn dent(commands: &mut Commands, image: &Handle<Image>, x: f32, now: f32, scale: Vec2) {
    commands.spawn((
        Footprint { born: now },
        DespawnOnExit(AppState::Fight),
        Sprite::from_image(image.clone()),
        // just inside the top of the floor, behind the fighters
        Transform::from_xyz(x, GROUND_Y - 2.0, 0.2).with_scale(scale.extend(1.0)),
    ));
}

/// A dent for each step and each landing.
pub fn leave_footprints(mut commands: Commands, sim: Res<Sim>, image: Res<FootprintImage>, time: Res<Time>, mut memory: Local<[Memory; 2]>) {
    let Some(image) = &image.0 else { return };
    let now = time.elapsed_secs();
    for (i, mem) in memory.iter_mut().enumerate() {
        let f = &sim.0.fighters[i];
        let x = (f.x / PX) as f32;
        let on_floor = f.y == 0;
        let walking = f.state == FighterState::Walk && on_floor;
        let step = f.state_frame / STEP_FRAMES;
        if walking && (!mem.walking || step != mem.step) {
            mem.step = step;
            mem.right_foot = !mem.right_foot;
            let foot = if mem.right_foot { FOOT_OFFSET } else { -FOOT_OFFSET };
            dent(&mut commands, image, x + foot, now, Vec2::ONE);
        }
        mem.walking = walking;
        // coming down: both feet at once, deeper
        if mem.airborne && on_floor && f.state != FighterState::Ko {
            dent(&mut commands, image, x, now, Vec2::new(1.9, 1.4));
        }
        mem.airborne = !on_floor;
    }
}

/// Old dents soften and fade over the last half of their life; the oldest go first when there are too many.
pub fn fade_footprints(mut commands: Commands, time: Res<Time>, mut prints: Query<(Entity, &Footprint, &mut Sprite)>) {
    let now = time.elapsed_secs();
    let mut alive: Vec<(f32, Entity)> = Vec::new();
    for (entity, print, mut sprite) in &mut prints {
        let age = now - print.born;
        if age > LIFE {
            commands.entity(entity).despawn();
            continue;
        }
        let alpha = (1.0 - ((age / LIFE) - 0.5).max(0.0) * 2.0).clamp(0.0, 1.0);
        let color = Color::srgba(1.0, 1.0, 1.0, alpha);
        if sprite.color != color {
            sprite.color = color;
        }
        alive.push((print.born, entity));
    }
    if alive.len() > MAX_PRINTS {
        alive.sort_by(|a, b| a.0.total_cmp(&b.0));
        for (_, entity) in alive.iter().take(alive.len() - MAX_PRINTS) {
            commands.entity(*entity).despawn();
        }
    }
}

//! The campaign: maps with levels on them, each level a fight against a fixed rival on a stage, and how far the player got.

use serde::{Deserialize, Serialize};

/// Loaded from `assets/campaign/campaign.ron`.
#[derive(Clone, Debug, Deserialize)]
pub struct CampaignData {
    pub maps: Vec<MapData>,
}

#[derive(Clone, Debug, Deserialize)]
pub struct MapData {
    /// Short name used in the saved progress.
    pub id: String,
    /// Shown as the map's title.
    pub name: String,
    /// The picture (path under `assets/`), shown 384 x 224 units.
    pub image: String,
    #[serde(default)]
    pub theme: MapTheme,
    /// Levels in the order they are played; none on a map that is only a preview.
    #[serde(default)]
    pub levels: Vec<LevelData>,
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, Deserialize)]
pub enum MapTheme {
    #[default]
    Istanbul,
    ForeignLands,
    SnowForests,
}

#[derive(Clone, Debug, Deserialize)]
pub struct LevelData {
    pub name: String,
    /// Where its circle is, in map units (384 x 224) from the picture's top left.
    pub at: (i32, i32),
    /// A stage's name (see `assets/stages`).
    pub stage: String,
    /// A character's name; another one fights instead if the player is playing that one.
    pub rival: String,
    /// 1 (easy) to 5 (hard): how well the CPU plays.
    pub difficulty: u8,
    /// The map's last fight.
    #[serde(default)]
    pub boss: bool,
}

/// Who fights instead when the rival is the player's own fighter, in this order.
pub const FALLBACK_RIVALS: [&str; 4] = ["The Professor", "The Scribe", "Haymaker", "Cowboy From Hell"];

impl CampaignData {
    pub fn from_ron(text: &str) -> Result<Self, ron::error::SpannedError> {
        ron::from_str(text)
    }

    /// Browsing includes locked levels and preview maps; only starting a fight checks progress.
    pub fn browse(&self, map: usize, level: usize, dir: i32) -> (usize, usize) {
        let last = self.maps[map].levels.len().saturating_sub(1);
        if dir > 0 {
            if level < last { (map, level + 1) }
            else if map + 1 < self.maps.len() { (map + 1, 0) }
            else { (map, level) }
        } else if dir < 0 {
            if level > 0 { (map, level - 1) }
            else if map > 0 { (map - 1, self.maps[map - 1].levels.len().saturating_sub(1)) }
            else { (map, level) }
        } else { (map, level) }
    }
}

impl MapData {
    /// The name a level is saved under.
    pub fn level_id(&self, level: usize) -> String {
        format!("{}/{}", self.id, level + 1)
    }
}

/// The rival for `level`: its own, unless that is the player's fighter.
pub fn rival_for<'a>(level: &'a LevelData, player: &str) -> &'a str {
    if level.rival != player {
        return &level.rival;
    }
    FALLBACK_RIVALS.iter().copied().find(|name| *name != player && *name != level.rival).unwrap_or(&level.rival)
}

/// Which levels have been beaten. Saved as `campaign.ron` next to the settings.
#[derive(Clone, Debug, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct Progress {
    #[serde(default)]
    pub beaten: Vec<String>,
    /// Last playable campaign visited, used by the home screen across launches.
    #[serde(default)]
    pub last_map: Option<String>,
}

impl Progress {
    /// Finish the earlier campaigns before starting this one. Empty previews are never playable.
    pub fn campaign_unlocked(&self, campaign: &CampaignData, map: usize) -> bool {
        campaign.maps.get(map).is_some_and(|m| !m.levels.is_empty())
            && campaign.maps[..map].iter().all(|m| (0..m.levels.len()).all(|l| self.is_beaten(m, l)))
    }

    pub fn can_play(&self, campaign: &CampaignData, map: usize, level: usize) -> bool {
        self.campaign_unlocked(campaign, map)
            && level < campaign.maps[map].levels.len()
            && self.is_unlocked(&campaign.maps[map], level)
    }

    pub fn last_campaign(&self, campaign: &CampaignData) -> usize {
        self.last_map.as_deref()
            .and_then(|id| campaign.maps.iter().position(|m| m.id == id && !m.levels.is_empty()))
            .unwrap_or_else(|| campaign.maps.iter().position(|m| !m.levels.is_empty()).unwrap_or(0))
    }

    /// Preview-only maps do not replace the last real campaign on the title.
    pub fn visit(&mut self, map: &MapData) -> bool {
        if map.levels.is_empty() || self.last_map.as_deref() == Some(&map.id) {
            return false;
        }
        self.last_map = Some(map.id.clone());
        true
    }

    pub fn is_beaten(&self, map: &MapData, level: usize) -> bool {
        self.beaten.contains(&map.level_id(level))
    }

    /// A level can be played once the one before it is beaten (the first always can).
    pub fn is_unlocked(&self, map: &MapData, level: usize) -> bool {
        level == 0 || self.is_beaten(map, level - 1)
    }

    /// Records a win. Returns whether it was the first.
    pub fn beat(&mut self, map: &MapData, level: usize) -> bool {
        let id = map.level_id(level);
        if self.beaten.contains(&id) {
            return false;
        }
        self.beaten.push(id);
        true
    }

    /// The first level not beaten yet (the last one when all are).
    pub fn current(&self, map: &MapData) -> usize {
        (0..map.levels.len()).find(|&i| !self.is_beaten(map, i)).unwrap_or(map.levels.len().saturating_sub(1))
    }

    /// The level one step along (`dir` is 1 or -1) from `from`, staying on levels that can be played.
    pub fn step(&self, map: &MapData, from: usize, dir: i32) -> usize {
        let to = (from as i32 + dir).clamp(0, map.levels.len() as i32 - 1).max(0) as usize;
        if self.is_unlocked(map, to) { to } else { from }
    }

    pub fn from_ron(text: &str) -> Progress {
        ron::from_str(text).unwrap_or_default()
    }

    pub fn to_ron(&self) -> String {
        ron::ser::to_string_pretty(self, ron::ser::PrettyConfig::default()).unwrap_or_default()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::sim::CharacterData;
    use crate::stage::StageData;

    fn data() -> CampaignData {
        CampaignData::from_ron(&std::fs::read_to_string("assets/campaign/campaign.ron").unwrap()).unwrap()
    }

    #[test]
    fn every_rival_and_stage_in_the_campaign_exists() {
        let characters: Vec<String> = std::fs::read_dir("assets/characters")
            .unwrap()
            .filter_map(|e| e.ok())
            .filter(|e| e.path().extension().is_some_and(|x| x == "ron"))
            .map(|e| CharacterData::from_ron(&std::fs::read_to_string(e.path()).unwrap()).unwrap().name)
            .collect();
        let stages: Vec<String> = std::fs::read_dir("assets/stages")
            .unwrap()
            .filter_map(|e| e.ok())
            .filter(|e| e.path().extension().is_some_and(|x| x == "ron"))
            .map(|e| StageData::from_ron(&std::fs::read_to_string(e.path()).unwrap()).unwrap().name)
            .collect();
        let campaign = data();
        assert!(campaign.maps.len() >= 2);
        for name in FALLBACK_RIVALS {
            assert!(characters.iter().any(|c| c == name), "fallback rival {name}");
        }
        for map in &campaign.maps {
            assert!(std::path::Path::new("assets").join(&map.image).exists(), "{} picture {}", map.name, map.image);
            for level in &map.levels {
                assert!(characters.iter().any(|c| *c == level.rival), "{}: rival {}", level.name, level.rival);
                assert!(stages.iter().any(|s| *s == level.stage), "{}: stage {}", level.name, level.stage);
                assert!((1..=5).contains(&level.difficulty), "{}: difficulty", level.name);
                assert!((0..384).contains(&level.at.0) && (0..224).contains(&level.at.1), "{}: inside the map", level.name);
            }
        }
    }

    #[test]
    fn the_first_map_has_five_levels_and_ends_at_galata_tower() {
        let campaign = data();
        let city = &campaign.maps[0];
        assert_eq!(city.name, "The City");
        assert_eq!(city.levels.len(), 5);
        assert_eq!(city.levels[0].stage, "Istanbul Courtyard");
        let last = city.levels.last().unwrap();
        assert_eq!((last.name.as_str(), last.stage.as_str(), last.boss), ("Galata Tower", "Galata Tower", true));
        assert!(campaign.maps[3].levels.is_empty(), "the next map is only a preview");
        // the circles don't sit on top of each other
        for (i, a) in city.levels.iter().enumerate() {
            for b in &city.levels[i + 1..] {
                assert!((a.at.0 - b.at.0).abs() + (a.at.1 - b.at.1).abs() > 20, "{} and {} overlap", a.name, b.name);
            }
        }
    }

    #[test]
    fn foreign_lands_has_the_requested_five_opponents_and_temporary_stage() {
        let campaign = data();
        let map = &campaign.maps[1];
        assert_eq!(map.name, "The Foreign Lands");
        assert_eq!(map.theme, MapTheme::ForeignLands);
        assert_eq!(map.levels.len(), 5);
        assert_eq!(map.levels[0].name, "Assgrad");
        let rivals: Vec<_> = map.levels.iter().map(|l| l.rival.as_str()).collect();
        assert_eq!(rivals, ["Katmata", "Haymaker", "Katmata", "Cowboy From Hell", "Junkhead"]);
        assert!(map.levels.iter().all(|l| l.stage == "Assgrad"));
        assert!(map.levels[4].boss);
        assert!(map.levels[..4].iter().all(|l| !l.boss));
    }

    #[test]
    fn browsing_locked_campaigns_does_not_allow_starting_them() {
        let campaign = data();
        let mut progress = Progress::default();
        let mut cursor = (0, 0);
        for _ in 0..10 { cursor = campaign.browse(cursor.0, cursor.1, 1); }
        assert_eq!(cursor, (2, 0));
        assert!(progress.can_play(&campaign, 0, 0));
        assert!(!progress.can_play(&campaign, 0, 1));
        assert!(!progress.can_play(&campaign, 1, 0));
        assert!(!progress.can_play(&campaign, 2, 0));
        for l in 0..campaign.maps[0].levels.len() { progress.beat(&campaign.maps[0], l); }
        assert!(progress.can_play(&campaign, 1, 0));
        assert!(!progress.can_play(&campaign, 1, 1));
        assert!(!progress.can_play(&campaign, 2, 0));
        for l in 0..campaign.maps[1].levels.len() { progress.beat(&campaign.maps[1], l); }
        assert!(progress.can_play(&campaign, 2, 0));
        assert!(!progress.can_play(&campaign, 3, 0));
        assert_eq!(campaign.browse(3, 0, -1), (2, 2));
        assert_eq!(campaign.browse(0, 0, -1), (0, 0));
        assert_eq!(campaign.browse(3, 0, 1), (3, 0));
    }

    #[test]
    fn snow_forests_has_three_fights_and_remembers_its_home_background() {
        let campaign = data();
        let map = &campaign.maps[2];
        assert_eq!(map.name, "Snow Forests");
        assert_eq!(map.theme, MapTheme::SnowForests);
        assert_eq!(map.levels.iter().map(|l| l.rival.as_str()).collect::<Vec<_>>(), ["Haymaker", "Goblin King", "Anaran"]);
        assert!(map.levels[2].boss);
        assert!(map.levels[..2].iter().all(|l| !l.boss));
        let mut progress = Progress::default();
        progress.visit(map);
        assert_eq!(Progress::from_ron(&progress.to_ron()).last_campaign(&campaign), 2);
    }

    #[test]
    fn last_campaign_survives_restart_without_resetting_level_progress() {
        let campaign = data();
        let mut progress = Progress::from_ron("(beaten: [\"the_city/1\"])");
        assert_eq!(progress.last_campaign(&campaign), 0);
        assert!(progress.visit(&campaign.maps[1]));
        assert!(!progress.visit(&campaign.maps[1]));
        let mut restored = Progress::from_ron(&progress.to_ron());
        assert_eq!(restored.last_campaign(&campaign), 1);
        assert!(restored.is_beaten(&campaign.maps[0], 0));
        assert!(!restored.visit(&campaign.maps[3]), "a preview is not a campaign");
        assert_eq!(restored.last_campaign(&campaign), 1);
        assert!(restored.visit(&campaign.maps[0]));
        assert_eq!(restored.last_campaign(&campaign), 0);
        restored.last_map = Some("removed_campaign".into());
        assert_eq!(restored.last_campaign(&campaign), 0);
    }

    #[test]
    fn levels_unlock_in_order_and_beating_one_twice_counts_once() {
        let campaign = data();
        let map = &campaign.maps[0];
        let mut progress = Progress::default();
        assert!(progress.is_unlocked(map, 0));
        assert!(!progress.is_unlocked(map, 1));
        assert_eq!(progress.current(map), 0);
        assert!(progress.beat(map, 0));
        assert!(!progress.beat(map, 0));
        assert!(progress.is_unlocked(map, 1) && !progress.is_unlocked(map, 2));
        assert_eq!(progress.current(map), 1);
        // moving along the map stops at the first locked level
        assert_eq!(progress.step(map, 0, 1), 1);
        assert_eq!(progress.step(map, 1, 1), 1);
        assert_eq!(progress.step(map, 1, -1), 0);
        assert_eq!(progress.step(map, 0, -1), 0);
        for level in 1..map.levels.len() {
            progress.beat(map, level);
        }
        assert_eq!(progress.current(map), map.levels.len() - 1);
        assert_eq!(progress.step(map, 3, 1), 4);
        assert_eq!(progress.step(map, 4, 1), 4);
    }

    #[test]
    fn the_rival_is_never_the_players_own_fighter() {
        let campaign = data();
        for level in &campaign.maps[0].levels {
            assert_ne!(rival_for(level, "Haymaker"), "Haymaker");
            assert_eq!(rival_for(level, "Nobody"), level.rival);
            assert_ne!(rival_for(level, &level.rival), level.rival, "{} swaps its rival", level.name);
        }
        // the fallback is not the player's fighter either
        let level = &campaign.maps[0].levels[0];
        let swapped = rival_for(level, &level.rival);
        assert_ne!(rival_for(level, swapped), swapped);
    }

    #[test]
    fn progress_is_saved_and_an_unreadable_file_means_a_fresh_start() {
        let campaign = data();
        let map = &campaign.maps[0];
        let mut progress = Progress::default();
        progress.beat(map, 0);
        progress.beat(map, 1);
        assert_eq!(Progress::from_ron(&progress.to_ron()), progress);
        assert_eq!(Progress::from_ron("this is not ron"), Progress::default());
        // an older file without the list still loads
        assert_eq!(Progress::from_ron("()"), Progress::default());
    }
}

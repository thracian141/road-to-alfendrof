//! Every character file parses, and every sound its moves name exists in `assets/sfx`.

use std::path::PathBuf;

use t2f::sim::CharacterData;

fn assets() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("assets")
}

/// `name.wav`, or `name_0.wav`, `name_1.wav`...
fn sound_exists(name: &str) -> bool {
    std::fs::read_dir(assets().join("sfx")).unwrap().flatten().any(|entry| {
        let file = entry.file_name().into_string().unwrap();
        let Some(stem) = file.strip_suffix(".wav") else { return false };
        stem == name || stem.strip_prefix(name).and_then(|rest| rest.strip_prefix('_')).is_some_and(|n| !n.is_empty() && n.bytes().all(|b| b.is_ascii_digit()))
    })
}

#[test]
fn every_character_parses_and_its_sounds_exist() {
    let mut checked = 0;
    for entry in std::fs::read_dir(assets().join("characters")).unwrap().flatten() {
        let path = entry.path();
        if path.extension().is_none_or(|e| e != "ron") {
            continue;
        }
        let text = std::fs::read_to_string(&path).unwrap();
        let data = CharacterData::from_ron(&text).unwrap_or_else(|e| panic!("{}: {e}", path.display()));
        for mv in &data.moves {
            for name in [&mv.sfx.cast, &mv.sfx.launch, &mv.sfx.hit, &mv.sfx.block].into_iter().flatten() {
                // an empty name is a deliberate silence
                assert!(name.is_empty() || sound_exists(name), "{}: move {:?} names a sound that is not in assets/sfx: {name:?}", path.display(), mv.name);
                checked += 1;
            }
        }
    }
    assert!(checked > 20, "only {checked} sound names found");
}

/// A move's spells (Anaran's light): every chant is a sound, and every picture of every drawing is on disk.
#[test]
fn every_spell_has_its_chant_and_its_pictures() {
    let mut checked = 0;
    for entry in std::fs::read_dir(assets().join("characters")).unwrap().flatten() {
        let path = entry.path();
        if path.extension().is_none_or(|e| e != "ron") {
            continue;
        }
        let data = CharacterData::from_ron(&std::fs::read_to_string(&path).unwrap()).unwrap();
        let folder = data.sprites.clone().unwrap_or_else(|| data.name.to_lowercase());
        for mv in &data.moves {
            for spell in &mv.spells {
                assert!(sound_exists(&spell.chant), "{}: spell {:?} has no chant {:?}", path.display(), spell.image, spell.chant);
                assert!(spell.drawings > 0, "{}: spell {:?} has no drawings", path.display(), spell.image);
                for i in 0..spell.drawings {
                    let picture = assets().join("sprites").join(&folder).join(format!("{}_{i}.png", spell.image));
                    assert!(picture.exists(), "missing {}", picture.display());
                }
                checked += 1;
            }
        }
    }
    assert!(checked >= 5, "only {checked} spells found");
}

#[test]
fn the_generic_sounds_exist() {
    for name in [
        "whoosh_light", "whoosh_heavy", "hit_small", "hit_large", "hit_heavy", "block_small", "block_large", "ko", "smash",
        "jump", "jump_double", "land", "dash", "roll", "step", "guard", "guard_break",
        "round_start", "round_end", "match_win", "ui_move", "ui_confirm", "ui_back",
    ] {
        assert!(sound_exists(name), "missing generic sound {name:?}");
    }
}

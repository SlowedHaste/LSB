#!/usr/bin/env python3
"""
Convert the fishing SQL datasets into Lua tables.

This script reads the legacy SQL dumps from `sql/` and emits Lua data tables
under `scripts/globals/fishing/data/`. Runtime code can then consume the Lua
tables instead of querying the database.
"""

from __future__ import annotations

import re
import struct
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


SQL_DIR = Path("sql")
OUT_DIR = Path("scripts/globals/fishing/data")


def split_values(chunk: str) -> list[str]:
    """Split a VALUES payload while respecting quoted strings."""
    values: list[str] = []
    current: list[str] = []
    in_string = False
    escape = False

    for char in chunk:
        if in_string:
            if escape:
                current.append(char)
                escape = False
            elif char == "\\":
                escape = True
            elif char == "'":
                current.append(char)
                in_string = False
            else:
                current.append(char)
        else:
            if char == "'":
                current.append(char)
                in_string = True
            elif char == ",":
                values.append("".join(current).strip())
                current = []
            else:
                current.append(char)

    if current:
        values.append("".join(current).strip())

    return values


def parse_value(raw: str) -> Any:
    raw = raw.strip()
    if raw.upper() == "NULL":
        return None
    if raw.startswith("0x"):
        return bytes.fromhex(raw[2:])
    if raw.startswith("'") and raw.endswith("'"):
        value = raw[1:-1]
        value = value.replace("\\'", "'")
        value = value.replace("\r\n", "\n").replace("\n", " ")
        return value
    if "." in raw:
        return float(raw)
    return int(raw)


def parse_rows(sql_file: Path, columns: list[str]) -> Iterable[dict[str, Any]]:
    pattern = re.compile(r"INSERT INTO `[^`]+` VALUES\s*\((.*?)\);", re.DOTALL)
    text = sql_file.read_text(encoding="utf-8")

    for match in pattern.finditer(text):
        values = split_values(match.group(1))
        if len(values) != len(columns):
            raise ValueError(f"{sql_file} expected {len(columns)} values, got {len(values)}")
        yield {col: parse_value(val) for col, val in zip(columns, values)}


def format_bool(value: bool) -> str:
    return "true" if value else "false"


def format_float(value: float) -> str:
    formatted = f"{value:.6f}".rstrip("0").rstrip(".")
    return formatted or "0"


def parse_bounds(blob: bytes | None) -> list[dict[str, float]]:
    if not blob:
        return []

    vectors: list[dict[str, float]] = []
    last_non_zero = -1

    for idx in range(0, len(blob), 12):
        if idx + 12 > len(blob):
            break
        x, y, z = struct.unpack_from("<fff", blob, idx)
        vectors.append({"x": x, "y": y, "z": z})
        if x != 0 or y != 0 or z != 0:
            last_non_zero = len(vectors) - 1

    if last_non_zero >= 0:
        return vectors[: last_non_zero + 1]
    return []


def parse_required_catches(blob: bytes | None) -> list[int]:
    if not blob:
        return []

    catches: list[int] = []
    for idx in range(0, len(blob), 2):
        if idx + 2 > len(blob):
            break
        fish_id = int.from_bytes(blob[idx : idx + 2], "little")
        if fish_id == 0:
            break
        catches.append(fish_id)
    return catches


def lua_table(lines: list[str], indent: int = 0) -> list[str]:
    prefix = " " * indent
    return [f"{prefix}{{"] + lines + [f"{prefix}}}"]


def write_lua_file(path: Path, content: list[str]) -> None:
    path.write_text("\n".join(content) + "\n", encoding="utf-8")


def write_simple_map(path: Path, data: dict[int, dict[str, Any]]) -> None:
    lines: list[str] = ["return {"]
    for key in sorted(data):
        entry = data[key]
        parts = [f'name = "{entry["name"]}"'] if "name" in entry else []
        for k, v in entry.items():
            if k == "name":
                continue
            if isinstance(v, bool):
                parts.append(f"{k} = {format_bool(v)}")
            else:
                parts.append(f"{k} = {v}")
        joined = ", ".join(parts)
        lines.append(f"    [{key}] = {{ {joined} }},")
    lines.append("}")
    write_lua_file(path, lines)


def write_areas(path: Path, areas: dict[int, dict[int, dict[str, Any]]]) -> None:
    lines: list[str] = ["return {"]
    for zone_id in sorted(areas):
        lines.append(f"    [{zone_id}] = {{")
        for area_id in sorted(areas[zone_id]):
            area = areas[zone_id][area_id]
            lines.append(f'        [{area_id}] = {{ name = "{area["name"]}", boundType = {area["bound_type"]}, boundHeight = {area["bound_height"]}, boundRadius = {area["bound_radius"]}, difficulty = {area["difficulty"]},')
            lines.append(
                f'            center = {{ x = {format_float(area["center_x"])}, y = {format_float(area["center_y"])}, z = {format_float(area["center_z"])} }},'
            )
            if area["bounds"]:
                lines.append("            bounds = {")
                for vec in area["bounds"]:
                    lines.append(
                        f'                {{ x = {format_float(vec["x"])}, y = {format_float(vec["y"])}, z = {format_float(vec["z"])} }},'
                    )
                lines.append("            },")
            else:
                lines.append("            bounds = {},")
            lines.append("        },")
        lines.append("    },")
    lines.append("}")
    write_lua_file(path, lines)


def write_fish(path: Path, fish: dict[int, dict[str, Any]]) -> None:
    lines: list[str] = ["return {"]
    for fish_id in sorted(fish):
        entry = fish[fish_id]
        lines.append(f'    [{fish_id}] = {{ name = "{entry["name"]}", skill = {entry["skill_level"]}, difficulty = {entry["difficulty"]}, baseDelay = {entry["base_delay"]}, baseMove = {entry["base_move"]}, minLength = {entry["min_length"]}, maxLength = {entry["max_length"]},')
        lines.append(
            f'        sizeType = {entry["size_type"]}, waterType = {entry["water_type"]}, log = {entry["log"]}, quest = {entry["quest"]}, flags = {entry["flags"]}, legendary = {format_bool(entry["legendary"])}, legendaryFlags = {entry["legendary_flags"]},'
        )
        lines.append(
            f'        item = {format_bool(entry["item"])}, maxHook = {entry["max_hook"]}, rarity = {entry["rarity"]}, requiredKeyItem = {entry["required_keyitem"]}, questStatus = {entry["quest_status"]}, questOnly = {format_bool(entry["quest_only"])}, ranking = {entry["ranking"]}, contest = {format_bool(entry["contest"])},'
        )
        if entry["required_catches"]:
            catches = ", ".join(str(v) for v in entry["required_catches"])
            lines.append(f"        requiredCatches = {{ {catches} }},")
        else:
            lines.append("        requiredCatches = {},")
        lines.append("    },")
    lines.append("}")
    write_lua_file(path, lines)


def write_mobs(path: Path, mobs: dict[int, dict[str, Any]]) -> None:
    lines: list[str] = ["return {"]
    for mob_id in sorted(mobs):
        entry = mobs[mob_id]
        lines.append(
            f'    [{mob_id}] = {{ name = "{entry["name"]}", zoneId = {entry["zoneid"]}, level = {entry["level"]}, minLength = {entry["min_length"]}, maxLength = {entry["max_length"]}, ranking = {entry["ranking"]}, difficulty = {entry["difficulty"]}, baseDelay = {entry["base_delay"]}, baseMove = {entry["base_move"]}, log = {entry["log"]}, quest = {entry["quest"]},'
        )
        lines.append(
            f'        nm = {format_bool(entry["nm"])}, nmFlags = {entry["nm_flags"]}, areaId = {entry["areaid"]}, rarity = {entry["rarity"]}, minRespawn = {entry["min_respawn"]}, maxRespawn = {entry["max_respawn"]}, requiredBaitId = {entry["required_baitid"]}, alternativeBaitId = {entry["alternative_baitid"]}, requiredKeyItem = {entry["required_keyitem"]}, questOnly = {format_bool(entry["quest_only"])},'
        )
        lines.append("    },")
    lines.append("}")
    write_lua_file(path, lines)


def write_baits(path: Path, baits: dict[int, dict[str, Any]]) -> None:
    lines: list[str] = ["return {"]
    for bait_id in sorted(baits):
        entry = baits[bait_id]
        lines.append(
            f'    [{bait_id}] = {{ name = "{entry["name"]}", type = {entry["type"]}, maxHook = {entry["maxhook"]}, losable = {format_bool(entry["losable"])}, flags = {entry["flags"]}, mmm = {format_bool(entry["mmm"])}, rankMod = {entry["rankmod"]} }},'
        )
    lines.append("}")
    write_lua_file(path, lines)


def write_affinities(path: Path, affinities: dict[int, dict[int, int]]) -> None:
    lines: list[str] = ["return {"]
    for bait_id in sorted(affinities):
        lines.append(f"    [{bait_id}] = {{")
        for fish_id in sorted(affinities[bait_id]):
            lines.append(f"        [{fish_id}] = {affinities[bait_id][fish_id]},")
        lines.append("    },")
    lines.append("}")
    write_lua_file(path, lines)


def write_groups(path: Path, groups: dict[int, dict[int, dict[str, int]]]) -> None:
    lines: list[str] = ["return {"]
    for group_id in sorted(groups):
        lines.append(f"    [{group_id}] = {{")
        for fish_id in sorted(groups[group_id]):
            entry = groups[group_id][fish_id]
            lines.append(f'        [{fish_id}] = {{ rarity = {entry["rarity"]}, poolSize = {entry["pool_size"]}, restockRate = {entry["restock_rate"]} }},')
        lines.append("    },")
    lines.append("}")
    write_lua_file(path, lines)


def write_catches(path: Path, catches: dict[int, dict[int, int]]) -> None:
    lines: list[str] = ["return {"]
    for zone_id in sorted(catches):
        lines.append(f"    [{zone_id}] = {{")
        for area_id in sorted(catches[zone_id]):
            lines.append(f"        [{area_id}] = {catches[zone_id][area_id]},")
        lines.append("    },")
    lines.append("}")
    write_lua_file(path, lines)


def write_aggregate(path: Path) -> None:
    content = [
        "return {",
        '    zones = require("scripts/globals/fishing/data/zones"),',
        '    areas = require("scripts/globals/fishing/data/areas"),',
        '    fish = require("scripts/globals/fishing/data/fish"),',
        '    mobs = require("scripts/globals/fishing/data/mobs"),',
        '    rods = require("scripts/globals/fishing/data/rods"),',
        '    baits = require("scripts/globals/fishing/data/baits"),',
        '    baitAffinities = require("scripts/globals/fishing/data/bait_affinities"),',
        '    groups = require("scripts/globals/fishing/data/groups"),',
        '    catches = require("scripts/globals/fishing/data/catches"),',
        "}",
    ]
    write_lua_file(path, content)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    zones = {
        row["zoneid"]: {"name": row["name"], "difficulty": row["difficulty"]}
        for row in parse_rows(SQL_DIR / "fishing_zone.sql", ["zoneid", "name", "difficulty"])
    }

    areas: dict[int, dict[int, dict[str, Any]]] = defaultdict(dict)
    for row in parse_rows(
        SQL_DIR / "fishing_area.sql",
        ["zoneid", "areaid", "name", "bound_type", "bound_height", "bound_radius", "bounds", "center_x", "center_y", "center_z"],
    ):
        zone_difficulty = zones.get(row["zoneid"], {}).get("difficulty", 0)
        areas[row["zoneid"]][row["areaid"]] = {
            "name": row["name"],
            "bound_type": row["bound_type"],
            "bound_height": row["bound_height"],
            "bound_radius": row["bound_radius"],
            "bounds": parse_bounds(row["bounds"]),
            "center_x": row["center_x"],
            "center_y": row["center_y"],
            "center_z": row["center_z"],
            "difficulty": zone_difficulty,
        }

    fish: dict[int, dict[str, Any]] = {}
    for row in parse_rows(
        SQL_DIR / "fishing_fish.sql",
        [
            "fishid",
            "name",
            "skill_level",
            "difficulty",
            "base_delay",
            "base_move",
            "min_length",
            "max_length",
            "ranking",
            "size_type",
            "water_type",
            "log",
            "quest",
            "quest_status",
            "flags",
            "hour_pattern",
            "moon_pattern",
            "month_pattern",
            "legendary",
            "legendary_flags",
            "item",
            "max_hook",
            "rarity",
            "required_keyitem",
            "required_catches",
            "family",
            "quest_only",
            "contest",
            "disabled",
        ],
    ):
        if row["disabled"] or row["ranking"] >= 99:
            continue
        fish[row["fishid"]] = {
            "name": row["name"],
            "skill_level": row["skill_level"],
            "difficulty": row["difficulty"],
            "base_delay": row["base_delay"],
            "base_move": row["base_move"],
            "min_length": row["min_length"],
            "max_length": row["max_length"],
            "size_type": row["size_type"],
            "water_type": row["water_type"],
            "log": row["log"],
            "quest": row["quest"],
            "flags": row["flags"],
            "legendary": bool(row["legendary"]),
            "legendary_flags": row["legendary_flags"],
            "item": bool(row["item"]),
            "max_hook": row["max_hook"],
            "rarity": row["rarity"],
            "required_keyitem": row["required_keyitem"],
            "required_catches": parse_required_catches(row["required_catches"]),
            "quest_status": row["quest_status"],
            "quest_only": bool(row["quest_only"]),
            "ranking": row["ranking"],
            "contest": bool(row["contest"]),
        }

    mobs: dict[int, dict[str, Any]] = {}
    for row in parse_rows(
        SQL_DIR / "fishing_mob.sql",
        [
            "mobid",
            "name",
            "zoneid",
            "level",
            "min_length",
            "max_length",
            "ranking",
            "difficulty",
            "base_delay",
            "base_move",
            "log",
            "quest",
            "nm",
            "nm_flags",
            "areaid",
            "rarity",
            "min_respawn",
            "max_respawn",
            "required_baitid",
            "alternative_baitid",
            "required_keyitem",
            "quest_only",
            "disabled",
        ],
    ):
        if row["disabled"]:
            continue
        mobs[row["mobid"]] = {
            "name": row["name"],
            "zoneid": row["zoneid"],
            "level": row["level"],
            "min_length": row["min_length"],
            "max_length": row["max_length"],
            "ranking": row["ranking"],
            "difficulty": row["difficulty"],
            "base_delay": row["base_delay"],
            "base_move": row["base_move"],
            "log": row["log"],
            "quest": row["quest"],
            "nm": bool(row["nm"]),
            "nm_flags": row["nm_flags"],
            "areaid": row["areaid"],
            "rarity": row["rarity"],
            "min_respawn": row["min_respawn"],
            "max_respawn": row["max_respawn"],
            "required_baitid": row["required_baitid"],
            "alternative_baitid": row["alternative_baitid"],
            "required_keyitem": row["required_keyitem"],
            "quest_only": bool(row["quest_only"]),
        }

    rods = {
        row["rodid"]: {
            "name": row["name"],
            "material": row["material"],
            "size_type": row["size_type"],
            "flags": row["flags"],
            "min_rank": row["min_rank"],
            "max_rank": row["max_rank"],
            "fish_attack": row["fish_attack"],
            "lgd_bonus_attack": row["lgd_bonus_attack"],
            "fish_recovery": row["fish_recovery"],
            "fish_time": row["fish_time"],
            "lgd_bonus_time": row["lgd_bonus_time"],
            "sm_delay_bonus": row["sm_delay_bonus"],
            "sm_move_bonus": row["sm_move_bonus"],
            "lg_delay_bonus": row["lg_delay_bonus"],
            "lg_move_bonus": row["lg_move_bonus"],
            "multiplier": row["multiplier"],
            "breakable": bool(row["breakable"]),
            "broken_rodid": row["broken_rodid"],
            "mmm": bool(row["mmm"]),
            "legendary": bool(row["legendary"]),
        }
        for row in parse_rows(
            SQL_DIR / "fishing_rod.sql",
            [
                "rodid",
                "name",
                "material",
                "size_type",
                "flags",
                "min_rank",
                "max_rank",
                "fish_attack",
                "lgd_bonus_attack",
                "fish_recovery",
                "fish_time",
                "lgd_bonus_time",
                "sm_delay_bonus",
                "sm_move_bonus",
                "lg_delay_bonus",
                "lg_move_bonus",
                "multiplier",
                "breakable",
                "broken_rodid",
                "mmm",
                "legendary",
                "rating",
            ],
        )
    }

    baits = {
        row["baitid"]: {
            "name": row["name"],
            "type": row["type"],
            "maxhook": row["maxhook"],
            "losable": bool(row["losable"]),
            "flags": row["flags"],
            "mmm": bool(row["mmm"]),
            "rankmod": row["rankmod"],
        }
        for row in parse_rows(
            SQL_DIR / "fishing_bait.sql",
            ["baitid", "name", "type", "maxhook", "losable", "flags", "mmm", "rankmod"],
        )
    }

    affinities: dict[int, dict[int, int]] = defaultdict(dict)
    for row in parse_rows(SQL_DIR / "fishing_bait_affinity.sql", ["baitid", "fishid", "power"]):
        affinities[row["baitid"]][row["fishid"]] = row["power"]

    groups: dict[int, dict[int, dict[str, int]]] = defaultdict(dict)
    for row in parse_rows(
        SQL_DIR / "fishing_group.sql",
        ["groupid", "fishid", "rarity", "pool_size", "restock_rate"],
    ):
        groups[row["groupid"]][row["fishid"]] = {
            "rarity": row["rarity"],
            "pool_size": row["pool_size"],
            "restock_rate": row["restock_rate"],
        }

    catches: dict[int, dict[int, int]] = defaultdict(dict)
    for row in parse_rows(SQL_DIR / "fishing_catch.sql", ["zoneid", "areaid", "groupid"]):
        catches[row["zoneid"]][row["areaid"]] = row["groupid"]

    write_simple_map(OUT_DIR / "zones.lua", zones)
    write_areas(OUT_DIR / "areas.lua", areas)
    write_fish(OUT_DIR / "fish.lua", fish)
    write_mobs(OUT_DIR / "mobs.lua", mobs)
    write_simple_map(OUT_DIR / "rods.lua", rods)
    write_baits(OUT_DIR / "baits.lua", baits)
    write_affinities(OUT_DIR / "bait_affinities.lua", affinities)
    write_groups(OUT_DIR / "groups.lua", groups)
    write_catches(OUT_DIR / "catches.lua", catches)
    write_aggregate(OUT_DIR.parent / "data.lua")


if __name__ == "__main__":
    main()

from __future__ import annotations

import json
import os
from pathlib import Path

from flask import Flask, abort, jsonify, make_response, redirect, render_template, request, send_file, send_from_directory, url_for
from PIL import Image, ImageOps


BASE_DIR = Path(__file__).resolve().parent
template_dir = BASE_DIR / "templates"
thumbnail_cache_dir = BASE_DIR / ".thumbnail_cache"

app = Flask(__name__, template_folder=str(template_dir), static_folder=None)

LANG_UI = {
    "zh": {"title": "教育游戏", "subtitle": "交互游戏，寓教于乐", "play": "进入游戏", "map": "查看地图"},
    "en": {"title": "Educational Games", "subtitle": "Interactive games, playful learning", "play": "Play", "map": "Narrative Map"},
}

GAME_META = {
    "tech_education": {"zh": "科技教育", "en": "Tech Education", "desc_zh": "科学实践中的观察、判断与安全选择。", "desc_en": "Observation, judgment, and safe choices in science practice."},
    "spring_outing": {"zh": "春游历险", "en": "Spring Outing Adventure", "desc_zh": "在户外探索中做出正确的风险判断。", "desc_en": "Make risk-aware decisions during an outdoor adventure."},
    "moving_house": {"zh": "搬家风波", "en": "Moving Day Chaos", "desc_zh": "用科学方法解决搬家过程中的麻烦。", "desc_en": "Use scientific thinking to solve moving-day problems."},
    "fire_rescue": {"zh": "火灾救援", "en": "Fire Rescue", "desc_zh": "高层火灾中的紧急避险与求生决策。", "desc_en": "Emergency survival choices during a high-rise fire."},
}

GAME_CONFIG = {
    "tech_education": {
        "json": {
            "zh": Path(r"d:\AAA\工作\work_on_vske\On_use\bilingual_versions\tech_education\story_graph_zh.json"),
            "en": Path(r"d:\AAA\工作\work_on_vske\On_use\bilingual_versions\tech_education\story_graph_en.json"),
        },
        "image_dirs": [Path(r"d:\AAA\工作\work_on_vske\On_use\cot_20260424_131513\output_images")],
    },
    "spring_outing": {
        "json": {
            "zh": Path(r"d:\AAA\工作\work_on_vske\On_use\bilingual_versions\spring_outing\story_graph_zh.json"),
            "en": Path(r"d:\AAA\工作\work_on_vske\On_use\bilingual_versions\spring_outing\story_graph_en.json"),
        },
        "image_dirs": [Path(r"d:\AAA\工作\work_on_vske\On_use\cot_20260424_123248\output_images")],
    },
    "moving_house": {
        "json": {
            "zh": Path(r"d:\AAA\工作\work_on_vske\On_use\bilingual_versions\moving_house\story_graph_zh.json"),
            "en": Path(r"d:\AAA\工作\work_on_vske\On_use\bilingual_versions\moving_house\story_graph_en.json"),
        },
        "image_dirs": [Path(r"d:\AAA\工作\work_on_vske\On_use\cot_20260425_111838\output_images")],
    },
    "fire_rescue": {
        "json": {
            # Use the exact ELK storyline bundle used by story_visualizer_narrative_elk_demo.py.
            "zh": Path(r"d:\AAA\工作\work_on_vske\On_use\demo_elk\output\fire_core_for_edu_new\output\story_graph_storyline_elk.json"),
            "en": Path(r"d:\AAA\工作\work_on_vske\On_use\demo_elk\output\fire_core_for_edu_new\output\story_graph_storyline_elk.json"),
        },
        "image_dirs": [Path(r"d:\AAA\工作\work_on_vske\On_use\demo_elk\output\fire_core_for_edu_new\output_images")],
    },
}


def validate_lang_game(lang: str, game_key: str) -> None:
    if lang not in LANG_UI:
        abort(404)
    if game_key not in GAME_CONFIG:
        abort(404)


def get_ctx_from_request() -> tuple[str, str]:
    lang = request.cookies.get("hub_lang", "zh")
    game_key = request.cookies.get("hub_game", "tech_education")
    if lang not in LANG_UI:
        lang = "zh"
    if game_key not in GAME_CONFIG:
        game_key = "tech_education"
    return lang, game_key


def set_ctx_cookie(response, lang: str, game_key: str):
    response.set_cookie("hub_lang", lang, max_age=7 * 24 * 3600)
    response.set_cookie("hub_game", game_key, max_age=7 * 24 * 3600)
    return response


def resolve_image_file(game_key: str, filename: str) -> Path | None:
    for img_dir in GAME_CONFIG[game_key]["image_dirs"]:
        candidate = img_dir / filename
        if candidate.exists():
            return candidate
    return None


def build_thumbnail_file(source_file: Path, cache_key: str, width: int, quality: int) -> Path:
    thumbnail_cache_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"{cache_key}_{width}_{quality}.jpg".replace("/", "_").replace("\\", "_")
    cached_file = thumbnail_cache_dir / safe_name
    source_mtime = source_file.stat().st_mtime
    if cached_file.exists() and cached_file.stat().st_mtime >= source_mtime:
        return cached_file
    with Image.open(source_file) as image:
        image = ImageOps.exif_transpose(image)
        image = image.convert("RGB")
        target_height = max(1, round(width * 9 / 16))
        image.thumbnail((width, target_height * 2))
        image.save(cached_file, format="JPEG", quality=quality, optimize=True)
    return cached_file


def get_node_type_info(node: dict, start_node_id: str, outgoing_count: int) -> dict:
    metadata = node.get("metadata", {}) or {}
    display_role = (metadata.get("display_role") or "").strip()
    node_id = node.get("id")
    node_type = (node.get("type") or "unknown").strip() or "unknown"
    role_styles = {
        "prologue": {"key": "prologue", "label": "Prologue", "color": "#8b5cf6"},
        "decision": {"key": "decision", "label": "Decision", "color": "#3b82f6"},
        "normal": {"key": "normal", "label": "Regular Event", "color": "#22c55e"},
        "success_end": {"key": "ending", "label": "Success End", "color": "#f97316"},
        "failure_end": {"key": "fatal", "label": "Failure End", "color": "#334155"},
    }
    if display_role in role_styles:
        return role_styles[display_role]
    if node_id == "node_1" or node_id == start_node_id:
        return role_styles["prologue"]
    if outgoing_count == 0:
        return role_styles["failure_end"]
    if outgoing_count >= 2 or node_type == "decision":
        return role_styles["decision"]
    return role_styles["normal"]


def collect_detail_fields(node: dict, incoming_count: int, outgoing_count: int, display_type_label: str = "") -> list[dict]:
    return [
        {"label": "Node ID", "value": node.get("id", "-")},
        {"label": "Node Type", "value": display_type_label or node.get("type", "-")},
        {"label": "Incoming", "value": str(incoming_count)},
        {"label": "Outgoing", "value": str(outgoing_count)},
    ]


def collect_neighbor_nodes(node_id: str, edges: dict, jump_edges: list[dict]) -> tuple[list[dict], list[dict]]:
    incoming, outgoing, seen_in, seen_out = [], [], set(), set()
    for source_id, targets in (edges or {}).items():
        if node_id in (targets or []) and source_id not in seen_in:
            seen_in.add(source_id)
            incoming.append({"id": source_id, "jump": False})
    for target_id in edges.get(node_id, []) or []:
        if target_id not in seen_out:
            seen_out.add(target_id)
            outgoing.append({"id": target_id, "jump": False})
    for item in jump_edges or []:
        source = item.get("source") or item.get("from")
        target = item.get("target") or item.get("to")
        if target == node_id and source and source not in seen_in:
            seen_in.add(source)
            incoming.append({"id": source, "jump": True})
        if source == node_id and target and target not in seen_out:
            seen_out.add(target)
            outgoing.append({"id": target, "jump": True})
    return incoming, outgoing


def build_processed_graph(story_graph: dict, lang: str, game_key: str) -> dict:
    raw_nodes = story_graph.get("nodes", []) or []
    edges = story_graph.get("edges", {}) or {}
    start_node_id = story_graph.get("start_node_id") or (raw_nodes[0].get("id") if raw_nodes else "")
    incoming_map: dict[str, list[str]] = {}
    for source_id, targets in edges.items():
        for target_id in targets or []:
            incoming_map.setdefault(target_id, []).append(source_id)

    processed_nodes, legend_map, image_count, ending_count = [], {}, 0, 0
    for node in raw_nodes:
        metadata = dict(node.get("metadata", {}) or {})
        outgoing = edges.get(node.get("id"), []) or []
        image_path_raw = metadata.get("image_path") or metadata.get("image_url")
        image_url, thumb_url = None, None
        if image_path_raw:
            filename = os.path.basename(str(image_path_raw).replace("\\", "/"))
            if filename:
                image_url = url_for("serve_game_image", lang=lang, game_key=game_key, filename=filename)
                thumb_url = url_for("serve_game_thumbnail", lang=lang, game_key=game_key, filename=filename)
                metadata["image_path"] = image_url
                metadata["image_url"] = image_url
                image_count += 1

        type_info = get_node_type_info(node, start_node_id, len(outgoing))
        legend_map[type_info["key"]] = {"key": type_info["key"], "label": type_info["label"], "color": type_info["color"]}
        incoming = incoming_map.get(node.get("id"), []) or []
        content = str(node.get("content", "") or "")
        preview = content.strip().replace("\n", " ")
        metadata["display_type_key"] = type_info["key"]
        processed_node = {
            "id": node.get("id"),
            "type": metadata.get("display_role") or node.get("type", "unknown"),
            "display_type": type_info["label"],
            "display_type_key": type_info["key"],
            "type_color": type_info["color"],
            "content": content,
            "preview": preview[:88] + ("..." if len(preview) > 88 else ""),
            "image_url": image_url,
            "thumbnail_url": thumb_url,
            "metadata": metadata,
            "incoming_count": len(incoming),
            "outgoing_count": len(outgoing),
            "detail_fields": collect_detail_fields(node, len(incoming), len(outgoing), type_info["label"]),
            "is_ending": type_info["key"] in {"ending", "fatal"},
        }
        if processed_node["is_ending"]:
            ending_count += 1
        processed_nodes.append(processed_node)

    for node in processed_nodes:
        edges.setdefault(node["id"], [])

    jump_edges = []
    for item in (story_graph.get("metadata", {}) or {}).get("jump_edges", []) or []:
        source_id = item.get("from")
        target_id = item.get("to")
        if source_id and target_id:
            jump_edges.append({"source": source_id, "target": target_id, "label": item.get("label", "")})

    for node in processed_nodes:
        incoming_nodes, outgoing_nodes = collect_neighbor_nodes(node["id"], edges, jump_edges)
        node["incoming_nodes"] = incoming_nodes
        node["outgoing_nodes"] = outgoing_nodes

    metadata = story_graph.get("metadata", {}) or {}
    layout_hints = metadata.get("layout_hints", {}) or {}
    return {
        "nodes": processed_nodes,
        "edges": edges,
        "start_node_id": start_node_id or (processed_nodes[0]["id"] if processed_nodes else ""),
        "ending_node_ids": [node["id"] for node in processed_nodes if node["is_ending"]],
        "jump_edges": jump_edges,
        "layout_hints": layout_hints,
        "metadata": metadata,
        "legend": list(legend_map.values()),
        "stats": {
            "node_count": len(processed_nodes),
            "edge_count": sum(len(targets or []) for targets in edges.values()),
            "ending_count": ending_count,
            "image_count": image_count,
            "jump_edge_count": len(jump_edges),
            "layout_mode": layout_hints.get("layout_mode", "elk_layered"),
            "layout_version": layout_hints.get("layout_version", ""),
        },
    }


@app.route("/")
def root():
    return redirect("/zh")


@app.route("/<lang>")
def hub_index(lang: str):
    if lang not in LANG_UI:
        abort(404)
    games = []
    for key, names in GAME_META.items():
        games.append(
            {
                "key": key,
                "name": names[lang],
                "desc": names[f"desc_{lang}"],
                "play_url": url_for("interactive_story", lang=lang, game_key=key),
                "map_url": url_for("narrative_map", lang=lang, game_key=key),
            }
        )
    return render_template("hub_index.html", lang=lang, ui=LANG_UI[lang], games=games)


@app.route("/<lang>/<game_key>/interactive-story")
def interactive_story(lang: str, game_key: str):
    validate_lang_game(lang, game_key)
    if game_key == "fire_rescue":
        tpl = "interactive_story_elk.html"
        rendered = render_template(
            tpl,
            narrative_map_url=url_for("narrative_map", lang=lang, game_key=game_key),
        )
    else:
        tpl = "interactive_story_classic.html"
        rendered = render_template(tpl)
    return set_ctx_cookie(
        make_response(rendered),
        lang,
        game_key,
    )


@app.route("/<lang>/<game_key>/narrative-map-elk")
def narrative_map(lang: str, game_key: str):
    validate_lang_game(lang, game_key)
    template_name = "story_graph_visualization_elk.html" if game_key == "fire_rescue" else "story_graph_visualization_classic.html"
    rendered = render_template(
        template_name,
        interactive_story_url=url_for("interactive_story", lang=lang, game_key=game_key),
        story_graph_api_url=url_for("api_story_graph", lang=lang, game_key=game_key),
    )
    return set_ctx_cookie(make_response(rendered), lang, game_key)


@app.route("/interactive-story")
def interactive_story_global():
    lang, game_key = get_ctx_from_request()
    return redirect(url_for("interactive_story", lang=lang, game_key=game_key))


@app.route("/story-graph-visualization")
def map_classic_global():
    lang, game_key = get_ctx_from_request()
    return redirect(url_for("narrative_map", lang=lang, game_key=game_key))


@app.route("/narrative-map-elk")
def map_elk_global():
    lang, game_key = get_ctx_from_request()
    return redirect(url_for("narrative_map", lang=lang, game_key=game_key))


@app.route("/api/story-graph")
def api_story_graph_global():
    lang, game_key = get_ctx_from_request()
    return api_story_graph(lang, game_key)


@app.route("/api/story-graph/<lang>/<game_key>")
def api_story_graph(lang: str, game_key: str):
    validate_lang_game(lang, game_key)
    graph_path = GAME_CONFIG[game_key]["json"][lang]
    if not graph_path.exists():
        return jsonify({"nodes": [], "edges": {}, "start_node_id": "", "ending_node_ids": [], "legend": [], "stats": {}})
    try:
        with open(graph_path, "r", encoding="utf-8") as f:
            story_graph = json.load(f)
        return jsonify(build_processed_graph(story_graph, lang, game_key))
    except Exception as exc:
        return jsonify({"error": "Failed to load story graph", "message": str(exc)}), 500


@app.route("/assets/<lang>/<game_key>/<path:filename>")
def serve_game_image(lang: str, game_key: str, filename: str):
    validate_lang_game(lang, game_key)
    resolved = resolve_image_file(game_key, filename)
    if not resolved:
        return "Image not found", 404
    return send_from_directory(resolved.parent, resolved.name)


@app.route("/assets_thumb/<lang>/<game_key>/<path:filename>")
def serve_game_thumbnail(lang: str, game_key: str, filename: str):
    validate_lang_game(lang, game_key)
    resolved = resolve_image_file(game_key, filename)
    if not resolved:
        return "Image not found", 404
    width = 320
    quality = 58
    try:
        cache_key = f"{lang}_{game_key}_{Path(filename).stem}"
        thumb = build_thumbnail_file(resolved, cache_key, width, quality)
        return send_file(thumb, mimetype="image/jpeg", max_age=3600)
    except Exception:
        return send_file(resolved, max_age=3600)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Bilingual game hub server")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=5004)
    args = parser.parse_args()
    app.run(debug=args.debug, host=args.host, port=args.port)


if __name__ == "__main__":
    main()

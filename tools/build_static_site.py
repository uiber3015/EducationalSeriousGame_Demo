from __future__ import annotations

import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = ROOT / "bilingual_hub" / "templates"
STORY_GRAPH_DIR = ROOT / "static" / "story_graph"

SITE_PATH_HELPERS = """
function getSiteBase() {
    const parts = location.pathname.split('/').filter(Boolean);
    while (parts.length) {
        const last = parts[parts.length - 1];
        if (last === 'zh' || last === 'en' || last.endsWith('.html')) {
            parts.pop();
            continue;
        }
        break;
    }
    return parts.length ? '/' + parts.join('/') + '/' : '/';
}

function sitePath(relativePath) {
    const clean = String(relativePath || '').replace(/^\\/+/, '');
    return getSiteBase() + clean;
}
"""

LANG_UI = {
    "zh": {"title": "教育游戏", "subtitle": "选择一个互动故事，开始体验或查看叙事流程图。", "play": "进入游戏", "map": "查看地图"},
    "en": {"title": "Educational Games", "subtitle": "Choose an interactive story to play or inspect its narrative map.", "play": "Play", "map": "Narrative Map"},
}

GAMES = {
    "tech_education": {
        "zh": "科技教育",
        "en": "Tech Education",
        "desc_zh": "科学实践中的观察、判断与安全选择。",
        "desc_en": "Observation, judgment, and safe choices in science practice.",
        "json": {
            "zh": ROOT / "bilingual_versions" / "tech_education" / "story_graph_zh.json",
            "en": ROOT / "bilingual_versions" / "tech_education" / "story_graph_en.json",
        },
        "image_dir": "cot_20260424_131513/output_images",
        "map": "classic",
    },
    "spring_outing": {
        "zh": "春游历险",
        "en": "Spring Outing Adventure",
        "desc_zh": "在户外探索中做出正确的风险判断。",
        "desc_en": "Make risk-aware decisions during an outdoor adventure.",
        "json": {
            "zh": ROOT / "bilingual_versions" / "spring_outing" / "story_graph_zh.json",
            "en": ROOT / "bilingual_versions" / "spring_outing" / "story_graph_en.json",
        },
        "image_dir": "cot_20260424_123248/output_images",
        "map": "classic",
    },
    "moving_house": {
        "zh": "搬家风波",
        "en": "Moving Day Chaos",
        "desc_zh": "用科学方法解决搬家过程中的麻烦。",
        "desc_en": "Use scientific thinking to solve moving-day problems.",
        "json": {
            "zh": ROOT / "bilingual_versions" / "moving_house" / "story_graph_zh.json",
            "en": ROOT / "bilingual_versions" / "moving_house" / "story_graph_en.json",
        },
        "image_dir": "cot_20260425_111838/output_images",
        "map": "classic",
    },
    "fire_rescue": {
        "zh": "火灾救援",
        "en": "Fire Rescue",
        "desc_zh": "高层火灾中的紧急避险与求生决策。",
        "desc_en": "Emergency survival choices during a high-rise fire.",
        "json": {
            "zh": ROOT / "demo_elk" / "output" / "fire_core_for_edu_new" / "output" / "story_graph_storyline_elk.json",
            "en": ROOT / "demo_elk" / "output" / "fire_core_for_edu_new" / "output" / "story_graph_storyline_elk.json",
        },
        "image_dir": "demo_elk/output/fire_core_for_edu_new/output_images",
        "map": "elk",
    },
}

ROLE_STYLES = {
    "prologue": {"key": "prologue", "label": "Prologue", "color": "#8b5cf6"},
    "decision": {"key": "decision", "label": "Decision", "color": "#3b82f6"},
    "normal": {"key": "normal", "label": "Regular Event", "color": "#22c55e"},
    "success_end": {"key": "ending", "label": "Success End", "color": "#f97316"},
    "failure_end": {"key": "fatal", "label": "Failure End", "color": "#334155"},
}


def node_type_info(node: dict, start_node_id: str, outgoing_count: int) -> dict:
    metadata = node.get("metadata", {}) or {}
    display_role = (metadata.get("display_role") or "").strip()
    node_id = node.get("id")
    node_type = (node.get("type") or "unknown").strip() or "unknown"
    if display_role in ROLE_STYLES:
        return ROLE_STYLES[display_role]
    if node_id == "node_1" or node_id == start_node_id:
        return ROLE_STYLES["prologue"]
    if outgoing_count == 0:
        return ROLE_STYLES["failure_end"]
    if outgoing_count >= 2 or node_type == "decision":
        return ROLE_STYLES["decision"]
    return ROLE_STYLES["normal"]


def collect_neighbors(node_id: str, edges: dict, jump_edges: list[dict]) -> tuple[list[dict], list[dict]]:
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


def processed_graph(story_graph: dict, game_key: str) -> dict:
    game = GAMES[game_key]
    raw_nodes = story_graph.get("nodes", []) or []
    edges = dict(story_graph.get("edges", {}) or {})
    start_node_id = story_graph.get("start_node_id") or (raw_nodes[0].get("id") if raw_nodes else "")
    incoming_map: dict[str, list[str]] = {}
    for source_id, targets in edges.items():
        for target_id in targets or []:
            incoming_map.setdefault(target_id, []).append(source_id)

    nodes, legend_map, image_count, ending_count = [], {}, 0, 0
    for node in raw_nodes:
        metadata = dict(node.get("metadata", {}) or {})
        outgoing = edges.get(node.get("id"), []) or []
        image_path_raw = metadata.get("image_path") or metadata.get("image_url")
        image_url = None
        if image_path_raw:
            filename = os.path.basename(str(image_path_raw).replace("\\", "/"))
            if filename:
                image_url = f"{game['image_dir']}/{filename}"
                metadata["image_path"] = image_url
                metadata["image_url"] = image_url
                image_count += 1

        type_info = node_type_info(node, start_node_id, len(outgoing))
        legend_map[type_info["key"]] = {"key": type_info["key"], "label": type_info["label"], "color": type_info["color"]}
        incoming = incoming_map.get(node.get("id"), []) or []
        content = str(node.get("content", "") or "")
        processed = {
            "id": node.get("id"),
            "type": metadata.get("display_role") or node.get("type", "unknown"),
            "display_type": type_info["label"],
            "display_type_key": type_info["key"],
            "type_color": type_info["color"],
            "content": content,
            "preview": content.strip().replace("\n", " ")[:88],
            "image_url": image_url,
            "thumbnail_url": image_url,
            "metadata": metadata,
            "incoming_count": len(incoming),
            "outgoing_count": len(outgoing),
            "detail_fields": [
                {"label": "Node ID", "value": node.get("id", "-")},
                {"label": "Node Type", "value": type_info["label"]},
                {"label": "Incoming", "value": str(len(incoming))},
                {"label": "Outgoing", "value": str(len(outgoing))},
            ],
            "is_ending": type_info["key"] in {"ending", "fatal"},
        }
        if processed["is_ending"]:
            ending_count += 1
        nodes.append(processed)

    for node in nodes:
        edges.setdefault(node["id"], [])

    jump_edges = []
    for item in (story_graph.get("metadata", {}) or {}).get("jump_edges", []) or []:
        source_id = item.get("from")
        target_id = item.get("to")
        if source_id and target_id:
            jump_edges.append({"source": source_id, "target": target_id, "label": item.get("label", "")})

    for node in nodes:
        incoming_nodes, outgoing_nodes = collect_neighbors(node["id"], edges, jump_edges)
        node["incoming_nodes"] = incoming_nodes
        node["outgoing_nodes"] = outgoing_nodes

    metadata = story_graph.get("metadata", {}) or {}
    layout_hints = metadata.get("layout_hints", {}) or {}
    return {
        "nodes": nodes,
        "edges": edges,
        "start_node_id": start_node_id or (nodes[0]["id"] if nodes else ""),
        "ending_node_ids": [node["id"] for node in nodes if node["is_ending"]],
        "jump_edges": jump_edges,
        "layout_hints": layout_hints,
        "metadata": metadata,
        "legend": list(legend_map.values()),
        "stats": {
            "node_count": len(nodes),
            "edge_count": sum(len(targets or []) for targets in edges.values()),
            "ending_count": ending_count,
            "image_count": image_count,
            "jump_edge_count": len(jump_edges),
            "layout_mode": layout_hints.get("layout_mode", "elk_layered"),
            "layout_version": layout_hints.get("layout_version", ""),
        },
    }


def build_graph_json() -> None:
    STORY_GRAPH_DIR.mkdir(parents=True, exist_ok=True)
    for game_key, game in GAMES.items():
        for lang, json_path in game["json"].items():
            target_dir = STORY_GRAPH_DIR / lang
            target_dir.mkdir(parents=True, exist_ok=True)
            raw = json.loads(json_path.read_text(encoding="utf-8"))
            data = processed_graph(raw, game_key)
            (target_dir / f"{game_key}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def hub_html() -> str:
    games_payload = {
        key: {"zh": value["zh"], "en": value["en"], "desc_zh": value["desc_zh"], "desc_en": value["desc_en"], "map": value["map"]}
        for key, value in GAMES.items()
    }
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Educational Games</title>
  <style>
    :root {{ --bg:#f4f7fb; --card:rgba(255,255,255,.86); --border:rgba(148,163,184,.22); --text:#0f172a; --muted:#64748b; --teal:#0f766e; --indigo:#4f46e5; }}
    * {{ box-sizing: border-box; }}
    body {{ font-family:"Microsoft YaHei","Segoe UI",Arial,sans-serif; margin:0; min-height:100vh; color:var(--text); background:radial-gradient(circle at 10% 10%,rgba(20,184,166,.14),transparent 28%),radial-gradient(circle at 85% 15%,rgba(79,70,229,.14),transparent 24%),linear-gradient(135deg,#f8fafc 0%,var(--bg) 100%); }}
    .wrap {{ max-width:1060px; margin:0 auto; padding:54px 24px 72px; }}
    .top {{ display:flex; justify-content:space-between; align-items:flex-end; gap:20px; margin-bottom:28px; }}
    h1 {{ margin:0; font-size:44px; line-height:1.08; letter-spacing:-.04em; }}
    .subtitle {{ margin-top:10px; color:var(--muted); font-size:15px; }}
    .lang {{ display:inline-flex; gap:8px; padding:6px; border-radius:999px; background:rgba(255,255,255,.72); border:1px solid var(--border); box-shadow:0 10px 25px rgba(15,23,42,.06); }}
    .lang button {{ color:#334155; border:0; background:transparent; cursor:pointer; font-weight:800; font-size:13px; padding:8px 12px; border-radius:999px; }}
    .lang button.active {{ background:#0f172a; color:#fff; }}
    .grid {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:18px; }}
    .card {{ position:relative; overflow:hidden; min-height:160px; padding:22px; border-radius:24px; background:var(--card); border:1px solid var(--border); box-shadow:0 18px 42px rgba(15,23,42,.08); backdrop-filter:blur(12px); }}
    .card::after {{ content:""; position:absolute; right:-42px; bottom:-42px; width:130px; height:130px; border-radius:50%; background:linear-gradient(135deg,rgba(20,184,166,.18),rgba(79,70,229,.16)); }}
    .name,.desc,.actions {{ position:relative; z-index:1; }}
    .name {{ font-size:23px; font-weight:900; margin-bottom:12px; }}
    .desc {{ color:var(--muted); font-size:13px; margin-bottom:22px; }}
    .actions {{ display:flex; flex-wrap:wrap; gap:10px; }}
    .actions a {{ display:inline-flex; align-items:center; justify-content:center; min-width:92px; padding:10px 14px; border-radius:999px; text-decoration:none; font-size:13px; font-weight:900; color:#fff; box-shadow:0 10px 22px rgba(15,23,42,.14); }}
    .play {{ background:linear-gradient(135deg,var(--teal),#06b6d4); }}
    .map {{ background:linear-gradient(135deg,var(--indigo),#7c3aed); }}
    @media (max-width:760px) {{ .top{{align-items:flex-start;flex-direction:column;}} .grid{{grid-template-columns:1fr;}} h1{{font-size:36px;}} }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="top">
      <div><h1 id="title"></h1><div id="subtitle" class="subtitle"></div></div>
      <div class="lang"><button id="zh-btn">中文</button><button id="en-btn">English</button></div>
    </div>
    <div id="game-grid" class="grid"></div>
  </div>
  <script>
    {SITE_PATH_HELPERS}
    const games = {json.dumps(games_payload, ensure_ascii=False)};
    const ui = {json.dumps(LANG_UI, ensure_ascii=False)};
    const pathLang = location.pathname.split('/').filter(Boolean).find(part => part === 'zh' || part === 'en');
    let lang = pathLang || (localStorage.getItem('hub_lang') || 'zh');
    function renderHub() {{
      localStorage.setItem('hub_lang', lang);
      document.documentElement.lang = lang === 'zh' ? 'zh-CN' : 'en';
      document.title = ui[lang].title;
      document.getElementById('title').textContent = ui[lang].title;
      document.getElementById('subtitle').textContent = ui[lang].subtitle;
      document.getElementById('zh-btn').classList.toggle('active', lang === 'zh');
      document.getElementById('en-btn').classList.toggle('active', lang === 'en');
      document.getElementById('game-grid').innerHTML = Object.entries(games).map(([key, game]) => {{
        const mapPage = game.map === 'elk' ? 'narrative-map-elk.html' : 'narrative-map-classic.html';
        return `<div class="card"><div class="name">${{game[lang]}}</div><div class="desc">${{game['desc_' + lang]}}</div><div class="actions"><a class="play" href="${{sitePath('interactive-story.html')}}?lang=${{lang}}&game=${{key}}">${{ui[lang].play}}</a><a class="map" href="${{sitePath(mapPage)}}?lang=${{lang}}&game=${{key}}">${{ui[lang].map}}</a></div></div>`;
      }}).join('');
    }}
    document.getElementById('zh-btn').onclick = () => {{ lang = 'zh'; renderHub(); }};
    document.getElementById('en-btn').onclick = () => {{ lang = 'en'; renderHub(); }};
    renderHub();
  </script>
</body>
</html>
"""


def build_hub_pages() -> None:
    html = hub_html()
    (ROOT / "index.html").write_text(html, encoding="utf-8")
    for lang in ("zh", "en"):
        lang_dir = ROOT / lang
        lang_dir.mkdir(exist_ok=True)
        (lang_dir / "index.html").write_text(html, encoding="utf-8")


def build_interactive_page() -> None:
    html = (TEMPLATE_DIR / "interactive_story_classic.html").read_text(encoding="utf-8")
    html = html.replace("localKaTeX.src = '/static/katex/katex.min.js';", "localKaTeX.src = 'static/katex/katex.min.js';")
    html = html.replace("localAutoRender.src = '/static/katex/auto-render.min.js';", "localAutoRender.src = 'static/katex/auto-render.min.js';")
    html = html.replace("localCSS.href = '/static/katex/katex.min.css';", "localCSS.href = 'static/katex/katex.min.css';")
    html = html.replace(
        "        .graph-button:hover {\n"
        "            background-color: rgba(11, 218, 90, 0.9);\n"
        "            transform: scale(1.05);\n"
        "        }\n",
        "        .graph-button {\n"
        "            width: 158px;\n"
        "            min-width: 158px;\n"
        "            box-sizing: border-box;\n"
        "            text-align: center;\n"
        "            justify-content: center;\n"
        "        }\n"
        "\n"
        "        .graph-button:hover {\n"
        "            background-color: rgba(11, 218, 90, 0.9);\n"
        "            transform: scale(1.05);\n"
        "        }\n"
        "\n"
        "        .next-page-button {\n"
        "            position: absolute;\n"
        "            top: 50%;\n"
        "            right: 28px;\n"
        "            transform: translateY(-50%);\n"
        "            width: 58px;\n"
        "            height: 58px;\n"
        "            background: radial-gradient(circle at 32% 24%, rgba(255, 255, 255, 0.34), transparent 34%), linear-gradient(135deg, rgba(14, 165, 233, 0.96), rgba(37, 99, 235, 0.96));\n"
        "            border: 1px solid rgba(255, 255, 255, 0.68);\n"
        "            color: white;\n"
        "            padding: 0;\n"
        "            font-size: 0;\n"
        "            font-weight: 700;\n"
        "            cursor: pointer;\n"
        "            border-radius: 50%;\n"
        "            display: block;\n"
        "            z-index: 120;\n"
        "            box-shadow: 0 18px 34px rgba(15, 23, 42, 0.36), inset 0 1px 0 rgba(255, 255, 255, 0.28);\n"
        "            line-height: 1;\n"
        "            transition: transform 0.22s ease, box-shadow 0.22s ease, filter 0.22s ease;\n"
        "        }\n"
        "\n"
        "        .next-page-button::before {\n"
        "            content: \"\";\n"
        "            position: absolute;\n"
        "            left: 16px;\n"
        "            top: 50%;\n"
        "            width: 28px;\n"
        "            height: 24px;\n"
        "            border-radius: 999px;\n"
        "            background: currentColor;\n"
        "            clip-path: polygon(0 36%, 55% 36%, 55% 14%, 100% 50%, 55% 86%, 55% 64%, 0 64%);\n"
        "            transform: translateY(-50%);\n"
        "        }\n"
        "\n"
        "        .next-page-button::after {\n"
        "            content: \"\";\n"
        "            position: absolute;\n"
        "            inset: 9px;\n"
        "            border-radius: 50%;\n"
        "            border: 1px solid rgba(255, 255, 255, 0.18);\n"
        "            pointer-events: none;\n"
        "        }\n"
        "\n"
        "        .next-page-button:hover {\n"
        "            transform: translateY(-50%) scale(1.08);\n"
        "            filter: brightness(1.06);\n"
        "            box-shadow: 0 22px 40px rgba(15, 23, 42, 0.42), inset 0 1px 0 rgba(255, 255, 255, 0.34);\n"
        "        }\n",
    )
    bootstrap = (
        SITE_PATH_HELPERS
        + """
            const staticParams = new URLSearchParams(window.location.search);
            const staticLang = ['zh', 'en'].includes(staticParams.get('lang')) ? staticParams.get('lang') : (localStorage.getItem('hub_lang') || 'zh');
            const staticGame = staticParams.get('game') || localStorage.getItem('hub_game') || 'tech_education';
            localStorage.setItem('hub_lang', staticLang);
            localStorage.setItem('hub_game', staticGame);
            const graphDataUrl = sitePath(`static/story_graph/${staticLang}/${staticGame}.json`);
            const mapPage = staticGame === 'fire_rescue' ? 'narrative-map-elk.html' : 'narrative-map-classic.html';
            const narrativeMapUrl = `${sitePath(mapPage)}?lang=${encodeURIComponent(staticLang)}&game=${encodeURIComponent(staticGame)}`;
            function resolveAssetUrl(url) {
                if (!url) return url;
                if (/^(https?:|data:)/i.test(url)) return url;
                return sitePath(String(url).replace(/^\\/+/, ''));
            }
            function staticLoadErrorMessage() {
                if (location.protocol === 'file:') {
                    return '请用本地 HTTP 服务打开，不要直接双击 HTML。在 On_use 目录运行: python -m http.server 8765';
                }
                return `无法加载数据: ${graphDataUrl}`;
            }
"""
    )
    html = html.replace(
        "        <div id=\"loading\" class=\"loading\">Loading...</div>",
        "        <div id=\"loading\" class=\"loading\">Loading...</div>\n"
        "        <button id=\"next-page-button\" class=\"next-page-button\" aria-label=\"Continue\">&#8594;</button>",
    )
    html = html.replace("            let storyGraph = null;\n            let currentNodeId = null;", "            let storyGraph = null;\n            let currentNodeId = null;\n            let pendingNextNodeId = null;\n            let autoNextTimer = null;\n" + bootstrap)
    html = html.replace(
        "            const loadingEl = document.getElementById('loading');",
        "            const loadingEl = document.getElementById('loading');\n"
        "            const nextPageButtonEl = document.getElementById('next-page-button');",
    )
    html = html.replace(
        "                restartButtonEl.style.display = 'none';",
        "                restartButtonEl.style.display = 'none';\n"
        "                nextPageButtonEl.style.display = 'none';\n"
        "                pendingNextNodeId = null;\n"
        "                if (autoNextTimer) {\n"
        "                    clearTimeout(autoNextTimer);\n"
        "                    autoNextTimer = null;\n"
        "                }",
    )
    html = html.replace("            fetch('/api/story-graph')", "            fetch(graphDataUrl)")
    html = html.replace(
        "loadingEl.textContent = 'Failed to load story data. Please check whether the server is running.';",
        "loadingEl.textContent = staticLoadErrorMessage();",
    )
    html = html.replace(
        "loadingEl.textContent = 'Failed to load story data. Please check the static JSON file path.';",
        "loadingEl.textContent = staticLoadErrorMessage();",
    )
    html = html.replace("storyImageEl.src = fullImagePath;", "storyImageEl.src = resolveAssetUrl(fullImagePath);")
    html = html.replace("                        }, 6000); // 6秒后开始显示", "                        }, 4000); // 4秒后开始显示")
    html = html.replace(
        "                                setTimeout(() => {\n"
        "                                    currentNodeId = nextNodeIds[0];\n"
        "                                    displayNode(currentNodeId);\n"
        "                                }, 3000); // 延迟3秒跳转，让用户有时间阅读过渡情节内容",
        "                                pendingNextNodeId = nextNodeIds[0];\n"
        "                                nextPageButtonEl.innerHTML = '&#8594;';\n"
        "                                nextPageButtonEl.style.display = 'block';\n"
        "                                if (autoNextTimer) {\n"
        "                                    clearTimeout(autoNextTimer);\n"
        "                                }\n"
        "                                autoNextTimer = setTimeout(() => {\n"
        "                                    if (pendingNextNodeId === nextNodeIds[0]) {\n"
        "                                        currentNodeId = nextNodeIds[0];\n"
        "                                        pendingNextNodeId = null;\n"
        "                                        autoNextTimer = null;\n"
        "                                        displayNode(currentNodeId);\n"
        "                                    }\n"
        "                                }, 8000); // 延迟8秒自动进入下一页，期间可点击箭头立即跳转",
    )
    html = html.replace("                                }, 6000);", "                                }, 4000);")
    html = html.replace("                            }, 6000);", "                            }, 4000);")
    html = html.replace(
        "                            // ep_end节点不自动继续，等待用户点击物理知识点覆盖层的继续按钮（简化版本）\n"
        "                            physicsKnowledgeCloseBtnEl.textContent = 'Continue';",
        "                            // ep_end节点不自动继续，等待用户点击物理知识点覆盖层的继续按钮（简化版本）\n"
        "                            nextPageButtonEl.style.display = 'none';\n"
        "                            physicsKnowledgeCloseBtnEl.textContent = 'Continue';",
    )
    html = html.replace(
        "                            } else if (nextNodeIds.length > 1) {\n"
        "                                // 有多个连接边，显示选择按钮\n"
        "                                setTimeout(() => {",
        "                            } else if (nextNodeIds.length > 1) {\n"
        "                                // 有多个连接边，显示选择按钮\n"
        "                                nextPageButtonEl.style.display = 'none';\n"
        "                                setTimeout(() => {",
    )
    html = html.replace(
        "            // 重新开始按钮点击事件\n"
        "            restartButtonEl.addEventListener('click', startStory);",
        "            // 重新开始按钮点击事件\n"
        "            restartButtonEl.addEventListener('click', startStory);\n"
        "\n"
        "            // 等待 6 秒后由用户手动进入下一页\n"
        "            nextPageButtonEl.addEventListener('click', () => {\n"
        "                const nextNodeIds = (storyGraph && storyGraph.edges && storyGraph.edges[currentNodeId]) || [];\n"
        "                const targetNodeId = pendingNextNodeId || (nextNodeIds.length === 1 ? nextNodeIds[0] : null);\n"
        "                if (!targetNodeId) return;\n"
        "                if (autoNextTimer) {\n"
        "                    clearTimeout(autoNextTimer);\n"
        "                    autoNextTimer = null;\n"
        "                }\n"
        "                currentNodeId = targetNodeId;\n"
        "                pendingNextNodeId = null;\n"
        "                displayNode(currentNodeId);\n"
        "            });",
    )
    html = html.replace(
        "            // 跳转到故事图（旧版：/story-graph-visualization；v2：/narrative-map-v2，由服务端注入）\n"
        "            document.getElementById('goto-graph').addEventListener('click', () => {\n"
        "                window.location.href = {{ narrative_map_url | default('/story-graph-visualization') | tojson }};\n"
        "            });",
        "            // 跳转到当前游戏的静态叙事地图\n"
        "            document.getElementById('goto-graph').addEventListener('click', () => {\n"
        "                window.location.href = narrativeMapUrl;\n"
        "            });",
    )
    html = html.replace(
        "        .graph-button {\n"
        "            position: absolute;\n"
        "            top: 22px;\n"
        "            right: 18px;\n"
        "            background-color: rgba(9, 132, 83, 0.8);\n"
        "            border: 2px solid #067638;\n"
        "            color: white;\n"
        "            padding: 8px 20px;\n",
        "        .graph-button {\n"
        "            position: absolute;\n"
        "            top: 22px;\n"
        "            right: 18px;\n"
        "            background-color: rgba(9, 132, 83, 0.8);\n"
        "            border: 2px solid #067638;\n"
        "            color: white;\n"
        "            padding: 8px 12px;\n",
    )
    (ROOT / "interactive-story.html").write_text(html, encoding="utf-8")


def build_map_pages() -> None:
    bootstrap = (
        SITE_PATH_HELPERS
        + """
        const staticParams = new URLSearchParams(window.location.search);
        const staticLang = ['zh', 'en'].includes(staticParams.get('lang')) ? staticParams.get('lang') : (localStorage.getItem('hub_lang') || 'zh');
        const staticGame = staticParams.get('game') || localStorage.getItem('hub_game') || 'tech_education';
        localStorage.setItem('hub_lang', staticLang);
        localStorage.setItem('hub_game', staticGame);
        const graphDataUrl = sitePath(`static/story_graph/${staticLang}/${staticGame}.json`);
        const interactiveStoryUrl = `${sitePath('interactive-story.html')}?lang=${encodeURIComponent(staticLang)}&game=${encodeURIComponent(staticGame)}`;
        function staticMapErrorMessage() {
            if (location.protocol === 'file:') {
                return '请用本地 HTTP 服务打开，不要直接双击 HTML。在 On_use 目录运行: python -m http.server 8765';
            }
            return `无法加载数据: ${graphDataUrl}`;
        }
"""
    )
    classic = (TEMPLATE_DIR / "story_graph_visualization_classic.html").read_text(encoding="utf-8")
    classic = classic.replace(
        "        .node-detail-card.single-pane .detail-scroll-box.plot-box {\n"
        "            min-height: 176px;\n"
        "            max-height: 240px;\n"
        "        }\n",
        "        .node-detail-card.single-pane .detail-scroll-box.plot-box {\n"
        "            min-height: 176px;\n"
        "            max-height: 240px;\n"
        "        }\n"
        "        .node-detail-card.decision-compact .detail-scroll-box.plot-box {\n"
        "            min-height: 96px;\n"
        "            max-height: 150px;\n"
        "        }\n"
        "        .node-detail-card.has-decision-options .detail-scroll-box.plot-box,\n"
        "        .node-detail-card.has-decision-options #detail-secondary {\n"
        "            min-height: 92px;\n"
        "            max-height: 150px;\n"
        "        }\n",
    )
    classic = classic.replace("        const state = {", bootstrap + "\n        const state = {")
    classic = classic.replace(
        "        function getDecisionOptions(node) {\n"
        "            const sourceNodeId = getSourceNodeId(node.id);\n"
        "            const parentIds = state.parentMap.get(sourceNodeId) || [];\n"
        "            for (const parentId of parentIds) {\n"
        "                const siblingIds = state.childrenMap.get(parentId) || [];\n"
        "                const options = siblingIds\n"
        "                    .map(childId => state.nodeMap.get(childId))\n"
        "                    .filter(child => child && child.type === 'decision')\n"
        "                    .map((child, index) => `${index + 1}. ${cleanDisplayText(child.metadata?.choice_option || child.content || child.id)}`);\n"
        "                if (options.length) return options.join('\\n\\n');\n"
        "            }\n"
        "            const ownOption = cleanDisplayText(node.metadata?.choice_option || '');\n"
        "            return ownOption ? `1. ${ownOption}` : '';\n"
        "        }\n",
        "        function getDecisionOptions(node) {\n"
        "            const sourceNodeId = getSourceNodeId(node.id);\n"
        "            const optionSourceIds = node.type === 'decision'\n"
        "                ? ((state.parentMap.get(sourceNodeId) || [])[0] ? state.childrenMap.get((state.parentMap.get(sourceNodeId) || [])[0]) : [])\n"
        "                : (state.childrenMap.get(sourceNodeId) || []);\n"
        "            const options = (optionSourceIds || [])\n"
        "                .map(childId => state.nodeMap.get(childId))\n"
        "                .filter(child => child && child.type === 'decision')\n"
        "                .map((child, index) => `${index + 1}. ${cleanDisplayText(child.metadata?.choice_option || child.content || child.id)}`);\n"
        "            if (options.length) return options.join('\\n\\n');\n"
        "            const ownOption = cleanDisplayText(node.metadata?.choice_option || '');\n"
        "            return ownOption ? `1. ${ownOption}` : '';\n"
        "        }\n"
        "\n"
        "        function getPlotText(node) {\n"
        "            return cleanDisplayText(node.content || '');\n"
        "        }\n",
    )
    classic = classic.replace("fetch('/api/story-graph')", "fetch(graphDataUrl)")
    classic = classic.replace("Please confirm that `/api/story-graph` returns valid node data.", "Please confirm that the static story graph JSON file exists.")
    classic = classic.replace("Please confirm the server is running and `/api/story-graph` returns valid data.", "Please confirm the static story graph JSON file exists.")
    classic = classic.replace(
        "emptyState.innerHTML = '<strong>Failed to load story map</strong><span>Please confirm the static story graph JSON file exists.</span>';",
        "emptyState.innerHTML = `<strong>Failed to load story map</strong><span>${staticMapErrorMessage()}</span>`;",
    )
    classic = classic.replace("window.location.href = '/interactive-story';", "window.location.href = interactiveStoryUrl;")
    classic = classic.replace(
        "            setScrollBoxContent(detailPlot, cleanDisplayText(node.content || ''), 'No plot details available.');",
        "            const nodeDetailCard = document.querySelector('.node-detail-card');\n"
        "            nodeDetailCard.classList.remove('single-pane', 'decision-compact', 'has-decision-options');\n"
        "            setScrollBoxContent(detailPlot, getPlotText(node), 'No plot details available.');",
    )
    classic = classic.replace(
        "            if (node.type === 'decision') {\n"
        "                detailSecondaryTitle.textContent = 'Decision';\n"
        "                setScrollBoxContent(detailSecondary, getDecisionOptions(node), 'No decision options available.');\n"
        "                detailSecondarySection.classList.remove('hidden');\n"
        "                detailPlot.classList.remove('large');\n"
        "                detailImage.classList.remove('hidden');\n"
        "                detailBadge.classList.remove('hidden');\n"
        "                document.querySelector('.node-detail-card').classList.remove('single-pane');\n"
        "            } else if (node.type === 'ep_end' || node.type === 'fatal') {",
        "            const decisionOptions = node.type === 'decision' ? '' : getDecisionOptions(node);\n"
        "\n"
        "            if (node.type === 'ep_end' || node.type === 'fatal') {",
    )
    classic = classic.replace(
        "                document.querySelector('.node-detail-card').classList.remove('single-pane');",
        "                nodeDetailCard.classList.remove('single-pane');",
    )
    classic = classic.replace(
        "                document.querySelector('.node-detail-card').classList.add('single-pane');",
        "                if (node.type === 'decision') {\n"
        "                    detailSecondarySection.classList.add('hidden');\n"
        "                    detailPlot.classList.remove('large');\n"
        "                    nodeDetailCard.classList.add('decision-compact');\n"
        "                } else if (decisionOptions) {\n"
        "                    detailSecondaryTitle.textContent = 'Decision';\n"
        "                    setScrollBoxContent(detailSecondary, decisionOptions, 'No decision options available.');\n"
        "                    detailSecondarySection.classList.remove('hidden');\n"
        "                    detailPlot.classList.remove('large');\n"
        "                    nodeDetailCard.classList.add('has-decision-options');\n"
        "                } else {\n"
        "                    detailSecondarySection.classList.add('hidden');\n"
        "                    detailPlot.classList.add('large');\n"
        "                    nodeDetailCard.classList.add('single-pane');\n"
        "                }",
    )
    (ROOT / "narrative-map-classic.html").write_text(classic, encoding="utf-8")

    elk = (TEMPLATE_DIR / "story_graph_visualization_elk.html").read_text(encoding="utf-8")
    elk = elk.replace("        const graphContainer = document.getElementById('graph-container');", bootstrap + "\n        const graphContainer = document.getElementById('graph-container');")
    elk = elk.replace("fetch(`/api/story-graph?_=${Date.now()}`)", "fetch(`${graphDataUrl}?_=${Date.now()}`)")
    elk = elk.replace("Please confirm that `/api/story-graph` returns valid node data.", "Please confirm that the static story graph JSON file exists.")
    elk = elk.replace(
        "emptyState.innerHTML = `<strong>Failed to load story map</strong><span>${error.message}</span>`;",
        "emptyState.innerHTML = `<strong>Failed to load story map</strong><span>${staticMapErrorMessage()}</span>`;",
    )
    elk = elk.replace("window.location.href = '/interactive-story';", "window.location.href = interactiveStoryUrl;")
    (ROOT / "narrative-map-elk.html").write_text(elk, encoding="utf-8")


def main() -> None:
    build_graph_json()
    build_hub_pages()
    build_interactive_page()
    build_map_pages()
    print("Static site generated.")


if __name__ == "__main__":
    main()

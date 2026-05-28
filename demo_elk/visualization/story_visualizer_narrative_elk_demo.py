"""Narrative Map 可视化（ELK Layered 版）。硬编码/Dagre 版见 story_visualizer_narrative_v2.py。"""
from flask import Flask, render_template, jsonify, send_from_directory, request, send_file
import json
import os

from PIL import Image, ImageOps

current_dir = os.path.dirname(os.path.abspath(__file__))
# Standalone demo bundle root: .../On_use/demo_elk
project_root = os.path.dirname(current_dir)

template_dir = os.path.join(current_dir, 'templates')
thumbnail_cache_dir = os.path.join(current_dir, '.thumbnail_cache')
app = Flask(
    __name__,
    static_folder=os.path.join(project_root, 'output'),
    template_folder=template_dir,
)

story_graph_path = None

DEFAULT_ELK_STORY_GRAPH = os.path.join(
    'output',
    'fire_core_for_edu_new',
    'output',
    'story_graph_storyline_elk.json',
)


def get_story_graph_absolute_path():
    global story_graph_path
    if not story_graph_path:
        return None
    if os.path.isabs(story_graph_path):
        return story_graph_path
    return os.path.abspath(os.path.join(project_root, story_graph_path))


def get_candidate_output_images_dirs():
    candidate_dirs = []
    graph_abs_path = get_story_graph_absolute_path()
    if graph_abs_path:
        graph_dir = os.path.dirname(graph_abs_path)
        graph_parent_dir = os.path.dirname(graph_dir)
        for candidate_dir in [
            os.path.join(graph_dir, 'output_images'),
            os.path.join(graph_parent_dir, 'output_images'),
        ]:
            if os.path.isdir(candidate_dir) and candidate_dir not in candidate_dirs:
                candidate_dirs.append(candidate_dir)

    output_root = os.path.join(project_root, 'output')
    if os.path.isdir(output_root):
        for subdir in os.listdir(output_root):
            output_images_path = os.path.join(output_root, subdir, 'output_images')
            if os.path.isdir(output_images_path) and output_images_path not in candidate_dirs:
                candidate_dirs.append(output_images_path)
    return candidate_dirs


def normalize_image_path(raw_path: str | None) -> str | None:
    if not raw_path:
        return None
    filename = os.path.basename(str(raw_path).replace('\\', '/'))
    return f'/output_images/{filename}' if filename else None


def build_thumbnail_url(image_path: str | None, width: int = 320, quality: int = 58) -> str | None:
    if not image_path:
        return None
    filename = os.path.basename(str(image_path).replace('\\', '/'))
    if not filename:
        return None
    return f'/output_images_thumb/{filename}?w={width}&q={quality}'


def resolve_output_image_file(filename: str) -> str | None:
    for output_images_path in get_candidate_output_images_dirs():
        candidate_file = os.path.join(output_images_path, filename)
        if os.path.exists(candidate_file):
            return candidate_file
    return None


def build_thumbnail_file(source_file: str, filename: str, width: int, quality: int) -> str:
    os.makedirs(thumbnail_cache_dir, exist_ok=True)
    safe_name = f'{width}_{quality}_{os.path.splitext(filename)[0]}.jpg'
    cached_file = os.path.join(thumbnail_cache_dir, safe_name)
    source_mtime = os.path.getmtime(source_file)
    if os.path.exists(cached_file) and os.path.getmtime(cached_file) >= source_mtime:
        return cached_file

    with Image.open(source_file) as image:
        image = ImageOps.exif_transpose(image)
        image = image.convert('RGB')
        target_height = max(1, round(width * 9 / 16))
        image.thumbnail((width, target_height * 2))
        image.save(cached_file, format='JPEG', quality=quality, optimize=True)
    return cached_file


MANUAL_PROLOGUE_NODE_ID = 'node_1'

MANUAL_SUCCESS_END_NODE_IDS = {
    'node_16',
    'generated_node_137',
    'generated_node_144',
    'generated_node_168',
    'generated_node_179',
    'generated_node_180',
    'ending_success_escape',
    'ending_success_rescued',
}


def get_node_type_info(node: dict, start_node_id: str, outgoing_count: int) -> dict:
    metadata = node.get('metadata', {}) or {}
    display_role = (metadata.get('display_role') or '').strip()
    node_id = node.get('id')
    node_type = (node.get('type') or 'unknown').strip() or 'unknown'

    role_styles = {
        'prologue': {'key': 'prologue', 'label': 'Prologue', 'color': '#8b5cf6'},
        'decision': {'key': 'decision', 'label': 'Decision', 'color': '#3b82f6'},
        'normal': {'key': 'normal', 'label': 'Regular Event', 'color': '#22c55e'},
        'success_end': {'key': 'ending', 'label': 'Success End', 'color': '#f97316'},
        'failure_end': {'key': 'fatal', 'label': 'Failure End', 'color': '#334155'},
    }
    if display_role in role_styles:
        return role_styles[display_role]

    if node_id == MANUAL_PROLOGUE_NODE_ID or node_id == start_node_id:
        return role_styles['prologue']
    if outgoing_count == 0:
        if node_id in MANUAL_SUCCESS_END_NODE_IDS or metadata.get('outcome_type') == 'success':
            return role_styles['success_end']
        return role_styles['failure_end']
    if outgoing_count >= 2 or node_type == 'decision':
        return role_styles['decision']
    return role_styles['normal']


def collect_detail_fields(
    node: dict,
    incoming_count: int,
    outgoing_count: int,
    display_type_label: str = '',
) -> list[dict]:
    return [
        {'label': 'Node ID', 'value': node.get('id', '-')},
        {'label': 'Node Type', 'value': display_type_label or node.get('type', '-')},
        {'label': 'Incoming', 'value': str(incoming_count)},
        {'label': 'Outgoing', 'value': str(outgoing_count)},
    ]


def collect_neighbor_nodes(
    node_id: str,
    edges: dict,
    jump_edges: list[dict],
) -> tuple[list[dict], list[dict]]:
    incoming: list[dict] = []
    outgoing: list[dict] = []
    seen_in: set[str] = set()
    seen_out: set[str] = set()

    for source_id, targets in (edges or {}).items():
        if node_id not in (targets or []):
            continue
        if source_id not in seen_in:
            seen_in.add(source_id)
            incoming.append({'id': source_id, 'jump': False})

    for target_id in edges.get(node_id, []) or []:
        if target_id not in seen_out:
            seen_out.add(target_id)
            outgoing.append({'id': target_id, 'jump': False})

    for item in jump_edges or []:
        source = item.get('source') or item.get('from')
        target = item.get('target') or item.get('to')
        if target == node_id and source and source not in seen_in:
            seen_in.add(source)
            incoming.append({'id': source, 'jump': True})
        if source == node_id and target and target not in seen_out:
            seen_out.add(target)
            outgoing.append({'id': target, 'jump': True})

    return incoming, outgoing


def build_processed_graph(story_graph: dict) -> dict:
    raw_nodes = story_graph.get('nodes', []) or []
    edges = story_graph.get('edges', {}) or {}
    start_node_id = story_graph.get('start_node_id') or (raw_nodes[0].get('id') if raw_nodes else '')
    incoming_map: dict[str, list[str]] = {}
    for source_id, targets in edges.items():
        for target_id in targets or []:
            incoming_map.setdefault(target_id, []).append(source_id)

    processed_nodes = []
    legend_map = {}
    image_count = 0
    ending_count = 0
    for node in raw_nodes:
        metadata = dict(node.get('metadata', {}) or {})
        outgoing = edges.get(node.get('id'), []) or []
        image_path = normalize_image_path(metadata.get('image_path'))
        image_url = image_path or normalize_image_path(metadata.get('image_url')) or metadata.get('image_url')
        if image_path:
            metadata['image_path'] = image_path
        if image_url:
            metadata['image_url'] = image_url
            image_count += 1
        type_info = get_node_type_info(node, start_node_id, len(outgoing))
        legend_map[type_info['key']] = {
            'key': type_info['key'],
            'label': type_info['label'],
            'color': type_info['color'],
        }
        incoming = incoming_map.get(node.get('id'), []) or []
        content = str(node.get('content', '') or '')
        preview = content.strip().replace('\n', ' ')
        metadata['display_type_key'] = type_info['key']
        processed_node = {
            'id': node.get('id'),
            'type': metadata.get('display_role') or node.get('type', 'unknown'),
            'display_type': type_info['label'],
            'display_type_key': type_info['key'],
            'type_color': type_info['color'],
            'content': content,
            'preview': preview[:88] + ('...' if len(preview) > 88 else ''),
            'image_url': image_url,
            'thumbnail_url': build_thumbnail_url(image_path),
            'metadata': metadata,
            'incoming_count': len(incoming),
            'outgoing_count': len(outgoing),
            'detail_fields': collect_detail_fields(
                node,
                len(incoming),
                len(outgoing),
                type_info['label'],
            ),
            'is_ending': type_info['key'] in {'ending', 'fatal'},
        }
        if processed_node['is_ending']:
            ending_count += 1
        processed_nodes.append(processed_node)

    for node in processed_nodes:
        edges.setdefault(node['id'], [])

    jump_edges = []
    for item in (story_graph.get('metadata', {}) or {}).get('jump_edges', []) or []:
        source_id = item.get('from')
        target_id = item.get('to')
        if source_id and target_id:
            jump_edges.append({
                'source': source_id,
                'target': target_id,
                'label': item.get('label', ''),
            })

    for node in processed_nodes:
        incoming_nodes, outgoing_nodes = collect_neighbor_nodes(
            node['id'],
            edges,
            jump_edges,
        )
        node['incoming_nodes'] = incoming_nodes
        node['outgoing_nodes'] = outgoing_nodes

    metadata = story_graph.get('metadata', {}) or {}
    layout_hints = metadata.get('layout_hints', {}) or {}

    return {
        'nodes': processed_nodes,
        'edges': edges,
        'start_node_id': start_node_id or (processed_nodes[0]['id'] if processed_nodes else ''),
        'ending_node_ids': [node['id'] for node in processed_nodes if node['is_ending']],
        'jump_edges': jump_edges,
        'layout_hints': layout_hints,
        'metadata': metadata,
        'legend': list(legend_map.values()),
        'stats': {
            'node_count': len(processed_nodes),
            'edge_count': sum(len(targets or []) for targets in edges.values()),
            'ending_count': ending_count,
            'image_count': image_count,
            'jump_edge_count': len(jump_edges),
            'layout_mode': layout_hints.get('layout_mode', 'elk_layered'),
            'layout_version': layout_hints.get('layout_version', ''),
        },
    }


@app.route('/')
def index():
    return render_template('interactive_story.html', narrative_map_url=NARRATIVE_MAP_URL_ELK)


@app.route('/narrative-map-elk')
def narrative_map_elk():
    return render_template('story_graph_visualization_elk.html')


@app.route('/narrative-map-v2')
def narrative_map_v2_link():
    # Keep legacy route available in standalone demo package.
    return render_template('story_graph_visualization_elk.html')


NARRATIVE_MAP_URL_ELK = '/narrative-map-elk'


@app.route('/interactive-story')
def interactive_story():
    return render_template('interactive_story.html', narrative_map_url=NARRATIVE_MAP_URL_ELK)


@app.route('/api/story-graph')
def get_story_graph():
    global story_graph_path
    if story_graph_path is None:
        story_graph_path = DEFAULT_ELK_STORY_GRAPH
        if not os.path.exists(os.path.join(project_root, story_graph_path)):
            story_graph_path = os.path.join(
                'output',
                'fire_core_for_edu_new',
                'output',
                'story_graph_storyline.json',
            )

    story_graph_abs_path = get_story_graph_absolute_path()
    if not story_graph_abs_path or not os.path.exists(story_graph_abs_path):
        return jsonify({'nodes': [], 'edges': {}, 'start_node_id': '', 'ending_node_ids': [], 'legend': [], 'stats': {}})

    try:
        with open(story_graph_abs_path, 'r', encoding='utf-8') as f:
            story_graph = json.load(f)
        return jsonify(build_processed_graph(story_graph))
    except Exception as exc:
        return jsonify({'error': 'Failed to load story graph', 'message': str(exc)}), 500


@app.route('/output_images/<path:filename>')
def serve_output_images(filename):
    resolved_file = resolve_output_image_file(filename)
    if resolved_file:
        return send_from_directory(os.path.dirname(resolved_file), os.path.basename(resolved_file))
    return 'Image not found', 404


@app.route('/output_images_thumb/<path:filename>')
def serve_output_image_thumbnail(filename):
    resolved_file = resolve_output_image_file(filename)
    if not resolved_file:
        return 'Image not found', 404

    width = request.args.get('w', default=320, type=int) or 320
    quality = request.args.get('q', default=58, type=int) or 58
    width = max(120, min(width, 640))
    quality = max(35, min(quality, 85))

    try:
        thumbnail_file = build_thumbnail_file(resolved_file, filename, width, quality)
        return send_file(thumbnail_file, mimetype='image/jpeg', max_age=3600)
    except Exception:
        return send_file(resolved_file, max_age=3600)


def run_story_visualizer(custom_story_graph_path=None, debug=True, host='0.0.0.0', port=5002):
    global story_graph_path
    story_graph_path = custom_story_graph_path
    app.run(debug=debug, host=host, port=port)


def main():
    import argparse

    parser = argparse.ArgumentParser(description='启动 ELK Layered Narrative Map 可视化服务器')
    parser.add_argument('--story-graph', type=str, dest='story_graph_path', help='故事图 JSON（推荐 storyline_elk.json）')
    parser.add_argument('--debug', action='store_true', dest='debug', help='启用调试模式')
    parser.add_argument('--host', type=str, dest='host', default='0.0.0.0', help='服务器主机地址')
    parser.add_argument('--port', type=int, dest='port', default=5002, help='服务器端口')
    args = parser.parse_args()
    run_story_visualizer(args.story_graph_path, args.debug, args.host, args.port)


if __name__ == '__main__':
    main()

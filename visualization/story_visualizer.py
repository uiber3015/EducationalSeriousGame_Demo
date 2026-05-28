from flask import Flask, render_template, jsonify, send_from_directory
import json
import os

# 获取当前文件所在目录的绝对路径
current_dir = os.path.dirname(os.path.abspath(__file__))
# On_use/visualization is one level below the demo package root.
project_root = os.path.dirname(current_dir)

app = Flask(__name__, 
           static_folder=os.path.join(project_root, 'output'),
           template_folder=os.path.join(current_dir, 'templates'))

# 全局变量存储故事图路径
story_graph_path = None

def get_story_graph_absolute_path():
    global story_graph_path
    if not story_graph_path:
        return None
    if os.path.isabs(story_graph_path):
        return story_graph_path
    candidates = [
        os.path.abspath(os.path.join(project_root, story_graph_path)),
        os.path.abspath(os.path.join(current_dir, story_graph_path)),
        os.path.abspath(os.path.join(os.getcwd(), story_graph_path)),
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    return candidates[0]

def get_candidate_output_images_dirs():
    candidate_dirs = []

    graph_abs_path = get_story_graph_absolute_path()
    if graph_abs_path:
        graph_dir = os.path.dirname(graph_abs_path)
        graph_parent_dir = os.path.dirname(graph_dir)

        direct_output_images_dir = os.path.join(graph_dir, 'output_images')
        sibling_output_images_dir = os.path.join(graph_parent_dir, 'output_images')

        for candidate_dir in [direct_output_images_dir, sibling_output_images_dir]:
            if os.path.isdir(candidate_dir) and candidate_dir not in candidate_dirs:
                candidate_dirs.append(candidate_dir)

    output_root = os.path.join(project_root, 'output')
    if os.path.isdir(output_root):
        for subdir in os.listdir(output_root):
            subdir_path = os.path.join(output_root, subdir)
            output_images_path = os.path.join(subdir_path, 'output_images')
            if os.path.isdir(output_images_path) and output_images_path not in candidate_dirs:
                candidate_dirs.append(output_images_path)

    return candidate_dirs

NARRATIVE_MAP_URL = '/story-graph-visualization'


@app.route('/')
def index():
    return render_template('interactive_story.html', narrative_map_url=NARRATIVE_MAP_URL)


@app.route('/interactive-story')
def interactive_story():
    return render_template('interactive_story.html', narrative_map_url=NARRATIVE_MAP_URL)

@app.route('/story-graph-visualization')
def story_graph_visualization():
    return render_template('story_graph_visualization.html')

@app.route('/api/story-graph')
def get_story_graph():
    global story_graph_path
    
    # 如果没有设置故事图路径，使用指定的文件夹
    if story_graph_path is None:
        story_graph_path = os.path.join('output', 'cot_20260209_160249', 'output', 'story_graph_with_image_prompts_with_scene_transitions_with_images.json')
        print(f" 加载故事图: {story_graph_path}")

    story_graph_abs_path = get_story_graph_absolute_path()
    
    # 如果文件不存在，尝试使用其他可能的故事图文件
    if not story_graph_abs_path or not os.path.exists(story_graph_abs_path):
        alternative_paths = [
            os.path.join(project_root, 'output', 'continued_story_graph.json'),
            os.path.join(project_root, 'output', 'story_graph.json'),
            os.path.join(project_root, 'output', 'enhanced_story_graph.json'),
            os.path.join(project_root, 'output', 'continued_all_story_graph.json')
        ]
        
        for path in alternative_paths:
            if os.path.exists(path):
                story_graph_path = path
                story_graph_abs_path = path
                break
        else:
            # 如果所有文件都不存在，返回空的故事图
            return jsonify({
                'nodes': [],
                'edges': {},
                'start_node_id': '',
                'ending_node_ids': []
            })
    
    try:
        with open(story_graph_abs_path, 'r', encoding='utf-8') as f:
            story_graph = json.load(f)
        
        # 处理故事图数据，确保与前端兼容
        processed_graph = process_story_graph(story_graph)
        return jsonify(processed_graph)
    except Exception as e:
        print(f"Error loading story graph: {e}")
        return jsonify({
            'error': 'Failed to load story graph',
            'message': str(e)
        }), 500

def process_story_graph(story_graph):
    """
    处理故事图数据，确保与前端兼容
    
    Args:
        story_graph: 原始故事图数据
        
    Returns:
        处理后的故事图数据
    """
    # 创建处理后的故事图
    processed_graph = {
        'nodes': story_graph.get('nodes', []),
        'edges': story_graph.get('edges', {}),
        'start_node_id': story_graph.get('start_node_id', 'node_1'),
        'ending_node_ids': []
    }
    
    # 收集所有ending类型的节点ID
    for node in processed_graph['nodes']:
        metadata = node.get('metadata', {})
        image_path = metadata.get('image_path')
        if image_path:
            normalized_path = image_path.replace('\\', '/')
            filename = os.path.basename(normalized_path)
            if filename:
                metadata['image_path'] = f"/output_images/{filename}"

        if node.get('type') == 'ending':
            processed_graph['ending_node_ids'].append(node['id'])
    
    # 如果没有找到ending节点，使用原始的ending_node_ids
    if not processed_graph['ending_node_ids']:
        processed_graph['ending_node_ids'] = story_graph.get('ending_node_ids', [])
    
    # 确保edges中的每个节点都有对应的边列表
    for node in processed_graph['nodes']:
        node_id = node['id']
        if node_id not in processed_graph['edges']:
            processed_graph['edges'][node_id] = []
    
    return processed_graph

@app.route('/output_images/<path:filename>')
def serve_output_images(filename):
    for output_images_path in get_candidate_output_images_dirs():
        candidate_file = os.path.join(output_images_path, filename)
        if os.path.exists(candidate_file):
            return send_from_directory(output_images_path, filename)
    
    # 如果没有找到匹配的目录，返回404
    return "Image not found", 404

@app.route('/output/<path:subpath>/<path:filename>')
def serve_output_subpath(subpath, filename):
    # 动态查找匹配的目录
    output_dir = 'output'
    if os.path.exists(output_dir):
        # 遍历output目录下的所有子目录
        for subdir in os.listdir(output_dir):
            # 如果子目录名匹配请求的subpath
            if subdir == subpath:
                directory = os.path.join(output_dir, subdir)
                if os.path.exists(directory):
                    return send_from_directory(directory, filename)
    
    # 如果没有找到匹配的目录，返回404
    return "File not found", 404

@app.route('/<path:subpath>/output_images/<path:filename>')
def serve_nested_output_images(subpath, filename):
    # 动态查找匹配的嵌套output_images目录
    output_dir = 'output'
    if os.path.exists(output_dir):
        # 遍历output目录下的所有子目录
        for subdir in os.listdir(output_dir):
            # 如果子目录名匹配请求的subpath
            if subdir == subpath:
                directory = os.path.join(output_dir, subdir, 'output_images')
                if os.path.exists(directory):
                    return send_from_directory(directory, filename)
    
    # 如果没有找到匹配的目录，返回404
    return "Image not found", 404

def run_story_visualizer(custom_story_graph_path=None, debug=True, host='0.0.0.0', port=5000):
    global story_graph_path
    story_graph_path = custom_story_graph_path
    app.run(debug=debug, host=host, port=port)

def main():
    import argparse
    
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='启动故事可视化服务器')
    parser.add_argument('--story-graph', type=str, dest='story_graph_path',
                        help='故事图JSON文件的路径')
    parser.add_argument('--debug', action='store_true', dest='debug',
                        help='启用调试模式')
    parser.add_argument('--host', type=str, dest='host', default='0.0.0.0',
                        help='服务器主机地址')
    parser.add_argument('--port', type=int, dest='port', default=5000,
                        help='服务器端口')
    
    # 解析命令行参数
    args = parser.parse_args()
    
    # 启动故事可视化服务器
    run_story_visualizer(args.story_graph_path, args.debug, args.host, args.port)

if __name__ == '__main__':
    main()
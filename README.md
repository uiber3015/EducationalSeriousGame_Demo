# Educational Game Demo Package

This folder contains the cleaned demo package for the bilingual educational games.

## Recommended Entry Point

### 静态站点入口（推荐，适合 Vercel）

直接打开或部署仓库根目录：

- `index.html`：总入口
- `zh/index.html`：中文总入口
- `en/index.html`：英文总入口
- `interactive-story.html`：静态互动游戏页
- `narrative-map-classic.html` / `narrative-map-elk.html`：静态叙事地图页

数据已预处理到 `static/story_graph/`，页面不再依赖 Flask API 或本机端口。

重新生成静态文件：

```powershell
python "tools/build_static_site.py"
```

### Flask 调试入口（仅本机开发）

```powershell
cd "d:\AAA\工作\work_on_vske\On_use\bilingual_hub"
python "bilingual_hub_server.py" --debug --port 5004
```

Open:

- 启动页：`http://localhost:5004/`（会跳转到 `/zh`）
- 中文总入口：`http://localhost:5004/zh`
- 英文总入口：`http://localhost:5004/en`

## Included Games

- Tech Education
- Spring Outing Adventure
- Moving Day Chaos
- Fire Rescue

## Standalone Fallbacks

Classic visualizer for the first three games:

```powershell
cd "d:\AAA\工作\work_on_vske\On_use\visualization"
python "story_visualizer.py" --debug --port 5000 --story-graph "d:\AAA\工作\work_on_vske\On_use\cot_20260424_123248\output\story_graph_with_image_prompts_with_scene_transitions_with_images.json"
```

Fire Rescue ELK visualizer:

```powershell
cd "d:\AAA\工作\work_on_vske\On_use\demo_elk\visualization"
python "story_visualizer_narrative_elk_demo.py" --debug --port 5002
```


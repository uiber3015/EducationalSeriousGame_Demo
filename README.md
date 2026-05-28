# Educational Game Demo Package

This folder contains the cleaned demo package for the bilingual educational games.

## Recommended Entry Point

Run the bilingual hub:

```powershell
cd "d:\AAA\工作\work_on_vske\On_use\bilingual_hub"
python "bilingual_hub_server.py" --debug --port 5004
```

Open:

- Chinese hub: `http://localhost:5004/zh`
- English hub: `http://localhost:5004/en`

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


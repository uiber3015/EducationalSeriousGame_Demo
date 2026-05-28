## ELK Demo Package (Standalone)

This folder is an isolated demo bundle for the ELK narrative map UI.

### Included

- `visualization/story_visualizer_narrative_elk_demo.py`
- `visualization/templates/story_graph_visualization_elk.html`
- `visualization/templates/interactive_story.html`
- `output/fire_core_for_edu_new/output/story_graph_storyline_elk.json`
- `output/fire_core_for_edu_new/output/story_graph_storyline.json`
- `output/fire_core_for_edu_new/output_images/*` (all required node images + runtime JSONs)

### Run

```powershell
cd "d:\AAA\工作\work_on_vske\On_use\demo_elk"
python "visualization\story_visualizer_narrative_elk_demo.py" --debug --port 5002
```

Open:

- `http://localhost:5002/narrative-map-elk`
- `http://localhost:5002/interactive-story`


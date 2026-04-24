# Documentation Assets

This folder is for README screenshots, GIFs, and short demo videos. The project already has tracked test fixtures in `media/core_images/`; those fixtures are used by tests and examples, so they should stay there.

## Existing Visual Assets

The main README currently references these tracked media fixtures:

| Asset | Purpose |
| --- | --- |
| `media/core_images/phase05_house_scene.png` | Enclosing house context fixture. |
| `media/core_images/phase04_bedroom_scene.png` | Bedroom fixture used in nested context and bundle scenarios. |
| `media/core_images/phase04_living_room_scene.png` | Living room fixture used in nested context scenarios. |
| `media/core_images/phase04_unknown_scene.png` | Unknown scene fixture used to confirm the agent asks for a label. |

These are small generated images, not screenshots of the terminal workflow.

## Suggested Future Captures

If a richer public demo is needed, capture real output from the current CLI and save it here:

| Suggested path | What to capture |
| --- | --- |
| `docs/assets/demo.gif` | A short terminal session that teaches a media fixture, recognizes it, and runs `inspect`. |
| `docs/assets/screenshot-home.png` | A still terminal screenshot showing the Phase 8 banner or quiet-mode session. |
| `docs/assets/demo-video.mp4` | A longer walkthrough for the README or project article. |

Do not reference these files from the README until they actually exist.

## Capture Checklist

- Use the current repository state.
- Prefer a clean temporary runtime directory so the demo is easy to follow.
- Show one scalar example and one `sense /path/to/file` example if there is enough room.
- Avoid exposing local personal paths in final public screenshots when possible.
- Update the README only after the asset has been committed or otherwise made available in the repository.

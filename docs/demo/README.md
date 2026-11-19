# Demo animation

`handoff-demo.gif` (in the top-level README) and `handoff-demo.mp4` show one round of the `handoff` skill.

- `capture.py` runs that round for real on throwaway repositories (a bare remote and two clones, `claude` and
  `codex`) with `skills/handoff/scripts/handoff.py`, and writes every command and its output to `transcript.js`.
  Commit dates are pinned to one value, so the `date:` lines imply no durations.
- `demo.html` draws the animation from `transcript.js`. The pull-request comment is the real output of
  `handoff.py announce`. The request bubble and the final notification are illustrations. The two times shown
  (about 10 s from push to comment, about 3 s from comment to wake-up) were measured on a Claude Code cloud session.
  Open the file in a browser to watch it play.
- `build.js` steps through the frames with Playwright and encodes them with ffmpeg: GIF at 880x540, 10 fps; MP4
  (H.264) at 1760x1080, 30 fps.

Rebuild, from the repository root (Python 3, Node with Playwright, ffmpeg; fonts Inter and JetBrains Mono if
installed, otherwise system fallbacks):

```bash
python3 docs/demo/capture.py && node docs/demo/build.js
```

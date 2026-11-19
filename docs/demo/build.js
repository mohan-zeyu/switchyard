// Render demo.html frame by frame and encode handoff-demo.gif and handoff-demo.mp4 next to this file.
//
//   node docs/demo/build.js            # both
//   node docs/demo/build.js gif        # or: mp4, or: frames <t1,t2,...> <outdir> (PNG stills for checking)
//
// Needs Playwright (with its Chromium) and ffmpeg on PATH. Frames go to a temporary directory under $TMPDIR.
const { chromium } = require("playwright");
const { execFileSync } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");

const HERE = __dirname;
const W = 880, H = 540;

async function frames(scale, times, dir) {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: scale });
  await page.goto("file://" + path.join(HERE, "demo.html"));
  await page.evaluate(() => document.fonts.ready);
  for (let i = 0; i < times.length; i++) {
    await page.evaluate(t => window.renderAt(t), times[i]);
    await page.screenshot({ path: path.join(dir, `f${String(i).padStart(5, "0")}.png`) });
  }
  await browser.close();
}

async function duration() {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto("file://" + path.join(HERE, "demo.html"));
  const d = await page.evaluate(() => window.DURATION);
  await browser.close();
  return d;
}

const steps = (d, fps) => Array.from({ length: Math.round(d * fps) }, (_, i) => i / fps);
const ff = args => execFileSync("ffmpeg", ["-y", "-loglevel", "error", ...args], { stdio: "inherit" });

async function gif(d) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "handoff-gif-"));
  const fps = 10;
  await frames(1, steps(d, fps), dir);
  ff(["-framerate", String(fps), "-i", path.join(dir, "f%05d.png"), "-vf",
      "split[a][b];[a]palettegen=max_colors=128:stats_mode=full[p];[b][p]paletteuse=dither=none:diff_mode=rectangle",
      "-loop", "0", path.join(HERE, "handoff-demo.gif")]);
  fs.rmSync(dir, { recursive: true });
}

async function mp4(d) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "handoff-mp4-"));
  const fps = 30;
  await frames(2, steps(d, fps), dir);
  ff(["-framerate", String(fps), "-i", path.join(dir, "f%05d.png"), "-c:v", "libx264", "-preset", "slow", "-crf", "22",
      "-pix_fmt", "yuv420p", "-movflags", "+faststart", path.join(HERE, "handoff-demo.mp4")]);
  fs.rmSync(dir, { recursive: true });
}

(async () => {
  const what = process.argv[2] || "all";
  if (what === "frames") {
    const times = process.argv[3].split(",").map(Number);
    fs.mkdirSync(process.argv[4], { recursive: true });
    await frames(1, times, process.argv[4]);
    return;
  }
  const d = await duration();
  if (what === "all" || what === "gif") await gif(d);
  if (what === "all" || what === "mp4") await mp4(d);
})().catch(e => { console.error(e); process.exit(1); });

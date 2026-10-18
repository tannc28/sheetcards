"""Sheet to Anki's half of carrying media inside the .apkg (site/media.js), in node.

The rules are src/media.py's and come in as `py`; what is pinned here is the
fetching: Commons is asked once for its titles, an address that refuses a
browser (a CORS failure, a throw) stays a link, the cache is used before the
network, at most four fetches run at once, and the size limit cuts the same
files every time — in the order of the sheet.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
NODE = shutil.which("node")

pytestmark = [
    pytest.mark.unit,
    pytest.mark.skipif(NODE is None, reason="node is not installed"),
]

SCRIPT = """
const m = await import(%s);
const jobs = [
  { url: "https://a.org/1.jpg", kind: "image", name: "_sc-1.jpg", commons: null },
  { url: "https://nocors.org/2.mp3", kind: "audio", name: "_sc-2.mp3", commons: null },
  { url: "https://commons/File:B.ogg", kind: "audio", name: "_sc-3.mp3", commons: "B.ogg" },
  { url: "https://a.org/4.jpg", kind: "image", name: "_sc-4.jpg", commons: null },
  { url: "https://a.org/page", kind: "image", name: null, commons: null },
];
const py = {
  queries: (titles) => ["https://api/?t=" + titles.join("|")],
  sources: (answers) => JSON.parse(answers[0]),
  settle: (job, type, size) => (type.startsWith(job.kind) && size ? job.name || "_sc-5.webp" : null),
  limit: 25,
};
let running = 0, most = 0;
const asked = [];
const body = (type, n) => ({ ok: true, headers: { get: () => type },
  text: async () => JSON.stringify({ "B.ogg": { audio: "https://upload/B.mp3" } }),
  arrayBuffer: async () => new Uint8Array(n).buffer });
const fake = async (url) => {
  asked.push(url);
  running++; most = Math.max(most, running);
  await new Promise((r) => setTimeout(r, 5));
  running--;
  if (url.startsWith("https://nocors")) throw new TypeError("Failed to fetch");
  if (url.startsWith("https://api")) return body("application/json", 0);
  if (url.endsWith(".mp3")) return body("audio/mpeg", 10);
  if (url.endsWith("page")) return body("image/webp", 4);
  return body("image/jpeg", 8);
};
const store = new Map();
const cache = { get: async (u) => store.get(u) || null, put: async (u, e) => { store.set(u, e); } };
const ticks = [];
const first = await m.gatherMedia(jobs, { py, fetch: fake, cache, progress: (d, t) => ticks.push([d, t]) });
const askedFirst = asked.length;
const second = await m.gatherMedia(jobs, { py, fetch: fake, cache });
const view = (r) => ({ ...r, files: r.files.map(([u, n, d]) => [u, n, d.length]) });
process.stdout.write(JSON.stringify({ first: view(first), second: view(second), asked, askedFirst,
  askedAgain: asked.length - askedFirst, most, ticks }));
"""


@pytest.fixture(scope="module")
def out():
    module = json.dumps((REPO / "site" / "media.js").as_uri())
    result = subprocess.run(
        [NODE, "--input-type=module", "-e", SCRIPT % module],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_what_the_browser_may_read_travels(out):
    files = out["first"]["files"]
    assert [f[0] for f in files] == [
        "https://a.org/1.jpg",
        "https://commons/File:B.ogg",
        "https://a.org/page",
    ]
    assert files[2][1] == "_sc-5.webp"  # named from the answer's type


def test_commons_is_asked_for_its_titles_and_fetched_from_the_upload_host(out):
    assert "https://api/?t=B.ogg" in out["asked"]
    assert "https://upload/B.mp3" in out["asked"]
    assert "https://commons/File:B.ogg" not in out["asked"]


def test_a_cors_refusal_and_the_size_limit_leave_links(out):
    first = out["first"]
    # 8 + 10 + 4 fit in 25; the second 8-byte picture does not.
    assert first["bytes"] == 22
    assert first["links"] == 2 and first["over"] == 1
    assert first["image"] == 2 and first["audio"] == 1


def test_a_second_download_fetches_only_what_failed(out):
    again = out["asked"][out["askedFirst"] :]
    assert again == ["https://nocors.org/2.mp3"]
    assert out["second"]["files"] == out["first"]["files"]


def test_four_at_a_time_and_progress_counts_every_job(out):
    assert out["most"] <= 4
    assert out["ticks"][0] == [0, 5] and out["ticks"][-1] == [5, 5]

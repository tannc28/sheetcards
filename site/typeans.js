/**
 * Anki's typed-answer box, as the preview can honestly show it.
 *
 * `{{type:Field}}` is not a filter. Anki's renderer leaves the tag in the
 * template and the *reviewer* substitutes it twice: an `<input>` while the
 * question is up, and a character-by-character comparison once the answer is
 * shown. A preview that treated it as an unknown filter printed the field
 * instead — which is to say it printed the answer on the question, the one thing
 * a typed-answer card exists to withhold.
 *
 * `compareAnswer` reproduces `Collection.compare_answer` (Rust, rslib), whose
 * exact output was read off a real collection and is pinned in
 * tests/test_site_typeans.py. The rules it implements:
 *
 *   - nothing typed        → the expected text, plain, no markup at all
 *   - typed == expected    → one `typeGood` span, showing the *expected* text
 *                            (which is the point of `nc`: you typed "el arbol"
 *                            and it shows you "el árbol")
 *   - otherwise            → two lines separated by a `↓`: what you typed, with
 *                            wrong characters `typeBad` and a `-` standing in
 *                            for each one you left out, then the expected text
 *                            with the characters you missed marked `typeMissed`
 *
 * The function is deliberately self-contained — every helper it uses is declared
 * inside it — because `runtime()` serialises it with `toString()` into the card's
 * own document. The card is a separate document with no module loader, and one
 * copy of a diff is better than two copies that drift.
 */

/**
 * The inside of Anki's `<code id=typeans>` element.
 *
 * @param {string} expected  the field's text, HTML already stripped
 * @param {string} typed     what the learner typed
 * @param {boolean} nc       compare without combining marks (the `nc:` prefix)
 */
export function compareAnswer(expected, typed, nc) {
  const esc = (s) =>
    String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  const span = (cls, text) =>
    text ? `<span class=${cls}>${esc(text)}</span>` : "";

  // With `nc`, alignment runs on the stripped characters while each line still
  // prints its own originals — one key per character, so the two stay in step.
  const key = (ch) => (nc ? ch.normalize("NFD").replace(/\p{M}/gu, "") : ch);

  const A = [...String(typed)]; // what was typed
  const B = [...String(expected)]; // what was wanted

  // Anki shows an unanswered card's expected text as bare text, not as a diff.
  if (!A.length) return esc(expected);

  const ka = A.map(key);
  const kb = B.map(key);

  // Longest common subsequence, then walk it back into runs. Answers are a
  // handful of words; the cap is only there so a pathological cell cannot make
  // the browser build a million-entry table.
  let ops;
  if (A.length * B.length > 250000) {
    ops = [{ tag: "replace", a: A, b: B }];
  } else {
    const n = A.length;
    const m = B.length;
    const dp = new Uint32Array((n + 1) * (m + 1));
    for (let i = n - 1; i >= 0; i--) {
      for (let j = m - 1; j >= 0; j--) {
        dp[i * (m + 1) + j] =
          ka[i] === kb[j]
            ? dp[(i + 1) * (m + 1) + j + 1] + 1
            : Math.max(dp[(i + 1) * (m + 1) + j], dp[i * (m + 1) + j + 1]);
      }
    }
    ops = [];
    let i = 0;
    let j = 0;
    const push = (tag, a, b) => {
      const last = ops[ops.length - 1];
      if (last && last.tag === tag) {
        last.a = last.a.concat(a);
        last.b = last.b.concat(b);
      } else ops.push({ tag, a, b });
    };
    while (i < n || j < m) {
      // A character of the expected answer that was never typed. Taken in
      // preference to a match whenever it costs nothing, because that is where
      // Anki's own diff puts it: "helo" against "hello" reports the missing
      // letter at the first l, not at the second.
      if (j < m && dp[i * (m + 1) + j + 1] === dp[i * (m + 1) + j]) {
        push("miss", [], [B[j]]);
        j++;
      } else if (i < n && j < m && ka[i] === kb[j]) {
        push("equal", [A[i]], [B[j]]);
        i++;
        j++;
      } else if (j < m && (i >= n || dp[i * (m + 1) + j + 1] >= dp[(i + 1) * (m + 1) + j])) {
        push("miss", [], [B[j]]);
        j++;
      } else {
        // A character that was typed and does not belong.
        push("extra", [A[i]], []);
        i++;
      }
    }
    // A run typed *and* a run missed at the same place is one substitution, and
    // Anki draws it as one: the wrong characters against the right ones, with no
    // dashes standing in for anything.
    const merged = [];
    for (const op of ops) {
      const last = merged[merged.length - 1];
      if (op.tag === "miss" && last && last.tag === "extra") {
        merged[merged.length - 1] = { tag: "replace", a: last.a, b: op.b };
      } else if (op.tag === "extra" && last && last.tag === "miss") {
        merged[merged.length - 1] = { tag: "replace", a: op.a, b: last.b };
      } else merged.push(op);
    }
    ops = merged;
  }

  if (ops.every((op) => op.tag === "equal")) {
    return span("typeGood", expected);
  }

  let typedLine = "";
  let wantedLine = "";
  for (const op of ops) {
    const a = op.a.join("");
    const b = op.b.join("");
    if (op.tag === "equal") {
      typedLine += span("typeGood", a);
      wantedLine += span("typeGood", b);
    } else if (op.tag === "extra") {
      typedLine += span("typeBad", a);
    } else if (op.tag === "miss") {
      typedLine += span("typeMissed", "-".repeat(op.b.length));
      wantedLine += span("typeMissed", b);
    } else {
      typedLine += span("typeBad", a);
      wantedLine += span("typeMissed", b);
    }
  }
  return `${typedLine}<br><span id=typearrow>&darr;</span><br>${wantedLine}`;
}

/**
 * The same code, as a script the card document can carry.
 *
 * The card is its own document — no bundler, no imports — so the function is
 * serialised in rather than fetched. The wiring around it is what makes the box
 * a box you can actually type into: Enter reveals the comparison, and after that
 * every keystroke redraws it. On the answer tabs it is revealed to begin with,
 * showing what Anki shows a learner who typed nothing.
 */
export function typeansRuntime() {
  return `<script>
${compareAnswer.toString()}
(function () {
  for (const box of document.querySelectorAll(".s2a-type")) {
    const spec = JSON.parse(box.dataset.typeans);
    const input = box.querySelector("input");
    const out = box.querySelector(".s2a-typeans");
    const draw = () => {
      out.hidden = false;
      out.innerHTML = '<code class="typeans">'
        + compareAnswer(spec.expect, input.value, spec.nc) + "</code>";
    };
    input.addEventListener("input", () => { if (!out.hidden) draw(); });
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") { e.preventDefault(); draw(); }
    });
    if (document.body.hasAttribute("data-answered")) draw();
  }
})();
<\/script>`;
}

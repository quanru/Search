# Search Midscene E2E

## Why desktop tests

Search is a native SwiftUI/AppKit application containing WKWebView, not a web
application. Its existing `Tests/SearchTests` suite checks imports, persistence,
downloads and extensions; Python probes drive model state in hidden windows.
There was no GitHub Actions workflow. These tests use `@midscene/test` to add visible user journeys
through the real application, using `@midscene/computer` rather than a Chromium
page that would miss Search's native menus, sheets and file chooser.

The design references [Rome #466](https://github.com/rome-os/rome/pull/466) and
[its follow-up #551](https://github.com/rome-os/rome/pull/551), plus the local
Rome test harness. It borrows isolation, credential gates, serial shards and
native report handling. Rome's business cases and web server are not reused.
The desktop API is described in the [Midscene documentation](https://midscenejs.com/platforms/desktop).

## Cases and isolation

`cases/*.yaml` contains the executable Midscene Test workflows; `cases.json` is
the reviewed inventory. `midscene.config.ts` registers `ComputerAgent` through
`createMidsceneNodes`, plus the deterministic `app.open` setup node. User actions are `aiAct` prompts;
visible outcomes are `aiAssert` prompts. No selectors or probe commands perform
user steps. The existing bench socket is used only as a startup readiness marker.

| Shard | Cases |
| --- | --- |
| import | Bookmarks file import; repeated import without duplicates |
| navigation | Navigate to a local page and find three occurrences of a word |

Every case starts a fresh process from a temporary app copy with a unique
bundle ID and `SEARCH_PROBE=midscene-<uuid>`. This gives it its own defaults
suite, support folder, WebKit storage and synthetic browser discovery root.
Each case generates its own Netscape bookmarks export and loopback HTTP server
with an ephemeral port. The update feed is also redirected to that server.
Fixtures have no external resources and a restrictive CSP. The model credentials
are removed from the launched application's environment.

This is the native equivalent of Rome's fresh browser context, not a shared
Playwright session. Only the child process started by the harness is terminated;
its temporary files, probe defaults and named WebKit caches are removed.
Force-killing the test runner can interrupt cleanup, so use a disposable desktop
account. Password/keychain and real installed-browser imports are intentionally
outside this initial inventory. The harness does not implement a system-wide
network firewall: additional cases must keep all page requests local.

## Local commands

Requires macOS 14+, Node 22.12+, Xcode command line tools and an English desktop
with a US keyboard layout. Use a dedicated test account/desktop: the SDK drives
the actual mouse and keyboard and screenshots contain the visible screen.
Grant Accessibility, Screen Recording, and Automation of System Events to the
terminal/runner that launches Node. Do not run multiple desktop shards together.

```sh
./build.sh debug
cd Tests/Midscene
npm ci
npm run check                    # No model or desktop access
# Export the four MIDSCENE_MODEL_* variables from .env.example securely.
MIDSCENE_DESKTOP_ENABLED=1 MIDSCENE_SHARD=import npm test
# Omit MIDSCENE_SHARD to run the whole inventory serially.
npm run report
```

`SEARCH_E2E_APP` can override the built app path. The default is
`../../build/Search.app` on Apple Silicon or `../../build/intel/Search.app` on Intel,
relative to `Tests/Midscene`. Missing credentials,
unknown shards and absent builds fail before any desktop agent is created.
The desktop opt-in is mandatory. No model retry is automatic: investigate the
native HTML before rerunning a failed journey.

## CI configuration

Every PR and pushed branch runs type checking, native framework YAML collection, report regression tests and Swift
regressions with no model secrets. The seven WebKit download tests run in
separate XCTest processes via `Tests/run-ci-tests.py`; all 51 Swift cases remain
required. They use GitHub-hosted `macos-15-intel`. Visual
tests run only for the default branch or the owner-configured trusted ref on push or manual dispatch, and only when
the repository variable `MIDSCENE_DESKTOP_ENABLED=true` is set. All pushed branches can run the secret-free checks. To validate an implementation branch before merging,
set `MIDSCENE_TRUSTED_REF` to its full ref, such as `refs/heads/test/midscene-e2e`;
clear that variable after validation. PR events never run model tests.

The Intel hosted runner passed the SDK screenshot, mouse movement and permissions
checks on 2026-09-30, exposing a 1920×1080 display. In the same check, ARM
`macos-15` exposed zero displays and failed screenshot capture. The optional
`desktop-capability` job records current runner evidence without model credentials.
No self-hosted runner is required. Set repository secrets `MIDSCENE_MODEL_API_KEY`,
`MIDSCENE_MODEL_NAME`, `MIDSCENE_MODEL_BASE_URL`, `MIDSCENE_MODEL_FAMILY` for a
supported vision model. Install/build steps do not receive those secrets.
The model endpoint must be reachable from GitHub's hosted network. Desktop
availability does not imply access to an internal model gateway: a connection
timeout should be resolved with a reachable provider or an approved runner with
the necessary network access, rather than by changing assertions or adding retries.
Both matrix shards run serially with `fail-fast: false`; a concurrency group
also serializes separate workflow runs. Each hosted job gets a fresh VM.

Optionally enable GitHub Pages with Actions as its source and set repository
variable `MIDSCENE_PAGES_URL` to the complete base URL, for example
`https://quanru.github.io/Search`. Use a repository where Pages is reserved for
these reports. Configure the `github-pages` environment to allow the default
branch. Published paths include both run ID and attempt number. Pages publishes
the latest workflow's reports; older reports remain downloadable as artifacts
for 14 days, but their hosted URLs expire when the next site replaces them.
With Pages enabled, Summary tables embed each case's PNG screenshot and link
to its exact native HTML. Without it, Summary provides artifact-relative paths;
GitHub artifacts cannot serve inline images or HTML. Check the publish job if
hosted links do not resolve.

## Native reports and failure handling

`npm test` calls the official `runTestProject` API; Midscene Test owns execution,
step timeouts, lifecycle teardown, outcomes and the unified native framework
report. The entry script only clears old output and exports case metadata for
CI Summary. `npm run nodes` generates the official Node Spec and is also part
of the secret-free checks. `tsx` is pinned for compatibility with the framework
CLI's CommonJS config loader.

Each case also saves a standalone Midscene HTML report with screenshots embedded,
a final PNG, and a `results.json` entry. Reports are written even after AI
assertion failure. The package pins Midscene versions in its npm lockfile.
The report job downloads shards into separate directories, merges via
`mergeReportFiles` from `@midscene/core`, and builds a Markdown case table from
the manifest. It never creates a substitute HTML report.

A missing case/report/screenshot or failed merge makes the report job fail.
Per-case reports remain in the combined artifact and can still be published
when native merging fails. Partial merged output is removed. Starting a new
shard deletes old `midscene_run`; assembling a report removes its old native
merge before processing the current results. Tests cover exact links, screenshots,
merge failure fallback and incomplete reruns.

A per-case runtime JSON records only the owned test world's bookmarks and process
identity, so isolation failures can be distinguished from UI assertion failures.
The setup raises the owned process's window and verifies its foreground PID.
Visual CI runs independently of the Swift regression job; failures in either
suite remain failures, and a Swift failure does not suppress visual evidence.

A shard timeout or setup failure may yield no report for its unfinished cases;
the aggregate Summary records those cases as missing rather than passed. Job
logs retain startup errors. Model execution was exercised locally and in hosted
CI. Hosted Intel CI verified isolated app startup and native report publication,
but the selected internal model endpoint timed out from GitHub's network. Local
AI assertions passed navigation and file import; repeated import reported duplicate
entries and needs further investigation. Visual journeys are not yet a passing
release gate.

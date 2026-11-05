# U8 failed attempts and corrections

Short record of the real failures encountered while implementing and testing
U8. Each entry names the symptom, the diagnosis and the correction. No product
requirement was weakened to make a test pass.

1. **Baseline suite passed.** No pre-existing baseline failure needed scope
   analysis: 1,238 passed, 1 skipped, 90.02% combined coverage; mypy, Ruff lint
   and Ruff format all passed.

2. **Home filter test failed after the intentional message change.**
   `test_home_text_filter_focus_enter_escape_and_empty_states` asserted the old
   exact sentence. The test was updated to the new sentence that tells the user
   to press `Esc`; no other assertion changed.

3. **A disposable probe timed out waiting for capture.**
   The probe passed an unresolved `/var/.../home` while the environment resolved
   to `/private/var/...`, so `capture_session` refused the mismatched home. The
   probe resolved its temporary home; tests use the repository fixtures.

4. **A probe queried the wrong screen.** `app.query_one` searched the default
   Home screen while Help was on top. The probe used `app.screen.query_one`;
   the product code was not changed.

5. **A Compare probe chose the same agent twice.** The B column starts on the
   same highlighted agent as A. The probe pressed `down` before choosing B.
   This became the duplicate-choice test instead of a product defect.

6. **The Why worker test used a nonexistent `.report` property.**
   `WhyScreen` stores `_report`; the test was corrected.

7. **A suspension test asserted an empty controller cache.** The Why report was
   already cached, so the assertion was narrowed to the `diff`/`compare` view
   under test.

8. **A worker-owned-token check raced the worker thread.** The controlled worker
   could set its "started" event before `_owned_request` was assigned. Tests now
   wait for both the event and the owned token.

9. **The stale-outcome test blocked only the second Diff call.** The first call
   completed before Help opened, so there was no live token to cancel. Both the
   first and second calls are now gated; the test injects stale outcomes around
   the real replacement.

10. **An unreadable skill directory made capture raise `IncompleteTreeError`.**
    That is correct capture behaviour. To exercise the captured-unreadable-root
    UI without changing core behaviour, the test injects the stored
    `scan.unreadable` record, matching the existing Home test.

11. **A literal markup description beginning with `[` broke YAML frontmatter.**
    The fixture description now starts with ordinary text before the
    markup-like characters, so it is valid YAML and still literal on screen.

12. **A Diff preservation test saw one copy instead of two.** With `cwd` equal
    to the mock home, the scenario's project copy is outside the project root.
    The app was launched with `cwd=project`, matching existing Diff tests.

13. **A refresh row-count expectation was wrong.** Deleting the project copy
    and adding one live-only skill nets the same row count. The test asserts the
    unchanged count plus the new key, then checks content after refresh.

14. **An A6 test pressed `d` while Why was in raw JSON.** Why correctly blocks
    Diff in that mode. The test presses `J` to leave JSON first.

15. **A broad text replacement inserted an unintended `J` before `d` in an
    unrelated worker test.** It passed only because of mount timing; it was
    removed to keep the test deterministic.

16. **An empty-catalog filter test expected the filter message.** With no rows
    at all, Home correctly says the catalog is empty rather than blaming the
    filter. The test now asserts the empty-catalog distinction; the existing
    nonempty-filter test covers the no-match message.

17. **A test queried `#diff-content` as a `Static`.** It is a `Vertical`
    container; the test queries its `Static` children instead.

18. **A Diff Help note assertion was over-specific.** Diff Help does not repeat
    the model's "no differences" sentence; the test now asserts the named Diff
    section and keeps the model answer assertion on the screen body.

19. **A Diff body was not scrollable in a scroll-restoration test.** The fixture
    had no differing copy. A second, longer Codex copy makes the report body
    genuinely scrollable.

20. **The mutation runner resolved the repository root one level too high.**
    `parents[5]` now points at the checkout; the first run failed before any
    mutation was applied.

21. **The first covered-key-leak mutation had no observable effect.** It called
    Home's guarded action, which correctly refused while suspended. The mutation
    now plants a direct hidden `open_why` call in Help; the hidden-key test
    catches it.

22. **Two fault mutations were mis-reported as survivors by the runner.** The
    mutants did fail meaningfully, but the expected substrings used source-code
    quoting rather than pytest's failure text. The expected strings were
    corrected; the final campaign caught 12/12.

23. **Home Help notes contained live counts.** Those could become stale during a
    covered refresh. The count note was removed; live status remains in the
    session section, which is updated while Help stays open.

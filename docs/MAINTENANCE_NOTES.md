# Maintenance Notes

## Validation record

This document records what has and has not been verified. It replaces the
earlier maintenance note that hosted workflows had not been run.

### October 4, 2026: PR #2 and hosted CI

- Merged change: [PR #2](https://github.com/jundoopop/journalism-and-literacy-kor/pull/2)
- Hosted workflow: [GitHub Actions run #37233075554](https://github.com/jundoopop/journalism-and-literacy-kor/actions/runs/37233075554)
- Workflow conclusion: **success**

The workflow reported both jobs as successful:

| Job | Automated evidence established by the run |
|---|---|
| `regression` | Python tests passed and JavaScript Chrome extension tests passed. |
| `container` | Docker image build, service startup, health check, and service shutdown all passed. |

Accordingly, statements that the model-related changes had not been followed by
a test rerun, or that hosted CI and container verification had not occurred, are
historical and must not be presented as the current verification state for the
revision exercised by this workflow.

## Interpretation boundaries

A green hosted workflow confirms only the automated steps that the workflow ran.
It does not imply that tests requiring external credentials, mutable third-party
services, or human browser interaction were performed.

### Verified automatically

- Python regression behavior covered by the workflow's Python test command.
- JavaScript extension behavior covered by the workflow's extension test
  command.
- Ability to build the tested Docker image.
- Ability to start the tested service, pass the configured health check, and
  shut it down in the workflow environment.

### Still requires separate verification

- **Live LLM API connectivity:** run provider connection checks using dedicated,
  authorized test credentials.
- **Live analysis quality:** evaluate real provider responses against the
  benchmark and record model IDs, prompt versions, dataset version, date, and
  metrics. A successful mock or contract test is not a quality evaluation.
- **Manual Chrome acceptance:** load `chrome-ex/` as an unpacked extension and
  verify supported-site detection, automatic and manual highlighting, tooltip
  content, popup controls, provider settings, cache/re-analysis behavior, and
  backend-disconnected error states.
- **Live publisher crawling:** verify representative current URLs because page
  structure and anti-automation behavior can change independently of this
  repository.

## Required wording for future status updates

Use scoped statements:

- Good: “Python and JavaScript regression tests passed in GitHub Actions run
  #37233075554.”
- Good: “The container smoke test built, started, passed health checking, and
  stopped successfully in run #37233075554.”
- Good: “Live Gemini analysis was manually checked on YYYY-MM-DD using model X.”
- Avoid: “Everything is fully tested” when only CI regression jobs ran.
- Avoid: “The extension works in Chrome” unless a manual or browser-automation
  acceptance run was completed and recorded.

## Verification checklist for a release

### Automated

- [x] Python regression tests — run #37233075554 (2026-10-04)
- [x] JavaScript extension tests — run #37233075554 (2026-10-04)
- [x] Docker image build — run #37233075554 (2026-10-04)
- [x] Container start/health/stop smoke test — run #37233075554 (2026-10-04)

### External/manual

- [ ] Live provider connectivity with authorized test keys
- [ ] External LLM quality evaluation against the benchmark
- [ ] Manual Chrome extension acceptance on supported news sites
- [ ] Representative live crawler checks

When one of the unchecked items is completed, add the date, environment, exact
command or procedure, model/browser version, result, and a link to retained
evidence. Do not convert a checkbox based on inference from a different test.

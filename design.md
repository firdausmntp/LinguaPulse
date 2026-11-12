# LinguaPulse TOEFL EPT design system

Hallmark v2.0.0, retained brand. Cobalt, Familjen Grotesk headings, IBM Plex Sans body. Consume tokens in frontend/css/tokens.css. No emojis, gamification, tracked capital labels, eyebrow labels, fake metrics, decorative gradients, or mock browser frames.

2026-11-10 EPT revision: Listening, Structure and Reading are the three EPT modules. Writing and sentence rewriting support the research task; they do not produce an official TOEFL score.

Landing: Stage hero with large EPT heading on ink-blue surface, paired with a real screenshot of the listening workspace. White text uses hero tokens. A single random Structure sample is available without login, with green/red feedback and full-width explanation. Full exams remain on their own route. Three-module information switcher, learning modes, workflow, privacy, FAQ. Visual mass comes from the real product, type and material, not invented evidence. Keep route destinations and page IDs.

App pages: light neutral paper, white work surfaces, cobalt selected/action state, compact navy headers. Exam has four tab destinations (Listening, Structure, Reading, Writing riset), actual completion progress, question navigator and flag-for-review controls, audio in listening, per-passage reading, minimal task chrome. No decorative page-load animation in app views.

Admin custom questions: master/detail bank and form, friendly module names, dynamic options and answer select, preview before saving, audio URL/upload, import/export JSON, active/inactive management, duplicate action. Existing proctor and users tabs remain. Error/loading/empty/full states and visible keyboard focus required. Audio upload is admin-only.

Palette tokens added by root: --color-hero-bg, --color-hero-ink, --color-hero-muted, --color-hero-rule. Use all other existing tokens. New stylesheets start with Hallmark stamp and critique. Max 350 lines per code file. Keep controls responsive at 320/375px, respect reduced motion. One primary button recipe (btn-primary); use existing SVG helper (aria-hidden); any icon-only button needs accessible name. Actual viewport panels must fit mobile, not merely hide overflow.

Files: edit existing templates/CSS/JS in place; add modular helpers as needed; delete no routes. Preserve account sessions, draft restore, telemetry only while exam active, owner-only results. All saved question text must be escaped before rendering.

2026-11-11 workspace polish: Admin opens to an operational overview, with a white collapsible sidebar, actual counts, recent submissions, module readiness and task links. Detailed proctor inspection stays under Pengawasan; no live monitoring claim. Unsubmitted attempts count only while their deadline is valid and exclude completed submissions. User CRUD and question editor remain unchanged in capability.

Participant dashboard leads with two clear paths: untimed practice and a timed exam session. `/practice` is participant-only and loads one random active multiple-choice question at a time from Listening, Structure or Reading. Select, check, read explanation, next. Green marks the correct option; red marks an incorrect selection, with text labels too. Practice never starts a timer, writes exam history or enables research sensors. Desktop keeps context beside answers; mobile stacks them. Query parameter `module` preserves the selected module on refresh.

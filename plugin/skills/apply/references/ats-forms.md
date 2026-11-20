# ATS form notes

What each applicant tracking system does differently. Learned by filling real forms.

## General

- Read the whole form before filling: required fields, file inputs, knockout questions.
- Salary fields often reject text: type plain numbers (`22000`), put the currency where asked.
- Single-line inputs can have hidden length caps (Workable: 127 chars). Long answers go in
  textareas; check the field kept the whole text after typing.
- A form inside an iframe or shadow DOM may not show in `read_page`; use `find` or
  `javascript_tool` to locate inputs.
- Do not trigger browser dialogs (alert/confirm); they freeze the extension.
- https pages cannot fetch `http://localhost`, so the browser cannot read the local DB:
  run `jobradar` commands in the terminal instead.
- reCAPTCHA / hCaptcha: stop and hand the tab to the user. Never try to solve or bypass one.

## Workable (`apply.workable.com/<slug>/j/<id>`)

- Fields autosave; a reload keeps the draft.
- Find a company's open jobs without a browser:
  `POST https://apply.workable.com/api/v3/accounts/<slug>/jobs` with `{"query": "engineer"}`.
  The slug is in the company's careers link.
- Single-line answers are capped at 127 characters.

## Greenhouse (`boards.greenhouse.io` / `job-boards.greenhouse.io`)

- Resume: "Attach" opens a file input; `file_upload` on that input.
- Custom questions are plain selects and textareas; EEO section is optional ("Decline to
  self-identify" is fine unless `answers` says otherwise).

## Lever (`jobs.lever.co/<company>/<id>/apply`)

- Resume upload first: Lever parses it and pre-fills name/email/phone. Check what it filled.

## Ashby (`jobs.ashbyhq.com/<company>/<id>`)

- "Application" tab holds the form. Some fields are React comboboxes: type, then pick the option.
- Some forms ask for age, gender, marital status or personal essays: only from `answers`;
  otherwise ask the user.

## SmartRecruiters (`jobs.smartrecruiters.com/<company>/<id>`)

- The one-click form lives in shadow DOM. To upload the CV: with `javascript_tool`, move the
  file `<input type=file>` to `document.body` and give it an `aria-label`, `file_upload` to it
  by ref, then move it back.

## JazzHR (`<company>.applytojob.com/apply/<id>`)

- Salary fields take numbers only. Often has a reCAPTCHA at submit: hand to the user.

## BambooHR (`<company>.bamboohr.com/careers/<id>`)

- "Desired pay" is free text. reCAPTCHA is common at submit.

## Teamtailor (`careers.<company>.com/jobs/<id>`)

- Plain form; cover letter is a textarea or an optional file.

## Google Forms

- Each question is a separate block; required ones show an asterisk. File upload needs a
  Google sign-in: hand to the user if not signed in.

## Workday, SuccessFactors, Oracle HCM, Taleo, Darwinbox

- Need an account per company. Hand to the user; do not create accounts or passwords for them.

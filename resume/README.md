# Drop your baseline resume here

Put ONE file in this folder: `.pdf`, `.docx`, `.md`, or `.txt`.
The agent extracts its text and uses it as the baseline for every
tailored resume it generates.

Note: this folder is gitignored by default so your resume never leaves
your machine accidentally. For the deployed (GitHub Actions) version:

- **Private repo (simplest):** remove `resume/*` from `.gitignore` and commit the file.
- **Public repo:** keep it ignored and set the `RESUME_B64` + `RESUME_EXT`
  secrets instead (see `.env.example` for the PowerShell one-liner).

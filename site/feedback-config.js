/**
 * Where the contact page's feedback form signs people in and posts to.
 *
 * Both values are public, not secrets: a Google OAuth client ID is printed into
 * every page that shows a Google sign-in button, and the web app's address is
 * what any browser posting to it can see. Nothing here may ever hold a client
 * secret or a key — the form needs none, and tests/test_site_contact.py fails if
 * a value looks like one.
 *
 * While either is empty the page shows a notice instead of the form, and points
 * at GitHub and Facebook, which always work. The owner sets them up once with
 * tools/feedback/README.md:
 *   clientId — Google Cloud → APIs & Services → Credentials → OAuth client ID,
 *              shaped like 1234…-abc….apps.googleusercontent.com;
 *   endpoint — the Apps Script web app URL, shaped like
 *              https://script.google.com/macros/s/…/exec.
 */
export const FEEDBACK = { clientId: "", endpoint: "" };

/**
 * FishBytes Waitlist — Google Apps Script webhook
 * ─────────────────────────────────────────────────
 *
 * SETUP (5 minutes)
 *
 * 1. Open Google Sheets and create a new sheet. Name the first tab "Waitlist".
 *    Add headers in row 1: timestamp | email | name | role | useCase | page | ua
 *    (or just leave row 1 blank — this script will write to whatever columns it has)
 *
 * 2. In the Sheet: Extensions → Apps Script. Delete the default Code.gs contents.
 *
 * 3. Paste THIS file's contents into Code.gs. Save (Ctrl/Cmd+S).
 *
 * 4. Deploy → New deployment → ⚙ (gear icon) → "Web app".
 *      - Description:   FishBytes waitlist intake
 *      - Execute as:    Me (your account)
 *      - Who has access:  Anyone               ← REQUIRED so the website can POST
 *      - Click "Deploy".
 *      - Authorize the script when prompted (Google will warn about an "unverified
 *        app" — click Advanced → Go to <name> (unsafe). It's your own script.)
 *
 * 5. Copy the "Web app URL" — it ends in /exec.
 *
 * 6. In index.html, find:    const WAITLIST_ENDPOINT = '';
 *    Paste the URL between the quotes. Save and redeploy your site.
 *
 * 7. Test it: fill the waitlist form on your site, then check the Sheet — a new
 *    row should appear within a couple seconds.
 *
 *
 * NOTES
 *
 * • The site posts JSON with mode: 'no-cors', which means it gets an opaque
 *   response. The script still writes the row; the browser just can't read the
 *   response body. This is fine — the form treats reachable endpoint as success.
 *
 * • If you ever change this script, you must Deploy → Manage deployments →
 *   pencil-icon → Version: New version → Deploy. The /exec URL stays the same.
 *
 * • The optional email-on-new-signup feature is at the bottom — uncomment and
 *   set NOTIFY_EMAIL to get a Gmail notification on every submission.
 */

const SHEET_NAME = 'Waitlist';
// const NOTIFY_EMAIL = 'you@example.com';   // uncomment + set to get emails

function doPost(e) {
  try {
    const data = JSON.parse(e.postData.contents || '{}');

    const ss = SpreadsheetApp.getActiveSpreadsheet();
    let sh = ss.getSheetByName(SHEET_NAME);
    if (!sh) {
      sh = ss.insertSheet(SHEET_NAME);
      sh.appendRow(['timestamp','email','name','role','useCase','page','ua']);
    }

    sh.appendRow([
      data.ts   || new Date().toISOString(),
      data.email || '',
      data.name  || '',
      data.role  || '',
      data.useCase || '',
      data.page  || '',
      data.ua    || ''
    ]);

    // Optional Gmail notification on every submission
    // if (typeof NOTIFY_EMAIL !== 'undefined' && NOTIFY_EMAIL) {
    //   MailApp.sendEmail({
    //     to: NOTIFY_EMAIL,
    //     subject: 'FishBytes waitlist: ' + (data.name || data.email),
    //     body: JSON.stringify(data, null, 2)
    //   });
    // }

    return ContentService
      .createTextOutput(JSON.stringify({ok: true}))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService
      .createTextOutput(JSON.stringify({ok: false, error: String(err)}))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

// Quick health check — open the /exec URL in a browser to verify it's live.
function doGet() {
  return ContentService
    .createTextOutput('FishBytes waitlist endpoint is alive. POST JSON to record a signup.')
    .setMimeType(ContentService.MimeType.TEXT);
}

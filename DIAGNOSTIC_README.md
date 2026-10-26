Replace only `engine.py` in your GitHub repository, then commit.

After Render redeploys:
1. Submit a brand-new review.
2. Open Case Details.
3. Look at **AI Decision Reason**.
   It will now show the exact Gemini HTTP status and message.
4. Render Logs will also contain a line starting with:
   `[Gemini HTTPError]`

This lets us distinguish invalid key/permission (401/403), malformed request (400),
quota/rate limit (429), and temporary overload (503).

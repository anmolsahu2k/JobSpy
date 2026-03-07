import csv
import os
import pandas as pd
from jobspy import scrape_jobs

# Handshake session cookies — copy from DevTools → Network → any /hs/graphql request → Cookie header
# These expire; refresh them when Handshake stops returning results
HANDSHAKE_COOKIES = (
    "ajs_anonymous_id=81495937-cabc-4213-87db-55f9d9169cd6; _ga=GA1.1.573941303.1758414905; "
    "__pdst=abea6695f5e948349d8c2fe9870d2989; _gd_visitor=465a52cd-ce64-4e8c-8135-fc4fb04dcfca; "
    "ajs_user_id=66264109; "
    "hss-global=eyJhbGciOiJkaXIiLCJjdHkiOiJKV1QiLCJlbmMiOiJBMjU2Q0JDLUhTNTEyIiwidHlwIjoiSldUIn0..FgEYPVhOqBrcgdGjG3O7sg.34ORJa8iVHUuJE6yqSKBh-gApWnLRuXHOnJ-tGFNF4ynDUMI-js_EWGhx8r0ATU1-1Mr3ZX5qA6eGDCpcAZdFsvlA9NcP2oSwIo43ydOzkl-X-eBYvposPmnkpPcxhTP7Xiy_1LwQQWJSx8afqKnyNIStUpT7zMcLFD9n0rGFZMlpp35QSLNe9j0MwqXKbLDL-ouB30ZYpe5GXpBPJR6ypWC18BU1xQXiCfCykKsFDZTEcfTSOdUEm7nuOLbpUfsYL-G9AwVHNFxjjeOMD_UZ-E4YBblAbqdoO95B12nAGVM9Z159wI2MA9HWxDYx4vaxAxRRhaxJutlxeSWzvTkLQelKSeE6bHO4kr6ptKUROXD4tCgurLtNGMlHMFvHeFh.LtAGaFOGhu-EecbKCe96CSuBR--jvRbJIfg4N8g46Qk; "
    "_trajectory_session=CGnflM4qihjzGxhZ7XwJcIFir4iuCuEQPB%2BkkTcQ4zrZ92h8WhJao%2Bw0KeM7vXi897nxM6x5gcgAUZbOstz%2Fzb8jb4uFDNnFJHYEXuOvEC1Ay%2FAMVKC3EpLgyUL5d%2F9hnQmV1aGgKcPS2s8hi9pMesg576MOXd3pnD6fX8eruix%2FdvfNP1x1JX0XQxO8wi03sZzaPFob%2FJbHESULr7y01%2B3I%2FVPX1HzqOgO7mEtr5QTBDxitDLLYa7y%2Fc0Z%2FLZB2bz2VnxICC6rRcQtSxSI0TlBM4dD7ykF1lwie1AUqj6ab90Z9yNI391sHRpxaJDyBYzLTBUKJwDX7Q6qhXxFO--KFqSdKQnl0IlDIgS--XiziK4DmlF65Kq7T6s3qxg%3D%3D"
)

jobs = scrape_jobs(
    site_name=["indeed", "linkedin", "glassdoor", "handshake"],  # google (bot detection) and zip_recruiter (expired token) excluded
    search_term="intern",
    google_search_term="software engineer jobs near San Francisco, CA since yesterday",
    location="San Francisco, CA",
    results_wanted=20,
    hours_old=168,  # 1 week — widened to get more results
    country_indeed="USA",
    verbose=2,  # 0=errors only, 1=warnings, 2=all logs
    handshake_cookies=HANDSHAKE_COOKIES,
    # linkedin_fetch_description=True,  # slower but gets full description + direct URL
    # proxies=["user:pass@host:port", "localhost"],
)

print(f"Found {len(jobs)} jobs")
print(jobs[["site", "title", "company", "location", "job_url"]].head(10))

output_file = "jobs.csv"
if os.path.isfile(output_file):
    existing = pd.read_csv(output_file)
    new_jobs = jobs[~jobs["job_url"].isin(existing["job_url"])]
    new_jobs.to_csv(output_file, mode="a", header=False, quoting=csv.QUOTE_NONNUMERIC, escapechar="\\", index=False)
    print(f"Appended {len(new_jobs)} new jobs ({len(jobs) - len(new_jobs)} duplicates skipped) to {output_file}")
else:
    jobs.to_csv(output_file, quoting=csv.QUOTE_NONNUMERIC, escapechar="\\", index=False)
    print(f"Saved {len(jobs)} jobs to {output_file}")

import csv
import os
import pandas as pd
from jobspy import scrape_jobs

jobs = scrape_jobs(
    site_name=["indeed", "linkedin", "glassdoor"],  # google (bot detection) and zip_recruiter (expired token) excluded
    search_term="intern",
    google_search_term="software engineer jobs near San Francisco, CA since yesterday",
    location="San Francisco, CA",
    results_wanted=20,
    hours_old=168,  # 1 week — widened to get more results
    country_indeed="USA",
    verbose=2,  # 0=errors only, 1=warnings, 2=all logs
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

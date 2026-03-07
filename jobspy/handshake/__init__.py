from __future__ import annotations

import json
import math
import random
import time
from typing import Optional

from bs4 import BeautifulSoup

from jobspy.handshake.constant import (
    BASE_URL,
    GRAPHQL_URL,
    JOB_SEARCH_PAGE,
    JOB_SEARCH_QUERY,
    HANDSHAKE_JOB_TYPE_IDS,
    page_headers,
    graphql_headers,
)
from jobspy.handshake.util import (
    offset_to_cursor,
    decode_relay_id,
    parse_location,
    parse_date,
    parse_job_type,
    parse_compensation,
    is_job_remote,
)
from jobspy.model import (
    JobPost,
    JobResponse,
    Scraper,
    ScraperInput,
    Site,
    DescriptionFormat,
)
from jobspy.util import (
    extract_emails_from_text,
    create_session,
    create_logger,
    markdown_converter,
    plain_converter,
)

log = create_logger("Handshake")


class Handshake(Scraper):
    base_url = BASE_URL
    jobs_per_page = 25
    delay = 2
    band_delay = 3

    def __init__(
        self,
        proxies: list[str] | str | None = None,
        ca_cert: str | None = None,
        user_agent: str | None = None,
        cookies: dict | str | None = None,
    ):
        super().__init__(Site.HANDSHAKE, proxies=proxies, ca_cert=ca_cert)
        self.session = create_session(
            proxies=self.proxies,
            ca_cert=ca_cert,
            is_tls=False,
            has_retry=True,
            delay=5,
            clear_cookies=False,
        )
        self.session.headers.update(page_headers)
        if user_agent:
            self.session.headers["User-Agent"] = user_agent

        if isinstance(cookies, dict):
            self.session.cookies.update(cookies)
        elif isinstance(cookies, str):
            for part in cookies.split(";"):
                part = part.strip()
                if "=" in part:
                    k, _, v = part.partition("=")
                    self.session.cookies.set(k.strip(), v.strip())

        self.scraper_input = None

    def _get_csrf_token(self) -> str | None:
        """Fetch the CSRF token from the job-search HTML page."""
        try:
            resp = self.session.get(JOB_SEARCH_PAGE, timeout=30)
            soup = BeautifulSoup(resp.text, "html.parser")
            for name in ("csrf-token", "token"):
                meta = soup.find("meta", attrs={"name": name})
                if meta and meta.get("content"):
                    return meta["content"]
        except Exception as e:
            log.warning(f"Handshake: could not fetch CSRF token: {e}")
        return None

    def scrape(self, scraper_input: ScraperInput) -> JobResponse:
        self.scraper_input = scraper_input
        job_list: list[JobPost] = []
        seen_ids = set()
        page = 1

        csrf_token = self._get_csrf_token()
        if not csrf_token:
            log.error(
                "Handshake: could not obtain CSRF token. "
                "Provide valid session cookies via handshake_cookies= in scrape_jobs(). "
                "Copy them from DevTools → Network → any /hs/graphql request → Cookie header."
            )
            return JobResponse(jobs=job_list)

        req_headers = {**graphql_headers, "X-CSRF-Token": csrf_token}

        continue_search = lambda: len(job_list) < scraper_input.results_wanted

        while continue_search():
            offset = (page - 1) * self.jobs_per_page
            log.info(
                f"search page: {page} / {math.ceil(scraper_input.results_wanted / self.jobs_per_page)}"
            )

            filter_input: dict = {}
            if scraper_input.search_term:
                filter_input["query"] = scraper_input.search_term
            if scraper_input.job_type:
                aliases = scraper_input.job_type.value  # tuple of alias strings
                job_type_ids = [
                    HANDSHAKE_JOB_TYPE_IDS[alias]
                    for alias in aliases
                    if alias in HANDSHAKE_JOB_TYPE_IDS
                ]
                if job_type_ids:
                    filter_input["jobTypeIds"] = job_type_ids

            variables: dict = {
                "first": self.jobs_per_page,
                "after": offset_to_cursor(offset),
                "input": {
                    "filter": filter_input,
                    "sort": {"direction": "ASC", "field": "RELEVANCE"},
                    "channel": "NL_SEARCH_CHANNEL",
                },
            }

            payload = {
                "operationName": "JobSearchQuery",
                "variables": variables,
                "query": JOB_SEARCH_QUERY,
            }

            try:
                response = self.session.post(
                    GRAPHQL_URL,
                    json=payload,
                    headers=req_headers,
                    timeout=scraper_input.request_timeout,
                )
            except Exception as e:
                log.error(f"Handshake: request failed: {e}")
                return JobResponse(jobs=job_list)

            if response.status_code in (401, 403):
                log.error(
                    "Handshake: authentication failed. "
                    "Provide fresh session cookies via handshake_cookies= in scrape_jobs()."
                )
                return JobResponse(jobs=job_list)

            if response.status_code not in range(200, 400):
                log.error(f"Handshake response {response.status_code}: {response.text[:300]}")
                return JobResponse(jobs=job_list)

            try:
                data = response.json()
            except Exception:
                log.error(f"Handshake: failed to parse JSON. Response: {response.text[:300]}")
                return JobResponse(jobs=job_list)

            if "errors" in data:
                log.error(f"Handshake GraphQL errors:\n{json.dumps(data['errors'], indent=2)}")
                return JobResponse(jobs=job_list)

            job_search = (data.get("data") or {}).get("jobSearch") or {}
            edges = job_search.get("edges") or []

            if not edges:
                log.info("No more job listings found")
                break

            for edge in edges:
                node = edge.get("node") or {}
                job = node.get("job") or {}
                if not job:
                    continue
                job_post = self._process_job(job)
                if job_post and job_post.id not in seen_ids:
                    seen_ids.add(job_post.id)
                    job_list.append(job_post)
                    if not continue_search():
                        break

            if continue_search():
                time.sleep(random.uniform(self.delay, self.delay + self.band_delay))
                page += 1

        return JobResponse(jobs=job_list[: scraper_input.results_wanted])

    def _process_job(self, job: dict) -> Optional[JobPost]:
        try:
            relay_id = job.get("id", "")
            job_int_id = decode_relay_id(relay_id)

            title = job.get("title") or "N/A"

            employer = job.get("employer") or {}
            company_name = employer.get("name") or "N/A"
            logo = employer.get("logo") or {}
            company_logo = logo.get("url") or None

            # Location — use first location in array
            locations = job.get("locations") or []
            location = parse_location(locations[0] if locations else None)

            date_posted = parse_date(job.get("createdAt") or job.get("applyStart"))

            job_url = f"{self.base_url}/job-search/{job_int_id}"

            job_type = parse_job_type(job.get("jobType"))
            compensation = parse_compensation(job.get("salaryRange"))

            description_raw = job.get("description") or ""
            description = self._format_description(description_raw)

            remote = is_job_remote(
                remote=job.get("remote"),
                hybrid=job.get("hybrid"),
                title=title,
                description=description,
            )

            return JobPost(
                id=f"hs-{job_int_id}",
                title=title,
                company_name=company_name,
                company_logo=company_logo,
                location=location,
                is_remote=remote,
                date_posted=date_posted,
                job_url=job_url,
                job_type=job_type,
                compensation=compensation,
                description=description,
                emails=extract_emails_from_text(description),
                company_industry=(employer.get("industry") or {}).get("name"),
            )
        except Exception as e:
            log.error(f"Handshake: error processing job: {e}")
            return None

    def _format_description(self, raw: str) -> str | None:
        if not raw:
            return None
        if self.scraper_input and self.scraper_input.description_format == DescriptionFormat.MARKDOWN:
            return markdown_converter(raw)
        if self.scraper_input and self.scraper_input.description_format == DescriptionFormat.PLAIN:
            return plain_converter(raw)
        return raw

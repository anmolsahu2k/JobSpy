# Handshake job type IDs — verify by inspecting jobType.id in GraphQL responses
# Common mapping based on Handshake's platform (adjust if IDs differ in your region/account)
HANDSHAKE_JOB_TYPE_IDS = {
    "fulltime": "1",
    "parttime": "2",
    "internship": "3",
    "coop": "4",
    "oncampus": "5",
    "fellowship": "6",
    "volunteer": "7",
    "other": "8",
    "contract": "9",
}

BASE_URL = "https://app.joinhandshake.com"
GRAPHQL_URL = f"{BASE_URL}/hs/graphql"
JOB_SEARCH_PAGE = f"{BASE_URL}/job-search"

page_headers = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
}

graphql_headers = {
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
    "apollographql-client-name": "consumer",
    "apollographql-client-version": "1.2",
    "graphql-operation-type": "query",
    "Origin": BASE_URL,
    "Referer": f"{BASE_URL}/job-search",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "DNT": "1",
}

# Exact GraphQL query from Handshake's consumer client
JOB_SEARCH_QUERY = """
query JobSearchQuery($first: Int, $after: String, $input: JobSearchInput) {
  jobSearch(first: $first, after: $after, input: $input) {
    totalCount
    searchId
    edges {
      node {
        id
        job {
          id
          title
          createdAt
          description
          remote
          onSite
          hybrid
          workLocationType
          applyStart
          locations {
            id
            city
            state
            country
            displayName
          }
          jobType {
            id
            name
            behaviorIdentifier
          }
          employmentType {
            id
            name
            behaviorIdentifier
          }
          salaryRange {
            id
            min
            max
            currency
            paySchedule {
              id
              behaviorIdentifier
              friendlyName
            }
          }
          salaryType {
            id
            name
            behaviorIdentifier
          }
          employer {
            id
            name
            logo {
              url(size: "small")
            }
            industry {
              id
              name
            }
          }
        }
      }
    }
  }
}
""".strip()

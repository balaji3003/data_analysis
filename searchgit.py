import requests
import pandas as pd
import time

def fetch_github_repositories(query, max_pages=20, per_page=100):
    """
    Fetches GitHub repositories based on a given query.
    
    Parameters:
        query (str): GitHub search query string.
        max_pages (int): Maximum number of pages to fetch.
        per_page (int): Number of results per page (max 100).
    
    Returns:
        pd.DataFrame: DataFrame containing repository details.
    """
    headers = {
        "Accept": "application/vnd.github+json"
    }

    base_url = f"https://api.github.com/search/repositories?q={query}&sort=stars&order=desc"
    all_repositories = []
    current_page = 1

    while current_page <= max_pages:
        print(f"Fetching page {current_page}...")

        # Construct full URL with pagination
        url = f"{base_url}&per_page={per_page}&page={current_page}"

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            repos = data.get("items", [])

            if not repos:  # Stop if no more results
                break

            for repo in repos:
                all_repositories.append({
                    "Name": repo["name"],
                    "Owner": repo["owner"]["login"],
                    "Stars": repo["stargazers_count"],
                    "Forks": repo["forks_count"],
                    "Last Updated": repo["pushed_at"],
                    "License": repo["license"]["name"] if repo["license"] else "N/A",
                    "URL": repo["html_url"]
                })

            current_page += 1  # Move to next page
            time.sleep(1)  # Avoid hitting GitHub rate limits

        elif response.status_code == 403 and "X-RateLimit-Reset" in response.headers:
            reset_time = int(response.headers["X-RateLimit-Reset"])
            wait_time = reset_time - int(time.time())

            if wait_time > 0:
                print(f"⚠️ API rate limit exceeded. Waiting {wait_time} seconds before retrying...")
                time.sleep(wait_time + 1)  # Wait until reset
            else:
                print("⚠️ API rate limit exceeded but reset time already passed. Retrying now...")

        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
            break  # Stop fetching if another error occurs

    # Convert to DataFrame
    df = pd.DataFrame(all_repositories)
    return df


# ✅ **Calling the function with a specific search query**
query = "language:python+stars:>100+forks:>20+pushed:>2024-01-01"
df_results = fetch_github_repositories(query)

# Save results
df_results.to_csv("github_java_repositories_functionss.csv", index=False)
print(f"✅ Data saved to github_java_repositories_functionss.csv with {len(df_results)} results")


  # THIS IS THE WORKING SCRIPT THAT EXTRACTS LIST OF FILES TO SEARCH
  
import json
import re
from collections import defaultdict
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
from git import Repo
import os

# Configuration
REPO_PATH = '.'  # Path to the repository

# Patterns and Keywords
TEST_FILE_PATTERN = re.compile(r'(tests?/|_test\.py|test_.*\.py|\.spec\.js$|\.test\.js$|Test\.java$)', re.I)
CI_PATTERN = re.compile(r'\.github/workflows/|\.gitlab-ci\.yml|\.travis\.yml|Jenkinsfile', re.I)
TEST_KEYWORDS = ["assert", "pytest", "@pytest.mark", "self.assert", "@Test", "mock", "TestCase"]


# Load commits from JSON
def load_commits(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


# Check if file matches test patterns
def is_test_file(filepath):
    return TEST_FILE_PATTERN.search(filepath) or CI_PATTERN.search(filepath)


# Check file content for automated test keywords
def has_test_keywords(repo, commit_hash, filepath):
    try:
        content = repo.git.show(f'{commit_hash}:{filepath}')
        return any(kw.lower() in content.lower() for kw in TEST_KEYWORDS)
    except Exception:
        return False


# Analysis function
def analyze_commits(commits, repo, json_file_name):
    total = len(commits)
    print(f"\n🚀 Analyzing total commits: {total}")
    results = defaultdict(lambda: {
        'test_commits': 0,
        'total_commits': 0,
        'test_files_modified': 0,
        'keyword_hits': 0,
        'keywords_found': set()
    })

    for idx, commit in enumerate(commits, start=1):
        date = datetime.strptime(commit['authorDate'], '%Y-%m-%dT%H:%M:%SZ').strftime('%Y-%m')
        results[date]['total_commits'] += 1
        is_test_related = False
        keyword_hit = False

        for fileChange in commit['fileChanges']:
            file_path = fileChange['file']
            if is_test_file(file_path):
                is_test_related = True
                results[date]['test_files_modified'] += 1
            if has_test_keywords(repo, commit['id'], file_path):
                keyword_hit = True
                results[date]['keywords_found'].add(file_path)

        if is_test_related or keyword_hit:
            results[date]['test_commits'] += 1
        if keyword_hit:
            results[date]['keyword_hits'] += 1

        # ✅ Print progress every 10 commits and at the end explicitly
        if idx % 10 == 0 or idx == total:
            percent_complete = (idx / total) * 100
            print(f"Processed commit {idx}/{total} ({percent_complete:.1f}% complete...)")

    # Prepare final detailed dictionary for JSON output
    analysis_details = {
        month: {
            "test_commit_percentage": round(data['test_commits'] / data['total_commits'] * 100, 2) if data[
                'total_commits'] else 0,
            "test_commits": data['test_commits'],
            "total_commits": data['total_commits'],
            "test_files_modified": data['test_files_modified'],
            "keyword_hits": data['keyword_hits'],
            "test_related_files": list(data['keywords_found'])
        }
        for month, data in results.items()
    }

    # Save results to a file named after the input JSON
    output_json_filename = f"automated_testing_longitudinal_analysis_{json_file_name.replace('.json', '')}.json"
    with open(output_json_filename, 'w', encoding='utf-8') as out_file:
        json.dump(analysis_details, out_file, indent=4)

    print(f"\n✅ Analysis complete. Results written to '{output_json_filename}'.")

    # Generate plots and save them as images named after the input JSON
    visualize_results(analysis_details, json_file_name.replace('.json', ''))

    return analysis_details


def visualize_results(analysis, base_name):
    # Convert the analysis dictionary to a DataFrame for visualization
    df = pd.DataFrame.from_dict(analysis, orient='index').sort_index()

    # Fill NaN values with 0 (in case of missing data for any month)
    df.fillna(0, inplace=True)

    # Plot 1: Test-Related Commits vs Total Commits
    ax = df[['test_commits', 'total_commits']].plot(kind='bar', figsize=(14, 8), alpha=0.8)
    plt.title(f"Monthly Automated Testing Commits vs Total Commits - {base_name}")
    plt.ylabel("Number of Commits")
    plt.xlabel("Month")
    plt.xticks(rotation=45)
    plt.grid(axis='y')
    plt.tight_layout()
    ax.get_figure().savefig(f"monthly_commits_vs_total_commits_{base_name}.png")
    plt.close()

    # Plot 2: Test Commit Percentage Over Time
    ax = df['test_commit_percentage'].plot(kind='line', figsize=(14, 8), marker='o', color='b', linewidth=2)
    plt.title(f"Percentage of Test-Related Commits Over Time - {base_name}")
    plt.ylabel("Test Commit Percentage (%)")
    plt.xlabel("Month")
    plt.xticks(rotation=45)
    plt.grid()
    plt.tight_layout()
    ax.get_figure().savefig(f"test_commit_percentage_over_time_{base_name}.png")
    plt.close()

    # Plot 3: Test Activity - Files Modified and Keyword Hits
    ax = df[['test_files_modified', 'keyword_hits']].plot(kind='bar', figsize=(14, 8), alpha=0.8)
    plt.title(f"Test Adoption: Test Files Modified and Keyword Hits - {base_name}")
    plt.ylabel("Count")
    plt.xlabel("Month")
    plt.xticks(rotation=45)
    plt.grid(axis='y')
    plt.tight_layout()
    ax.get_figure().savefig(f"test_files_and_keyword_hits_{base_name}.png")
    plt.close()

    # Plot 4: Highlight keyword usage trends over time
    ax = df['keyword_hits'].plot(kind='line', figsize=(14, 8), marker='o', color='g', linewidth=2)
    plt.title(f"Growth in Testing Framework and Tool Usage (Keyword Hits) - {base_name}")
    plt.ylabel("Number of Keyword Hits")
    plt.xlabel("Month")
    plt.xticks(rotation=45)
    plt.grid()
    plt.tight_layout()
    ax.get_figure().savefig(f"keyword_hits_trends_{base_name}.png")
    plt.close()

    print(f"\n📊 Visualization complete. Plots saved as images named after {base_name}.")


# Main execution: Hardcoded processing of multiple JSON files
if __name__ == "__main__":
    repo = Repo(REPO_PATH)
    json_files = [
        'interviews.json', 'jadx.json', 'Java.json', 'java-design-patterns.json', 'JavaGuide.json',
        'LeetCodeAnimation.json', 'mall.json', 'octocat_Hello-World.json', 'RxJava.json',
        'spring-boot.json', 'spring-framework.json', 'Stirling-PDF.json', 'guava.json', 'hello-algo.json'
    ]  # Hardcoded list of JSON files to process

    for json_file in json_files:
        print(f"\n📂 Processing file: {json_file}")
        if not os.path.exists(json_file):
            print(f"❌ File '{json_file}' not found, skipping...")
            continue

        try:
            commits = load_commits(json_file)
            analyze_commits(commits, repo, json_file)
            print(f"✅ Successfully analyzed {json_file}")
        except Exception as e:
            print(f"❌ Error processing '{json_file}': {e}")

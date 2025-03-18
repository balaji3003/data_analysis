import os
import subprocess
import json
import re
import shutil
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

from collections import defaultdict

# Function to get a valid GitHub repository URL
def get_valid_repo_url():
    while True:
        repo_url = input("Enter GitHub repository URL: ").strip()
        if re.match(r"^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/?$", repo_url):
            return repo_url
        print("Invalid URL format. Please enter a valid GitHub repository URL.")

# Function to clone or update GitHub repository
def clone_or_update_repo(repo_url):
    repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
    
    if os.path.exists(repo_name):
        print(f"Updating existing repository: {repo_name}")
        subprocess.run(["git", "-C", repo_name, "pull"], check=True)
    else:
        print(f"Cloning repository: {repo_url}")
        subprocess.run(["git", "clone", repo_url], check=True)
    
    return repo_name

# Function to extract Git history (Only New Commits) and update JSON file
def extract_git_history(repo_name):
    json_dir = os.path.join(repo_name, "git_analysis")  # Store JSONs inside a separate folder in the repo
    os.makedirs(json_dir, exist_ok=True)

    json_file = os.path.join(json_dir, "git_history.json")

    # Check if JSON file exists
    if os.path.exists(json_file):
        with open(json_file, "r", encoding="utf-8") as file:
            existing_data = json.load(file)
        existing_commits = {commit["commit_hash"] for commit in existing_data}
    else:
        existing_data = []
        existing_commits = set()

    log_file = os.path.join(json_dir, "git_history.log")
    
    # Extract Git history limited to last 10 years
    cmd = f"git -C {repo_name} log --since='10 years ago' --numstat --date=iso --pretty=format:'%H|%an|%ae|%ad|%s' --shortstat"
    with open(log_file, "w", encoding="utf-8") as file:
        subprocess.run(cmd, shell=True, stdout=file)

    # Parse and store data
    with open(log_file, "r", encoding="utf-8") as file:
        log_data = file.read().split("\n\n")

    new_commits = []
    for entry in log_data:
        lines = entry.split("\n")
        if len(lines) < 2:
            continue

        commit_info = lines[0].split("|")
        if len(commit_info) < 5:
            continue  

        commit_hash, author_name, author_email, commit_date, commit_message = commit_info[:5]

        # Skip existing commits
        if commit_hash in existing_commits:
            continue

        commit_entry = {
            "commit_hash": commit_hash,
            "author": {"name": author_name, "email": author_email},
            "date": commit_date,
            "message": commit_message,
            "file_changes": []
        }

        # Extract file changes
        for line in lines[1:]:
            match = re.match(r"(\d+|-)\s+(\d+|-)\s+(.+)", line)
            if match:
                lines_added = int(match.group(1)) if match.group(1) != "-" else 0
                lines_deleted = int(match.group(2)) if match.group(2) != "-" else 0
                filename = match.group(3)
                commit_entry["file_changes"].append({
                    "filename": filename,
                    "lines_added": lines_added,
                    "lines_deleted": lines_deleted
                })

        new_commits.append(commit_entry)

    # Merge new commits with existing data
    updated_data = new_commits + existing_data  

    # Save updated JSON
    with open(json_file, "w", encoding="utf-8") as file:
        json.dump(updated_data, file, indent=4)

    print(f"Git data saved in: {json_file} ({len(new_commits)} new commits added)")
    
    return json_file, json_dir

# Function to analyze commit history
# Function to analyze commit history
def analyze_commit_history(json_file, repo_name):
    with open(json_file, "r", encoding="utf-8") as file:
        git_data = json.load(file)

    df_commits = pd.DataFrame([
        {"commit_hash": commit["commit_hash"], "author": commit["author"]["name"], "date": commit["date"], "message": commit["message"]}
        for commit in git_data
    ])

    df_commits["date"] = pd.to_datetime(df_commits["date"], utc=True, errors="coerce")
    df_commits = df_commits.dropna(subset=["date"])
    df_commits.set_index("date", inplace=True)

    commit_frequency = df_commits.resample("W").size()
    commit_frequency_dict = {str(k): v for k, v in commit_frequency.items()}

    save_analysis_results(repo_name, "commit_frequency.json", commit_frequency_dict)

    return commit_frequency

# Function to analyze most changed files (Code Churn)
def analyze_code_churn(json_file, repo_name):
    with open(json_file, "r", encoding="utf-8") as file:
        git_data = json.load(file)

    file_churn = defaultdict(lambda: {"added": 0, "deleted": 0})
    for commit in git_data:
        for file_change in commit["file_changes"]:
            file_churn[file_change["filename"]]["added"] += file_change["lines_added"]
            file_churn[file_change["filename"]]["deleted"] += file_change["lines_deleted"]

    churn_data = dict(file_churn)
    save_analysis_results(repo_name, "code_churn.json", churn_data)

    df_churn = pd.DataFrame.from_dict(churn_data, orient="index")
    df_churn["total_changes"] = df_churn["added"] + df_churn["deleted"]
    df_churn = df_churn.sort_values(by="total_changes", ascending=False).head(10)

    return df_churn

# Function to analyze bug-prone files
def analyze_bug_prone_files(json_file, repo_name):
    with open(json_file, "r", encoding="utf-8") as file:
        git_data = json.load(file)

    bug_fixes = defaultdict(int)
    for commit in git_data:
        if "fix" in commit["message"].lower():
            for file_change in commit["file_changes"]:
                bug_fixes[file_change["filename"]] += 1

    save_analysis_results(repo_name, "bug_prone_files.json", bug_fixes)

    df_bugs = pd.DataFrame.from_dict(bug_fixes, orient="index", columns=["bug_fixes"])
    df_bugs = df_bugs.sort_values(by="bug_fixes", ascending=False).head(10)

    return df_bugs

# Function to analyze top contributors
def analyze_top_contributors(json_file, repo_name):
    with open(json_file, "r", encoding="utf-8") as file:
        git_data = json.load(file)

    author_commits = defaultdict(int)
    for commit in git_data:
        author_commits[commit["author"]["name"]] += 1

    save_analysis_results(repo_name, "top_contributors.json", author_commits)

    df_contributors = pd.DataFrame.from_dict(author_commits, orient="index", columns=["commit_count"])
    df_contributors = df_contributors.sort_values(by="commit_count", ascending=False).head(10)

    return df_contributors

# Function to plot all graphs at once
def plot_all_graphs(commit_frequency, df_churn, df_bugs, df_contributors):
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))

    # Commit Frequency
    sns.lineplot(ax=axes[0, 0], x=commit_frequency.index, y=commit_frequency.values, marker='o')
    axes[0, 0].set_title("Commit Frequency Over Time (Last 10 Years)")
    axes[0, 0].set_ylabel("Commits per Week")
    axes[0, 0].set_xlabel("Year")
    axes[0, 0].grid()

    # Code Churn
    df_churn_melted = df_churn.reset_index().melt(id_vars="index", value_vars=["added", "deleted"])
    sns.barplot(ax=axes[0, 1], x="index", y="value", hue="variable", data=df_churn_melted)
    axes[0, 1].set_xticklabels(axes[0, 1].get_xticklabels(), rotation=45, ha="right")
    axes[0, 1].set_title("Top 10 Most Changed Files (Last 10 Years)")
    axes[0, 1].set_ylabel("Lines Changed")
    axes[0, 1].set_xlabel("File Name")
    axes[0, 1].legend(["Added", "Deleted"])
    axes[0, 1].grid()

    # Bug-Prone Files
    sns.barplot(ax=axes[1, 0], x=df_bugs.index, y=df_bugs["bug_fixes"], color="red")
    axes[1, 0].set_xticklabels(axes[1, 0].get_xticklabels(), rotation=45, ha="right")
    axes[1, 0].set_title("Top 10 Bug-Prone Files (Last 10 Years)")
    axes[1, 0].set_ylabel("Bug Fixes")
    axes[1, 0].set_xlabel("File Name")
    axes[1, 0].grid()

    # Top Contributors
    sns.barplot(ax=axes[1, 1], x=df_contributors.index, y=df_contributors["commit_count"], color="green")
    axes[1, 1].set_xticklabels(axes[1, 1].get_xticklabels(), rotation=45, ha="right")
    axes[1, 1].set_title("Top 10 Contributors (Last 10 Years)")
    axes[1, 1].set_ylabel("Commit Count")
    axes[1, 1].set_xlabel("Contributor")
    axes[1, 1].grid()

    plt.tight_layout()
    plt.show()
   

# Function to store analysis results in JSON files
def save_analysis_results(repo_name, filename, data):
    json_dir = os.path.join(repo_name, "git_analysis")
    os.makedirs(json_dir, exist_ok=True)

    file_path = os.path.join(json_dir, filename)
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)
    print(f"Analysis saved: {file_path}")



# Main execution
if __name__ == "__main__":
    repo_url = input("Enter GitHub repository URL: ")
    repo_name = clone_or_update_repo(repo_url)
    json_file, repo_name = extract_git_history(repo_name)

    print("\nPerforming Analysis...\n")
    commit_frequency = analyze_commit_history(json_file, repo_name)
    df_churn = analyze_code_churn(json_file, repo_name)
    df_bugs = analyze_bug_prone_files(json_file, repo_name)
    df_contributors = analyze_top_contributors(json_file, repo_name)
    
    plot_all_graphs(commit_frequency, df_churn, df_bugs, df_contributors)
    print("\nAnalysis Completed!")



#https://github.com/spring-projects/spring-boot
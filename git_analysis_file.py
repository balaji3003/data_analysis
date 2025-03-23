import os
import subprocess
import json
import re
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

from collections import defaultdict
from datetime import datetime, timedelta

# Try using newer or older PyDriller API
try:
    from pydriller import RepositoryMining
    use_new_api = True
except ImportError:
    from pydriller import Repository
    use_new_api = False

import lizard

# Clone or update GitHub repository
def clone_or_update_repo(repo_url):
    repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
    if os.path.exists(repo_name):
        print(f"Updating existing repository: {repo_name}")
        subprocess.run(["git", "-C", repo_name, "pull"], check=True)
    else:
        print(f"Cloning repository: {repo_url}")
        subprocess.run(["git", "clone", repo_url], check=True)
    return repo_name

# Extract Git history using PyDriller
def extract_git_history(repo_name):
    repo_path = os.path.join(os.getcwd(), repo_name)
    since = datetime.now() - timedelta(days=365 * 10)

    json_dir = os.path.join(repo_path, "git_analysis")
    os.makedirs(json_dir, exist_ok=True)
    json_file = os.path.join(json_dir, "git_history.json")

    if os.path.exists(json_file):
        with open(json_file, "r", encoding="utf-8") as f:
            existing_data = json.load(f)
        existing_commits = {c["commit_hash"] for c in existing_data}
    else:
        existing_data = []
        existing_commits = set()

    git_data = []
    commits = (
        RepositoryMining(path_to_repo=repo_path, since=since).traverse_commits()
        if use_new_api else
        Repository(path_to_repo=repo_path, since=since).traverse_commits()
    )

    for commit in commits:
        try:
            if not hasattr(commit, "modifications") or commit.modifications is None:
                continue
            if commit.hash in existing_commits:
                continue

            commit_entry = {
                "commit_hash": commit.hash,
                "author": {"name": commit.author.name, "email": commit.author.email},
                "date": commit.author_date.isoformat(),
                "message": commit.msg,
                "file_changes": []
            }

            for mod in commit.modifications:
                filename = mod.new_path or mod.old_path
                if filename:
                    commit_entry["file_changes"].append({
                        "filename": filename,
                        "lines_added": mod.added,
                        "lines_deleted": mod.removed
                    })

            git_data.append(commit_entry)
        except Exception as e:
            print(f"⚠️ Skipping commit {getattr(commit, 'hash', 'unknown')}: {e}")

    updated_data = git_data + existing_data
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(updated_data, f, indent=4)

    print(f"Git data saved in: {json_file} ({len(git_data)} new commits added)")
    return json_file, repo_name

# Commit history analysis
def analyze_commit_history(json_file, repo_name):
    with open(json_file, "r", encoding="utf-8") as file:
        git_data = json.load(file)

    df = pd.DataFrame([{"date": c["date"]} for c in git_data])
    df["date"] = pd.to_datetime(df["date"], utc=True, errors="coerce")
    df = df.dropna(subset=["date"])
    df.set_index("date", inplace=True)

    commit_freq = df.resample("W").size()
    commit_freq_dict = {str(k): int(v) for k, v in commit_freq.items()}

    save_analysis_results(repo_name, "commit_frequency.json", commit_freq_dict)
    return commit_freq

# Code churn analysis
def analyze_code_churn(json_file, repo_name):
    with open(json_file, "r", encoding="utf-8") as f:
        git_data = json.load(f)

    churn = defaultdict(lambda: {"added": 0, "deleted": 0})
    for c in git_data:
        for fc in c["file_changes"]:
            churn[fc["filename"]]["added"] += fc["lines_added"]
            churn[fc["filename"]]["deleted"] += fc["lines_deleted"]

    save_analysis_results(repo_name, "code_churn.json", churn)
    df = pd.DataFrame.from_dict(churn, orient="index")
    df["total_changes"] = df["added"] + df["deleted"]
    df = df.sort_values("total_changes", ascending=False).head(10)
    return df

# Bug-prone files analysis
def analyze_bug_prone_files(json_file, repo_name):
    with open(json_file, "r", encoding="utf-8") as f:
        git_data = json.load(f)

    bugs = defaultdict(int)
    for c in git_data:
        if "fix" in c["message"].lower():
            for fc in c["file_changes"]:
                bugs[fc["filename"]] += 1

    save_analysis_results(repo_name, "bug_prone_files.json", bugs)
    df = pd.DataFrame.from_dict(bugs, orient="index", columns=["bug_fixes"])
    return df.sort_values("bug_fixes", ascending=False).head(10)

# Top contributors analysis
def analyze_top_contributors(json_file, repo_name):
    with open(json_file, "r", encoding="utf-8") as f:
        git_data = json.load(f)

    contributors = defaultdict(int)
    for c in git_data:
        contributors[c["author"]["name"]] += 1

    save_analysis_results(repo_name, "top_contributors.json", contributors)
    df = pd.DataFrame.from_dict(contributors, orient="index", columns=["commit_count"])
    return df.sort_values("commit_count", ascending=False).head(10)

# Cyclomatic complexity analysis using lizard
# Cyclomatic complexity analysis using lizard
# Cyclomatic Complexity Analysis using lizard
# Cyclomatic Complexity Analysis using lizard
def analyze_cyclomatic_complexity(repo_name):
    # Collect all relevant source files
    source_files = []
    for root, _, files in os.walk(repo_name):
        for file in files:
            if file.endswith(('.py', '.java', '.js', '.cpp', '.c', '.cs', '.ts')):
                source_files.append(os.path.join(root, file))

    if not source_files:
        print("⚠️ No source files found for complexity analysis.")
        return pd.DataFrame()

    result = list(lizard.analyze_files(source_files))
    cc_scores = []

    for file_info in result:
        total_cc = sum(f.cyclomatic_complexity for f in file_info.function_list)
        cc_scores.append({
            "file": os.path.relpath(file_info.filename, repo_name),
            "complexity": total_cc
        })

    cc_df = pd.DataFrame(cc_scores)
    if not cc_df.empty:
        cc_df = cc_df.sort_values(by="complexity", ascending=False).head(10).set_index("file")
        save_analysis_results(repo_name, "cyclomatic_complexity.json", cc_df.to_dict())
    return cc_df



def analyze_loc(repo_name):
    output = subprocess.check_output(["cloc", repo_name, "--json"])
    cloc_data = json.loads(output.decode("utf-8"))
    save_analysis_results(repo_name, "loc.json", cloc_data)
    return cloc_data

# Additional: Maintainability Index using radon
def analyze_maintainability_index(repo_name):
    scores = {}
    for dirpath, _, files in os.walk(repo_name):
        for file in files:
            if file.endswith(".py"):
                full_path = os.path.join(dirpath, file)
                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        code = f.read()
                    mi = radon_mi.mi_visit(code, True)
                    scores[full_path] = mi
                except Exception:
                    continue
    save_analysis_results(repo_name, "maintainability_index.json", scores)
    return scores

# Additional: Developer ownership matrix
def analyze_developer_ownership(json_file, repo_name):
    with open(json_file, "r", encoding="utf-8") as f:
        git_data = json.load(f)

    ownership = defaultdict(lambda: defaultdict(int))
    for c in git_data:
        author = c["author"]["name"]
        for fc in c["file_changes"]:
            ownership[fc["filename"]][author] += 1

    save_analysis_results(repo_name, "ownership_matrix.json", ownership)
    return ownership

# Additional: Bug Density (bugs / LOC)
def analyze_bug_density(bugs_df, loc_data, repo_name):
    file_loc = {}
    for k, v in loc_data.get("files", {}).items():
        file_loc[k] = v.get("code", 0)

    density = {}
    for file in bugs_df.index:
        loc = file_loc.get(file, 1)
        bug_count = bugs_df.loc[file]["bug_fixes"]
        density[file] = bug_count / loc if loc else 0

    save_analysis_results(repo_name, "bug_density.json", density)
    return density

# Additional: Security Scan using bandit
def analyze_security_issues(repo_name):
    output = subprocess.getoutput(f"bandit -r {repo_name} -f json --quiet")
    try:
        result = json.loads(output)
        issues = result.get("results", [])
        save_analysis_results(repo_name, "security_scan.json", issues)
        return issues
    except Exception as e:
        print("Bandit output not valid JSON:", e)
        return []



# Save JSON results
def save_analysis_results(repo_name, filename, data):
    json_dir = os.path.join(repo_name, "git_analysis")
    os.makedirs(json_dir, exist_ok=True)
    path = os.path.join(json_dir, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    print(f"Analysis saved: {path}")

# Plotting
def plot_all_graphs(commit_freq, churn_df, bugs_df, contrib_df, cc_df,
                    loc_data, maintainability_data, bug_density_data, ownership_data, security_issues):
    fig, axes = plt.subplots(4, 2, figsize=(18, 18))

    # Commit Frequency
    sns.lineplot(ax=axes[0, 0], x=commit_freq.index, y=commit_freq.values, marker='o')
    axes[0, 0].set_title("Commit Frequency Over Time")
    axes[0, 0].grid()

    # Code Churn
    churn_melted = churn_df.reset_index().melt(id_vars="index", value_vars=["added", "deleted"])
    sns.barplot(ax=axes[0, 1], x="index", y="value", hue="variable", data=churn_melted)
    axes[0, 1].set_title("Top 10 Most Changed Files")
    axes[0, 1].set_xticklabels(axes[0, 1].get_xticklabels(), rotation=45, ha="right")

    # Bug-Prone Files
    sns.barplot(ax=axes[1, 0], x=bugs_df.index, y=bugs_df["bug_fixes"], color="red")
    axes[1, 0].set_title("Top Bug-Prone Files")
    axes[1, 0].set_xticklabels(axes[1, 0].get_xticklabels(), rotation=45, ha="right")

    # Top Contributors
    sns.barplot(ax=axes[1, 1], x=contrib_df.index, y=contrib_df["commit_count"], color="green")
    axes[1, 1].set_title("Top Contributors")
    axes[1, 1].set_xticklabels(axes[1, 1].get_xticklabels(), rotation=45, ha="right")

    # Cyclomatic Complexity
    sns.barplot(ax=axes[2, 0], x=cc_df.index, y=cc_df["complexity"], color="purple")
    axes[2, 0].set_title("Cyclomatic Complexity (Top 10 Files)")
    axes[2, 0].set_xticklabels(axes[2, 0].get_xticklabels(), rotation=45, ha="right")

    # LOC
    loc_df = pd.DataFrame.from_dict(loc_data.get("files", {}), orient="index")
    if "code" in loc_df.columns:
          loc_df = loc_df.sort_values("code", ascending=False).head(10)
    else:
          loc_df = pd.DataFrame(columns=["code"])  # fallback

    sns.barplot(ax=axes[2, 1], x=loc_df.index, y=loc_df["code"])
    axes[2, 1].set_title("Top 10 Files by LOC")
    axes[2, 1].tick_params(axis='x', rotation=45)

    # Maintainability Index
    mi_df = pd.DataFrame.from_dict(maintainability_data, orient="index", columns=["Maintainability Index"])
    mi_df = mi_df.sort_values("Maintainability Index", ascending=False).head(10)
    sns.barplot(ax=axes[3, 0], x=mi_df.index, y=mi_df["Maintainability Index"])
    axes[3, 0].set_title("Maintainability Index (Top 10 Files)")
    axes[3, 0].tick_params(axis='x', rotation=45)

    # Security Issues
    issues_df = pd.DataFrame(security_issues)
    if not issues_df.empty and "filename" in issues_df.columns:
        issue_count = issues_df["filename"].value_counts().head(10)
        sns.barplot(ax=axes[3, 1], x=issue_count.index, y=issue_count.values, color="darkorange")
        axes[3, 1].set_title("Security Issues by File")
        axes[3, 1].tick_params(axis='x', rotation=45)
    else:
        axes[3, 1].text(0.5, 0.5, "No security issues found", ha="center", va="center")

    plt.tight_layout()
    plt.show()

# Main
if __name__ == "__main__":
    repo_url = input("Enter GitHub repository URL: ").strip()
    repo_name = clone_or_update_repo(repo_url)
    json_file, repo_name = extract_git_history(repo_name)

    print("\nRunning Analysis...\n")
    commit_freq = analyze_commit_history(json_file, repo_name)
    churn_df = analyze_code_churn(json_file, repo_name)
    bugs_df = analyze_bug_prone_files(json_file, repo_name)
    contrib_df = analyze_top_contributors(json_file, repo_name)
    cc_df = analyze_cyclomatic_complexity(repo_name)
    loc_data = analyze_loc(repo_name)
    maintainability_data = analyze_maintainability_index(repo_name)
    ownership_data = analyze_developer_ownership(json_file, repo_name)
    bug_density_data = analyze_bug_density(bugs_df, loc_data, repo_name)
    security_issues = analyze_security_issues(repo_name)

    plot_all_graphs(commit_freq, churn_df, bugs_df, contrib_df, cc_df,
                    loc_data, maintainability_data, bug_density_data, ownership_data, security_issues)
    print("\n✅ Analysis Completed!")
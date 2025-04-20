import os
import tempfile
import subprocess
from git import Repo
from datetime import datetime, timedelta
import json
from urllib.parse import urlparse


def clone_repo_only_git(git_url, clone_path):
    print(f"Cloning only Git history from {git_url}...")
    subprocess.run(["git", "clone", "--mirror", git_url, clone_path], check=True)


def extract_commit_history(repo_path, git_url, output_path, years_back=10):
    print("Extracting commit history...")
    repo = Repo(repo_path)
    start_date = datetime.now() - timedelta(days=365 * years_back)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("[\n")
        first = True

        for commit in repo.iter_commits():
            commit_date = datetime.fromtimestamp(commit.committed_date)
            if commit_date < start_date:
                continue

            try:
                files_changed = commit.stats.files
                file_changes = []
                for file_path, change_info in files_changed.items():
                    lines_added = change_info.get('insertions', 0)
                    lines_deleted = change_info.get('deletions', 0)
                    change_type = "MODIFIED"
                    if lines_added > 0 and lines_deleted == 0:
                        change_type = "ADDED"
                    elif lines_deleted > 0 and lines_added == 0:
                        change_type = "DELETED"
                    file_changes.append({
                        "type": change_type,
                        "file": file_path
                    })
            except Exception:
                file_changes = []

            commit_info = {
                "id": commit.hexsha,
                "author": {
                    "identifier": commit.author.name,
                    "emailAddress": commit.author.email
                },
                "authorDate": datetime.fromtimestamp(commit.authored_date).isoformat() + "Z",
                "committer": {
                    "identifier": commit.committer.name,
                    "emailAddress": commit.committer.email
                },
                "committerDate": commit_date.isoformat() + "Z",
                "message": commit.message.strip(),
                "fileChanges": file_changes
            }

            if not first:
                f.write(",\n")
            else:
                first = False

            json.dump(commit_info, f, indent=2)

        f.write("\n]")

    print(f"✅ Commit history saved to {output_path}")


def extract_commit_history_from_url(git_url, output_path, years_back=10):
    # Use the current working directory for temporary storage
    current_dir = os.getcwd()  # Get the current working directory
    os.makedirs(current_dir, exist_ok=True)  # Ensure the directory exists (not strictly necessary)


    with tempfile.TemporaryDirectory(dir=current_dir) as tmpdir:
        clone_repo_only_git(git_url, tmpdir)
        extract_commit_history(tmpdir, git_url, output_path, years_back)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Extract Git commit history from a GitHub repo")
    parser.add_argument("--url", type=str, required=True, help="GitHub repository URL")
    parser.add_argument("--output", type=str, required=True, help="Path to save JSON output")
    parser.add_argument("--years-back", type=int, default=10, help="Years of commit history to include")

    args = parser.parse_args()
    extract_commit_history_from_url(args.url, args.output, years_back=args.years_back)


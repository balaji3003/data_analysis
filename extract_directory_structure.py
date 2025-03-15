import os
import json
import subprocess
import tempfile
import pandas as pd
from tqdm import tqdm

def delete_directory(directory):
    """Deletes a directory and its contents without using shutil."""
    for root, dirs, files in os.walk(directory, topdown=False):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"Failed to delete file {file_path}: {e}")
        for dir in dirs:
            dir_path = os.path.join(root, dir)
            try:
                os.rmdir(dir_path)
            except Exception as e:
                print(f"Failed to delete directory {dir_path}: {e}")
    try:
        os.rmdir(directory)
    except Exception as e:
        print(f"Failed to delete root directory {directory}: {e}")

def get_repo_structure(repo_url, repo_name):
    """Clones a GitHub repository, extracts its directory structure, and deletes it."""
    temp_dir = tempfile.mkdtemp()
    repo_path = os.path.join(temp_dir, repo_name)

    try:
        # Clone the repository
        subprocess.run(["git", "clone", "--depth", "1", repo_url, repo_path], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # Extract directory structure
        repo_structure = {}
        for root, dirs, files in os.walk(repo_path):
            rel_path = os.path.relpath(root, repo_path)
            repo_structure[rel_path] = {"directories": dirs, "files": files}

        return repo_structure

    except subprocess.CalledProcessError as e:
        print(f"Error cloning {repo_name}: {e}")
        return None

    finally:
        # Delete cloned repository
        delete_directory(repo_path)

def load_existing_json(output_json):
    """Loads existing JSON file to check processed repositories."""
    if os.path.exists(output_json):
        try:
            with open(output_json, "r", encoding="utf-8") as json_file:
                return json.load(json_file)
        except json.JSONDecodeError:
            print(f"Warning: {output_json} is corrupted. Starting fresh.")
            return []
    return []

def process_repositories(csv_file, output_json):
    """Reads a CSV file, processes each repository, and saves the directory structure incrementally to JSON."""
    try:
        # Read CSV
        df = pd.read_csv(csv_file)

        # Ensure required columns exist
        required_columns = {"Name", "Owner", "Stars", "Forks", "Last Updated", "License", "URL"}
        if not required_columns.issubset(df.columns):
            raise ValueError("CSV file is missing required columns.")

        # Load existing JSON data
        existing_data = load_existing_json(output_json)

        # Convert existing repository names to a set for quick lookup
        processed_repos = {repo["name"] for repo in existing_data}

        for _, row in tqdm(df.iterrows(), total=df.shape[0], desc="Processing repositories"):
            repo_name = row["Name"]
            repo_url = row["URL"] + ".git"

            # Skip if already processed
            if repo_name in processed_repos:
                print(f"Skipping {repo_name}, already processed.")
                continue

            # Get the directory structure
            structure = get_repo_structure(repo_url, repo_name)

            if structure:
                # Append new repository data to JSON
                new_repo_data = {
                    "name": repo_name,
                    "owner": row["Owner"],
                    "stars": row["Stars"],
                    "forks": row["Forks"],
                    "last_updated": row["Last Updated"],
                    "license": row["License"],
                    "url": row["URL"],
                    "directory_structure": structure
                }

                # Update JSON file immediately
                existing_data.append(new_repo_data)
                with open(output_json, "w", encoding="utf-8") as json_file:
                    json.dump(existing_data, json_file, indent=4)

                # Add to processed set to avoid duplicates in same run
                processed_repos.add(repo_name)

        print(f"Repository structures saved incrementally to {output_json}")

    except Exception as e:
        print(f"Error processing CSV: {e}")

# Example Usage:
# process_repositories("repositories.csv", "repositories_structure.json")


# Example Usage:
process_repositories("github_java_repositories_paginated.csv", "repositories_structure_output.json")

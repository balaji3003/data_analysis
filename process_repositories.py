import os
import json
from extract_commit_history import extract_commit_history_from_url

# Repositories data (as plain text)
repositories_text = """JavaGuide,Snailclimb,148647,45752,2025-03-11T11:44:19Z,Apache License 2.0,https://github.com/Snailclimb/JavaGuide
hello-algo,krahets,110015,13693,2025-03-11T08:56:34Z,Other,https://github.com/krahets/hello-algo
java-design-patterns,iluwatar,90978,26841,2025-03-11T19:47:43Z,Other,https://github.com/iluwatar/java-design-patterns
mall,macrozheng,79424,29074,2025-03-10T08:32:04Z,Apache License 2.0,https://github.com/macrozheng/mall
advanced-java,doocs,77213,19161,2025-03-10T22:25:04Z,Creative Commons Attribution Share Alike 4.0 International,https://github.com/doocs/advanced-java
spring-boot,spring-projects,76416,40982,2025-03-12T15:49:57Z,Apache License 2.0,https://github.com/spring-projects/spring-boot
LeetCodeAnimation,MisterBooo,75759,13980,2023-08-14T12:14:01Z,N/A,https://github.com/MisterBooo/LeetCodeAnimation
elasticsearch,elastic,71958,25121,2025-03-12T19:01:42Z,Other,https://github.com/elastic/elasticsearch
interviews,kdn251,64008,12916,2024-05-13T08:48:36Z,MIT License,https://github.com/kdn251/interviews
Java,TheAlgorithms,61053,19732,2025-03-12T16:35:21Z,MIT License,https://github.com/TheAlgorithms/Java
spring-framework,spring-projects,57526,38416,2025-03-12T14:14:20Z,Apache License 2.0,https://github.com/spring-projects/spring-framework
ghidra,NationalSecurityAgency,55270,6203,2025-03-12T17:03:29Z,Apache License 2.0,https://github.com/NationalSecurityAgency/ghidra
Stirling-PDF,Stirling-Tools,53902,4455,2025-03-12T15:58:49Z,MIT License,https://github.com/Stirling-Tools/Stirling-PDF
guava,google,50576,10965,2025-03-11T20:51:38Z,Apache License 2.0,https://github.com/google/guava
RxJava,ReactiveX,48041,7606,2025-03-10T08:34:15Z,Apache License 2.0,https://github.com/ReactiveX/RxJava
jadx,skylot,43125,5006,2025-03-11T21:58:12Z,Apache License 2.0,https://github.com/skylot/jadx"""

# Progress log file path
progress_log_file = "progress_log.json"


def update_progress_log(repository, status, message=None):
    """
    Update the progress log file incrementally.
    Args:
        repository (str): The name of the repository being processed.
        status (str): The status of the process (e.g., "in_progress", "completed", "error").
        message (str): An optional message (e.g., error details).
    """
    # Load the existing progress log if it exists
    if os.path.exists(progress_log_file):
        with open(progress_log_file, "r") as file:
            progress_log = json.load(file)
    else:
        progress_log = {}

    # Update the log for the given repository
    progress_log[repository] = {"status": status, "message": message}

    # Write the updated progress log back to the file
    with open(progress_log_file, "w") as file:
        json.dump(progress_log, file, indent=4)


def process_repositories(repositories_text):
    # Split the repositories data line by line
    repositories = repositories_text.strip().split("\n")
    total_repositories = len(repositories)  # Get the total count of repositories

    for index, repo_data in enumerate(repositories, start=1):
        # Extract the repository information
        repo_info = repo_data.split(",")
        repo_name = repo_info[0]  # Repository name (e.g., "JavaGuide")
        git_url = repo_info[-1]  # Git URL (e.g., "https://github.com/Snailclimb/JavaGuide")

        # Display progress in the terminal
        print(f"Processing repository {index}/{total_repositories}: {repo_name}")

        # Define the output file path based on the repository name
        output_file = f"{repo_name}.json"

        # Start repository processing
        print(f"🔄 Processing repository: {repo_name}")
        update_progress_log(repo_name, "in_progress", message=f"Started processing repository: {git_url}")

        try:
            # Extract commit history (10 years back by default)
            extract_commit_history_from_url(git_url, output_file, years_back=10)
            print(f"✅ Completed processing: {repo_name}")
            update_progress_log(repo_name, "completed", message=f"Commit history saved to {output_file}")
        except Exception as e:
            print(f"❌ Error processing repository {repo_name}: {e}")
            update_progress_log(repo_name, "error", message=str(e))


if __name__ == "__main__":
    process_repositories(repositories_text)

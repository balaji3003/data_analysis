import json

def search_json(input_json, output_json, query_items):
    """
    Searches a JSON file for specific file names, directory names, or text patterns in the directory structure.

    :param input_json: Path to the input JSON file.
    :param output_json: Path to save the filtered output JSON file.
    :param query_items: List of keywords to search for (partial or full matches).
    """

    try:
        # Load the JSON data
        with open(input_json, "r", encoding="utf-8") as json_file:
            repositories = json.load(json_file)

        matched_repositories = []  # List to store filtered results

        for repo in repositories:
            matched_directory_structure = {}
            matched_queries = set()  # Track which queries have been matched

            # Loop through each directory path in the structure
            for dir_path, contents in repo.get("directory_structure", {}).items():
                matched_files = []
                matched_dirs = []

                # Search for matches in directories
                for dir_name in contents["directories"]:
                    for query in query_items:
                        if query.lower() in dir_name.lower() and query not in matched_queries:
                            matched_dirs.append(dir_name)
                            matched_queries.add(query)  # Mark this query as found
                            break  # Stop checking more directories for this query

                # Search for matches in files
                for file_name in contents["files"]:
                    for query in query_items:
                        if query.lower() in file_name.lower() and query not in matched_queries:
                            matched_files.append(file_name)
                            matched_queries.add(query)  # Mark this query as found
                            break  # Stop checking more files for this query

                # If any matches were found, store them
                if matched_dirs or matched_files:
                    matched_directory_structure[dir_path] = {
                        "directories": matched_dirs,
                        "files": matched_files
                    }

                # If all query items have been matched, stop processing this repository
                if len(matched_queries) == len(query_items):
                    break  # No need to keep searching in this repository

            # If at least one match is found, keep this repository
            if matched_directory_structure:
                filtered_repo = {
                    "name": repo["name"],
                    "owner": repo["owner"],
                    "stars": repo["stars"],
                    "forks": repo["forks"],
                    "last_updated": repo["last_updated"],
                    "license": repo["license"],
                    "url": repo["url"],
                    "query_items_matched": list(matched_queries),
                    "directory_structure": matched_directory_structure
                }
                matched_repositories.append(filtered_repo)

        # Save the filtered results to the output JSON file
        with open(output_json, "w", encoding="utf-8") as json_file:
            json.dump(matched_repositories, json_file, indent=4)

        print(f"Filtered JSON file saved to {output_json}")

    except Exception as e:
        print(f"Error processing JSON: {e}")

# Example Usage
input_json_file = "repositories_structure_output.json"  # Input JSON with full directory structure
output_json_file = "filtered_repositories.json"  # Output JSON with matches
search_keywords = ["test.java", "groovy", "src/test"]  # List of keywords to search for

search_json(input_json_file, output_json_file, search_keywords)

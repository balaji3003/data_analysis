library(R6)
library(jsonlite)
library(ggplot2)
library(lubridate)
library(dplyr)
library(stringr)

# GitHub Repository Class
GitHubRepo <- R6Class("GitHubRepo",
  public = list(
    repo_url = NULL,
    repo_name = NULL,

    initialize = function(repo_url) {
      self$repo_url <- repo_url
      self$repo_name <- basename(gsub(".git$", "", repo_url))
      self$clone_or_update_repo()
    },

    clone_or_update_repo = function() {
      if (dir.exists(self$repo_name)) {
        message("Updating repository: ", self$repo_name)
        system(paste("git -C", self$repo_name, "pull"))
      } else {
        message("Cloning repository: ", self$repo_url)
        system(paste("git clone", self$repo_url))
      }
    },

    extract_git_history = function() {
      json_dir <- file.path(self$repo_name, "git_analysis")
      dir.create(json_dir, showWarnings = FALSE)
      json_file <- file.path(json_dir, "git_history.json")
      log_file <- file.path(json_dir, "git_history.log")

      system(paste("git -C", self$repo_name, "log --since='10 years ago' --numstat --date=iso --pretty=format:'%H|%an|%ae|%ad|%s' --shortstat >", log_file))

      log_data <- readLines(log_file)
      commit_list <- list()
      commit <- NULL

      for (line in log_data) {
        if (str_detect(line, "|")) {
          commit_info <- unlist(strsplit(line, "|"))
          if (length(commit_info) >= 5) {
            commit <- list(
              commit_hash = commit_info[1],
              author = list(name = commit_info[2], email = commit_info[3]),
              date = commit_info[4],
              message = commit_info[5],
              file_changes = list()
            )
          }
        } else if (!is.null(commit) && str_detect(line, "\\d+\\s+\\d+\\s+")) {
          matches <- unlist(str_match(line, "(\\d+|-)", "(\\d+|-)", "(.+)"))
          commit$file_changes <- append(commit$file_changes, list(
            list(
              filename = matches[3],
              lines_added = ifelse(matches[1] == "-", 0, as.integer(matches[1])),
              lines_deleted = ifelse(matches[2] == "-", 0, as.integer(matches[2]))
            )
          ))
        } else if (!is.null(commit)) {
          commit_list <- append(commit_list, list(commit))
          commit <- NULL
        }
      }
      write_json(commit_list, json_file, pretty = TRUE)
      message("Git history extracted to: ", json_file)
      return(json_file)
    }
  )
)

# Analysis Class
GitAnalysis <- R6Class("GitAnalysis",
  public = list(
    json_file = NULL,
    repo_name = NULL,

    initialize = function(json_file, repo_name) {
      self$json_file <- json_file
      self$repo_name <- repo_name
    },

    analyze_commit_history = function() {
      data <- fromJSON(self$json_file)
      df <- data.frame(date = sapply(data, function(x) x$date), stringsAsFactors = FALSE)
      df$date <- as.Date(df$date)
      commit_count <- df %>% count(date = floor_date(date, "week"))

      ggplot(commit_count, aes(x = date, y = n)) +
        geom_line() +
        labs(title = "Commit Frequency Over Time", x = "Year", y = "Commits per Week")
    },

    analyze_code_churn = function() {
      data <- fromJSON(self$json_file)
      file_changes <- do.call(rbind, lapply(data, function(commit) {
        do.call(rbind, lapply(commit$file_changes, function(fc) {
          data.frame(filename = fc$filename, lines_added = fc$lines_added, lines_deleted = fc$lines_deleted)
        }))
      }))
      
      df <- aggregate(. ~ filename, data = file_changes, sum)
      df <- df[order(df$lines_added + df$lines_deleted, decreasing = TRUE), ][1:10, ]
      
      ggplot(df, aes(x = reorder(filename, lines_added + lines_deleted), y = lines_added + lines_deleted)) +
        geom_bar(stat = "identity", fill = "blue") +
        coord_flip() +
        labs(title = "Top 10 Most Changed Files", x = "File", y = "Lines Changed")
    },

    analyze_bug_prone_files = function() {
      data <- fromJSON(self$json_file)
      bug_files <- table(unlist(lapply(data, function(commit) {
        if (grepl("fix", commit$message, ignore.case = TRUE)) {
          sapply(commit$file_changes, function(fc) fc$filename)
        }
      })))
      
      df <- as.data.frame(bug_files, stringsAsFactors = FALSE)
      df <- df[order(df$Freq, decreasing = TRUE), ][1:10, ]
      
      ggplot(df, aes(x = reorder(Var1, Freq), y = Freq)) +
        geom_bar(stat = "identity", fill = "red") +
        coord_flip() +
        labs(title = "Top 10 Bug-Prone Files", x = "File", y = "Fix Count")
    },

    analyze_top_contributors = function() {
      data <- fromJSON(self$json_file)
      contributors <- table(sapply(data, function(commit) commit$author$name))
      
      df <- as.data.frame(contributors, stringsAsFactors = FALSE)
      df <- df[order(df$Freq, decreasing = TRUE), ][1:10, ]
      
      ggplot(df, aes(x = reorder(Var1, Freq), y = Freq)) +
        geom_bar(stat = "identity", fill = "green") +
        coord_flip() +
        labs(title = "Top 10 Contributors", x = "Contributor", y = "Commit Count")
    }
  )
)

# Main Execution
repo_url <- readline("Enter GitHub repository URL: ")
repo <- GitHubRepo$new(repo_url)
json_file <- repo$extract_git_history()
analysis <- GitAnalysis$new(json_file, repo$repo_name)

print("Performing Analysis...")
analysis$analyze_commit_history()
analysis$analyze_code_churn()
analysis$analyze_bug_prone_files()
analysis$analyze_top_contributors()

print("Analysis Completed!")

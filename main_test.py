import re
import os
import sys
import time
import multiprocessing

from git import Repo
from jira import JIRA

# You can use following environment variables:
# JIRA_SERVER - Jira server URL (required)
# JIRA_TOKEN - Jira token (required)
# LATEST_RELEASE_TAG - latest release tag (optional). Takes the latest tag if not specified from git.
# JIRA_FIX_VERSION - Jira fix version (optional). Takes the version from active branch name (release/<version>) if not specified.

repo = Repo()

def main():
    repo_name = repo.working_tree_dir.split("/")[-1]
    current_brunch = repo.active_branch
    
    # Get new version
    jira_fix_version = os.environ.get('JIRA_FIX_VERSION')
    if not jira_fix_version:
        try:          
            # Get new version from git branch name
            new_version_pattern = re.compile(r'/[0-9]+\.[0-9]?.+')
            new_version = new_version_pattern.search(
                current_brunch.name).group().split('/')[1]
            jira_fix_version = repo_name + '-' + new_version
        except:
            sys.exit(
                "Error: Can't get new version. Brunch {} doesn't " \
                "match the pattern: " \
                "<branch>/<version>.<version>".format(current_brunch.name)
            )

    # Get latest tag
    latest_release_tag = os.environ.get('LATEST_RELEASE_TAG')
    if not latest_release_tag:
        try:
            # Get sorted tags by commit date
            sorted_tags = [
                tag.name for tag in sorted(
                    repo.tags, key=lambda t: t.commit.committed_datetime
                )
            ]
            # Set pattern for release tags
            release_tag_pattern = re.compile(
                    r'(\d+\.\d+\.\d+(?!-))|(v\d+\.\d+\.\d+(?!-))'
                )
            # Filter release tags
            release_tags = [
                    tag for tag in sorted_tags 
                    if release_tag_pattern.match(tag)
                ]
            # Get latest release tag from filtered tags
            latest_release_tag = release_tags[-1]
        except:
            sys.exit(
                "Error: Can't get latest release tag. " \
                "Check if there are any release tags in the repo."
            )

    # Get Jira issues ids from git commits
    git_commits = repo.git.log(
            str(latest_release_tag) + '..HEAD', '--pretty=%s'
        ).split('\n')

    jira_id_pattern = re.compile(r'EPMRPP-[0-9]+')
    jira_issues_ids = {
        jira_id_pattern.search(line).group()
        for line in git_commits
        if jira_id_pattern.match(line)
    }
    
    # Print info
    print("Repo name:", repo_name)
    print("Current brunch:", current_brunch)
    print("Jira fix version:", jira_fix_version)
    print("Latest tag:", latest_release_tag)
    print("Numbers of Jira IDs:", len(jira_issues_ids))
    print("Jira IDs:", jira_issues_ids)
    
if __name__ == "__main__":
    main()
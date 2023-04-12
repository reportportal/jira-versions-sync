import re
import os
import sys

from git import Repo

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
    latest_tag = os.environ.get('LATEST_RELEASE_TAG')
    if not latest_tag:
        try:
            sorted_tags = sorted(repo.tags, key=lambda t: t.commit.committed_datetime)
            latest_tag = sorted_tags[-1]
        except:
            sys.exit("Error: Can't get latest tag. Check if there are any tags in the repo.")

    # Get Jira issues ids from git commits
    git_commits = repo.git.log(str(latest_tag) + '..HEAD', '--pretty=%s').split('\n')

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
    print("Latest tag:", latest_tag)
    print("Numbers of Jira issues:", len(jira_issues_ids))
    print("Jira issues ids:", jira_issues_ids)
    
if __name__ == "__main__":
    main()
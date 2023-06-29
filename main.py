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
jira_server = JIRA(
        server=os.environ.get('JIRA_SERVER'),
        token_auth=os.environ.get('JIRA_TOKEN'),
        )
jira_project_name = 'EPMRPP' # TODO: Get project name from env variable

def update_issue_task(issue_id, jira_fix_version):
    try:
        issue = jira_server.issue(issue_id, fields='fixVersions')         
        current_fix_versions = [fix_version.name for fix_version in issue.fields.fixVersions]
        
        if jira_fix_version not in current_fix_versions:
            current_fix_versions.append(jira_fix_version)
        
        updated_fix_versions = [{'name': fix_version} for fix_version in current_fix_versions]
        issue.update(fields={'fixVersions': updated_fix_versions}, notify=False)
        
        return issue_id
    except:
        print("Error: Can't update issue: " + issue_id)

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

    jira_id_pattern = re.compile(r'(?i)epmrpp-[0-9]+')
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

    # Check if version exists and create it if not
    if jira_server.get_project_version_by_name(jira_project_name, jira_fix_version) is None:
        jira_server.create_version(name=jira_fix_version, project=jira_project_name)

    # Update Fix Version field for all Jira issues
    start = time.time()

    with multiprocessing.Pool() as p:
        results = [
            p.apply_async(
                update_issue_task, args=(jira_issue, jira_fix_version)
            ) for jira_issue in jira_issues_ids
        ]
        
        for r in results:
            r.wait()

    end = time.time()
    total_time = end - start
    print("Number updated Jira issues:", len(results))
    print("Time execution:" + str(total_time))
    print("The following issues were updated:" + str([r.get() for r in results]))
    
if __name__ == "__main__":
    main()

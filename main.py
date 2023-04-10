import re
import time
import multiprocessing
import os

from git import Repo
from jira import JIRA

# You can use following environment variables:
# JIRA_SERVER - Jira server URL (required)
# JIRA_TOKEN - Jira token (required)
# LATEST_RELEASE_TAG - latest release tag (optional). Takes the latest tag if not specified from active branch name

repo = Repo()
jira_server = JIRA(
        server=os.environ.get('JIRA_SERVER'),
        token_auth=os.environ.get('JIRA_TOKEN'),
        )

def update_issue_task(issue_id, jira_fix_version):
    try:
        issue = jira_server.issue(issue_id, fields='None')
        issue.update(fields={'fixVersions': [{'name': jira_fix_version}]}, notify=False)
        return issue_id
    except:
        print("Error: Can't update issue: " + issue_id)

def main():
    repo_name = repo.working_tree_dir.split("/")[-1]
    current_brunch = repo.active_branch
    
    try:
        new_version_pattern = re.compile(r'/[0-9]+\.[0-9]?.+')
        new_version = new_version_pattern.search(
            current_brunch.name).group().split('/')[1]
    except:
        print("Error: Can't get new version. Check brunch name according to the pattern: <branch_name>/<version>.")

    jira_fix_version = repo_name + '-' + new_version

    latest_tag = os.environ.get('LATEST_RELEASE_TAG')
    if latest_tag is None:
        try:
            sorted_tags = sorted(repo.tags, key=lambda t: t.commit.committed_datetime)
            latest_tag = sorted_tags[-1]
        except:
            print("Error: Can't get latest tag. Check if there are any tags in the repo.")

    git_commits = repo.git.log(str(latest_tag) + '..HEAD', '--pretty=%s').split('\n')

    jira_id_pattern = re.compile(r'EPMRPP-[0-9]+')
    jira_issues_ids = {
        jira_id_pattern.search(line).group()
        for line in git_commits
        if jira_id_pattern.match(line)
        }
    
    print("Repo name:", repo_name)
    print("Current brunch:", current_brunch)
    print("Jira fix version:", jira_fix_version)
    print("Latest tag:", latest_tag)
    print("Numbers of Jira issues:", len(jira_issues_ids))
    
    project_name = 'EPMRPP'

    # Check if version exists and create it if not
    if jira_server.get_project_version_by_name(project_name, jira_fix_version) is None:
        jira_server.create_version(name=jira_fix_version, project=project_name)

    # Update Fix Version field for all Jira issues
    start = time.time()

    with multiprocessing.Pool() as p:
        results = [p.apply_async(update_issue_task, args=(jira_issue, jira_fix_version)) for jira_issue in jira_issues_ids]
        for r in results:
            r.wait()

    end = time.time()
    total_time = end - start
    print("Time execution:" + str(total_time))
    print("The following issues were updated:" + str([r.get() for r in results]))
    
if __name__ == "__main__":
    main()
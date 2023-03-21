from __future__ import annotations
import scipy.stats as stats
import numpy as np
import click
import json

from datetime import datetime, timedelta
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field
import random

EXTERNAL_ID = 3
NOW = datetime.now()
ONEDAY = timedelta(days=1)


class User(BaseModel):
    name: str


class Status(Enum):
    To_Do = "To Do"
    In_Progress = "In Progress"
    Done = "Done"


class StatusId(Enum):
    To_Do = 10000
    In_Progress = 3
    Done = 10001


class IssueType(Enum):
    Story = "Story"
    Bug = "Bug"


class Transition(BaseModel):
    fieldType: str = Field(default="jira", const=True)
    field: str = Field(default="status", const=True)
    from_: StatusId = Field(...,alias="from")
    fromString: Status
    to: StatusId
    toString: Status


ToDo_to_InProgress = Transition(
    **{
    'fieldType':'jira',
    'field':'status',
    'from':StatusId.To_Do,
    'fromString':Status.To_Do,
    'to':StatusId.In_Progress,
    'toString':Status.In_Progress
    }
)
InProgress_to_Done = Transition(
    **{
    'fieldType':'jira',
    'field':'status',
    'from':StatusId.In_Progress,
    'fromString':Status.In_Progress,
    'to':StatusId.Done,
    'toString':Status.Done
    }
)


class HistoryItem(BaseModel):
    author: str
    created: datetime
    items: List[Transition]


class Issue(BaseModel):
    description: str
    status: Status
    reporter: str
    issueType: IssueType
    resolution: Optional[str | None] = Field(default=None, regex="Done")
    created: datetime
    updated: datetime
    summary: str
    assignee: str
    externalId: str
    history: List[HistoryItem]



class Project(BaseModel):
    key: str
    issues: List[Issue]


class Model(BaseModel):
    users: List[User]
    projects: List[Project]


def gen_issue(user, creation_days_ago, duration):
    global EXTERNAL_ID
    descr = summary = "This is external issue %s" % EXTERNAL_ID
    reporter = user
    assignee = user
    status = Status.In_Progress
    if duration <= creation_days_ago:
        status = Status.Done

    created = NOW - timedelta(days=creation_days_ago)
    updated = created + timedelta(days=duration)
    if created.weekday() == 5:
        created = created - ONEDAY
    elif created.weekday() == 6:
        created = created + ONEDAY

    if updated.weekday() == 5:
        updated = updated - ONEDAY
    elif updated.weekday() == 6:
        updated = updated + ONEDAY

    issuetype = IssueType.Story

    history = []
    if status == Status.In_Progress:
        history = [
            HistoryItem(author=user, created=created, items=[ToDo_to_InProgress])
        ]
    else:
        history = [
            HistoryItem(author=user, created=created, items=[ToDo_to_InProgress]),
            HistoryItem(author=user, created=updated, items=[InProgress_to_Done]),
        ]

    issue = Issue(
        description=descr,
        status=status,
        reporter=reporter,
        issueType=IssueType.Story,
        created=created,
        updated=updated,
        summary=summary,
        assignee=assignee,
        externalId=EXTERNAL_ID,
        history=history,
    )
    EXTERNAL_ID +=1 
    if Status.Done == status:
        issue.resolution = 'Done'
    return issue


@click.command()
@click.option("--output","-o", default="jira_issues.json", help="output file")
@click.option("--project","-p", help="JIRA project")
@click.option("--useridentifier","-u", multiple=True, help="JIRA user")
def generate_jira_issues(output, project, useridentifier):
    mu = 3
    sigma = 10
    # Define the lower and upper bounds of the truncated distribution
    lower_bound = 0
    upper_bound = 60

    # Create a truncated normal distribution using the lower and upper bounds
    trunc_norm = stats.truncnorm(
        (lower_bound - mu) / sigma, (upper_bound - mu) / sigma, loc=mu, scale=sigma
    )

    # Generate a random sample from the truncated normal distribution
    sample = trunc_norm.rvs(size=100)

    # Convert the truncated normal sample to a Poisson distribution
    poisson_sample = stats.poisson.rvs(mu=sample, size=100)


 

    lookbackweeks = [1, 2, 3, 5, 8, 13, 21, 34, 55]
    issues = []

    lasttime = 0
    for weeksago in lookbackweeks:
        for duration in poisson_sample:
            userloc = random.randint(0,len(useridentifier)-1)
            issue = gen_issue(useridentifier[userloc], random.randint(lasttime*7,weeksago*7), int(duration))
            issues.append(issue)
        lasttime = weeksago

    users = [User(name=uid) for uid in useridentifier]

    project = Project(key=project, issues=issues)

    model = Model(users=users, projects=[project])

    print(poisson_sample)

    with open(output,"w") as ofile:
        ofile.write(model.json(exclude_unset=True,by_alias=True))


if __name__ == "__main__":
    generate_jira_issues()

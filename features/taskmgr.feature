```gherkin
Feature: taskmgr command-driven task manager

  Scenario: Add a minimal task
    Given an empty task list
    When I run the command: add name="VV Specification"
    Then the output contains: "Command success: add name=\"VV Specification\""
    And a task with name "VV Specification" exists with done=False

  Scenario: List tasks by type case-insensitive
    Given tasks exist with types "School" and "school"
    When I run the command: list property="type" val="school"
    Then the output contains: "Command success: list property=\"type\" val=\"school\""
    And the listed tasks only include those with type case-insensitively matching "school"

  Scenario: Mark task done with invalid id
    Given an empty task list
    When I run the command: done id=100
    Then the output contains: "Error TaskNotFound: done id=100"

  Scenario: Modify due with invalid date format
    Given a task with id 0 exists
    When I run the command: mod id=0 property="due" new_val="2025/10/31"
    Then the output contains: "Error InvalidDateFormat: mod id=0 property=\"due\" new_val=\"2025/10/31\""
```
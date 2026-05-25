Feature: Doctor diagnostic
  As a user setting up strudel-gen
  I want to check whether my environment has all prerequisites
  So that I know what to install before rendering

  Background:
    Given the strudel-gen CLI is installed

  Scenario: All prerequisites present
    Given SuperCollider is installed at "/usr/local/bin/sclang"
    And Node.js is installed at "/usr/local/bin/node"
    And pnpm is installed at "/usr/local/bin/pnpm"
    And Strudel is cloned at "/home/user/devel/strudel"
    When I run "strudel-gen doctor"
    Then the exit code should be 0
    And the output should contain "All prerequisites found"

  Scenario: Missing SuperCollider
    Given SuperCollider is not installed
    And Node.js is installed at "/usr/local/bin/node"
    And pnpm is installed at "/usr/local/bin/pnpm"
    And Strudel is cloned at "/home/user/devel/strudel"
    When I run "strudel-gen doctor --verbose"
    Then the exit code should be 1
    And the output should contain "sclang"
    And the output should contain "install hints"

  Scenario: All missing
    Given SuperCollider is not installed
    And Node.js is not installed
    And pnpm is not installed
    And Strudel is not cloned
    When I run "strudel-gen doctor"
    Then the exit code should be 1
    And the output should contain "Some prerequisites are missing"

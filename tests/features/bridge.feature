Feature: Bridge and SC lifecycle
  As a user rendering soundscapes
  I want the OSC bridge and SuperCollider to start and stop cleanly
  So that I can record audio reliably

  Background:
    Given the strudel-gen CLI is installed
    And sclang is available on the system
    And a Strudel clone is available

  Scenario: Start and stop both services
    When I run "strudel-gen session --dry-run --duration 2 --timeout-sc 120 --timeout-bridge 30"
    Then the exit code should be 0
    And the output should contain "Session active"
    And the output should contain "Session complete"

  Scenario: Doctor shows sclang before session
    When I run "strudel-gen doctor"
    Then the exit code should be 0

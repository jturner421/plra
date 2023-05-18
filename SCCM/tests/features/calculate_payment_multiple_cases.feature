# Created by jwt at 9/24/21
Feature: Payment Applied to Multiple Cases
  What happens when an payment occurs when two or more active cases exist.

  Scenario: Multiple Cases, oldest case paid, newest case with balance
    Given I'm a prisoner with multiple active cases
    And I owe $160.65 in my oldest case
    And I owe $350.00 in my newest case
    When I make a payment in the amount of $178.32
    Then I should have a balance of $0.00 in my oldest case
    And I should have a balance of $332.23 in my newest case

    Scenario: Multiple Cases, oldest case with balance
    Given I'm a prisoner with multiple unpaid active cases
    And I owe $160.65 in my oldest case
    And I owe $350.00 in my newest case
    When I make a payment in the amount of $4.59
    Then I should have a balance of $156.06 in my oldest case
    And I should have a balance of $350.00 in my newest case
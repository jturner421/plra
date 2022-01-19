# Created by jwt at 9/24/21
Feature: Payment
  Applying payment in a prisoner case.

  Scenario: Single Case is paid off
    Given I'm a prisoner with an active case
    And I owe $160.65
    When I make a payment in the amount of $172.87
    Then I should receive a refund of $12.22

  Scenario: Single Case with balance
    Given I'm a prisoner with an active case
    And I owe $160.65
    When I make a payment in the amount of $126.34
    Then I should have a balance of $34.31

  Scenario: No Case
    Given I'm a prisoner with no active cases
    When I make a payment in the amount of $50.00
    Then I should receive a refund of $50.00


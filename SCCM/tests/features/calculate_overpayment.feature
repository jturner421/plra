# Created by jwt at 9/24/21
Feature: Overpayment
  What happens when an overpayment occurs when one or more cases are paid off.

  Scenario: Multiple Cases, both cases paid off
    Given I'm a prisoner with multiple cases
    And I owe $160.65 in my oldest case
    And I owe $350.00 in my newest case
    When I make a payment in the amount of $525.00
    Then I should have a balance of $0.00 in my oldest case
    And I should have a balance of $0.00 in my newest case
    And I should have an overpayment of $14.35
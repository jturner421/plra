# Created by jwt at 9/24/21
Feature: Overpayment
  What happens when an overpayment occurs when one or more cases are paid off.

  Scenario: Multiple Cases, oldest case paid, newest case with balance
    Given I'm a prisoner with multiple active cases
    And I owe $160.65 in my oldest case
    And I owe $350.00 in my newest case
    When I make a payment in the amount of $178.32
    Then I should have a balance of $0.00 in my oldest case
    And I should have a balance of $332.23 in my newest case
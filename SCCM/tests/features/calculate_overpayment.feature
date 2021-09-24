# Created by jwt at 9/24/21
Feature: Overpayment
  What happens when an overpayment occurs when one or more cases are paid off.

  Scenario: Single Case is paid off
    Given I'm a prisoner with an active case
    And I owe $160.65

    When I make a payment in the amount of $172.87
#    And The payment exceeds what I owe

    Then I should receive a refund of $12.22
#    And My case is marked as paid off

#    Rule: Excess payments are refunded
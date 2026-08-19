# Virtuals ACP — Agent Commerce Protocol

## Revenue
155K jobs, $398K/30d, 3.84K active wallets, ~$2.56/job

## What It Does
Agents buy/sell services from each other via on-chain escrow on Base.

## QDW Mapping
- ACPJobOffering → Factory manifest
- ACPJob → WorkGraph node (with payment)
- ACPJobPhase → WorkGraph state machine
- ACPMemo → Evidence/artifacts
- evaluator → VerificationService
- escrow → Cost ledger

## Strategy
ACP = payment rails + escrow
QDW = economic authority that decides what to build

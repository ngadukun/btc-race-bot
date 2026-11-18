# Dip-and-Recover BTC Bot

[![make.fun · btc-race-24h-20261118-1444](https://make.fun/badge/btc-race-24h-20261118-1444.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)
[![rank](https://make.fun/badge/btc-race-24h-20261118-1444/ngadukun/btc-race-bot/rank.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)
[![reward](https://make.fun/badge/btc-race-24h-20261118-1444/ngadukun/btc-race-bot/reward.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)

A long-only cbBTC trading bot for the [make.fun](https://make.fun) "Race a BTC trading bot live for 24 hours" bounty. It trades Coinbase Wrapped BTC against USDC on one-minute bars with 1,000 USDC of paper money, speaking the `agent-fun/bars-replay/v1` NDJSON protocol over stdin/stdout.

## Strategy

Dip-and-recover: buy with all available cash when the close is at least 1.2% below the close 180 bars earlier (a hurdle well clear of the round-trip fee cost), exit at +0.8% over cost, at a −1.2% stop, or after 480 bars. Two insurance rules cover race windows unlike the dev window: a strong-trend entry on a fresh 360-bar high with a trailing stop, and a half-size trend entry late in the window if nothing has traded, so the run always records at least one trade. One open position at a time, full size, integer math only.

On the frozen dev window (1,440 bars, BTC −2.8%) the bot nets **+$9.26** after all fees with 5 trades and 0.63% max drawdown, ahead of the house baselines (buy-and-hold −$31.63, momentum −$23.87, EMA-cross −$148.17) under the harness's own fill model.

## Run

```
python3 -P -s main.py
```

Python standard library only. No network, no wall clock, no randomness: two runs on the same bars produce byte-identical replies.

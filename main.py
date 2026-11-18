"""Dip-and-recover bot for the make.fun BTC 24h bars race (agent-fun/bars-replay/v1).

Strategy (long only, one position, full size):
  - Dip entry: when the latest close is at least 1.2% below the close 180 bars
    (3 hours) earlier, buy with all cash. Deep, fast drops in cbBTC have tended
    to bounce; the 1.2% hurdle is well clear of the ~0.3% full-size round-trip
    cost (4 bps fee + 2 bps slippage + constant-product impact, each way).
  - Dip exit: sell everything at +0.8% over the position's cost, at -1.2%
    under it, or after 480 bars, whichever comes first.
  - Trend insurance (never fires on the dev window): in a strong uptrend the
    dip may never come, so if the close makes a 360-bar high at least 3%
    above where it was 360 bars ago, buy and ride it with a 0.8% trailing
    stop (same -1.2% cost stop, 720-bar cap). If nothing has traded by bar
    1200 and the close is above its 720-bar mean, take a half-size trend
    position on the same exit rules, so the bot always has its one trade.
All comparisons are integer arithmetic: the same bars give the same orders in
every run. Standard library only; no clock, no network, no randomness.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

SYMBOL = "CBBTC"
SLIP_BPS = 300

DIP_LOOKBACK = 180        # bars (3 hours at 1m)
DIP_DROP_NUM = 988        # enter when close < ref * 988/1000  (-1.2%)
TARGET_NUM = 1008         # dip exit at value >= cost * 1008/1000  (+0.8%)
STOP_NUM = 988            # exit at value <= cost * 988/1000  (-1.2%)
DIP_TIMEOUT = 480         # bars

TREND_LOOKBACK = 360
TREND_RISE_NUM = 103      # close >= ref * 103/100 and a 360-bar high
TRAIL_NUM = 992           # trend exit at value <= peak * 992/1000  (-0.8%)
TREND_TIMEOUT = 720

INSURE_SEQ = 1200
INSURE_MEAN_BARS = 720
INSURE_FRACTION = 2       # buys cash // 2

closes = []               # every close seen, in order
mode = None               # None | "dip" | "trend"
entry_seq = -1
peak_value = 0
traded = False


def on_batch(state, batch):
    global mode, entry_seq, peak_value, traded
    bar = state.latest.get(SYMBOL)
    if bar is None:
        return []
    closes.append(int(bar["c"]))
    i = len(closes) - 1
    c = closes[i]
    held = state.positions.get(SYMBOL)

    if held is not None and held.qty > 0:
        val = state.value(SYMBOL, held.qty)
        if val > peak_value:
            peak_value = val
        sell = False
        if mode == "dip":
            sell = (
                val * 1000 >= held.cost * TARGET_NUM
                or val * 1000 <= held.cost * STOP_NUM
                or state.seq - entry_seq >= DIP_TIMEOUT
            )
        else:
            sell = (
                val * 1000 <= peak_value * TRAIL_NUM
                or val * 1000 <= held.cost * STOP_NUM
                or state.seq - entry_seq >= TREND_TIMEOUT
            )
        if sell:
            mode = None
            return [{"side": "sell", "symbol": SYMBOL, "qty": held.qty,
                     "max_slippage_bps": SLIP_BPS}]
        return []

    if state.warming_up:
        return []

    # Dip entry: a deep, fast drop.
    if i >= DIP_LOOKBACK and c * 1000 < closes[i - DIP_LOOKBACK] * DIP_DROP_NUM:
        if state.cash >= 1_000_000:
            mode, entry_seq, peak_value, traded = "dip", state.seq, 0, True
            return [{"side": "buy", "symbol": SYMBOL,
                     "notional_quote_units": state.cash,
                     "max_slippage_bps": SLIP_BPS}]
        return []

    # Strong-trend entry: a fresh 360-bar high, well above 360 bars ago.
    if i >= TREND_LOOKBACK and c >= max(closes[i - TREND_LOOKBACK:i]) \
            and c * 100 > closes[i - TREND_LOOKBACK] * TREND_RISE_NUM:
        if state.cash >= 1_000_000:
            mode, entry_seq, peak_value, traded = "trend", state.seq, 0, True
            return [{"side": "buy", "symbol": SYMBOL,
                     "notional_quote_units": state.cash,
                     "max_slippage_bps": SLIP_BPS}]
        return []

    # Insurance: nothing traded late in the window and price is above its
    # 720-bar mean -- take a half-size trend position so the run has a trade.
    if not traded and state.seq >= INSURE_SEQ and i >= INSURE_MEAN_BARS:
        window = closes[i - INSURE_MEAN_BARS + 1:i + 1]
        if c * INSURE_MEAN_BARS > sum(window):
            amount = state.cash // INSURE_FRACTION
            if amount >= 1_000_000:
                mode, entry_seq, peak_value, traded = "trend", state.seq, 0, True
                return [{"side": "buy", "symbol": SYMBOL,
                         "notional_quote_units": amount,
                         "max_slippage_bps": SLIP_BPS}]
    return []


if __name__ == "__main__":
    makefun_bars.run(on_batch)

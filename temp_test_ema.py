import pandas as pd
import logging
import sys
import os

# Add local dir to sys.path to import services
sys.path.append(os.getcwd())

from services.patterns import CandlePatternDetector

# Setup logging
logging.basicConfig(level=logging.DEBUG)

def test_trend():
    print("Testing Trend Logic...")
    # Create a simple uptrend
    # Close: 10, 12, 14, 16, 18, 20
    # EMA(5) should be lagging below 20.
    data = {
        'open': [10, 12, 14, 16, 18, 20],
        'high': [11, 13, 15, 17, 19, 21],
        'low':  [9, 11, 13, 15, 17, 19],
        'close': [10, 12, 14, 16, 18, 20]
    }
    df = pd.DataFrame(data)
    
    # Initialize detector with trend_lookback=3 (short)
    detector = CandlePatternDetector(df, trend_lookback=3)
    
    # Calculate EMA manually for verification
    # span=3, adjust=False
    # Start: 10
    # t1: (12 - 10)*(2/4) + 10 = 11
    # t2: (14 - 11)*(2/4) + 11 = 1.5 + 11 = 12.5
    # t3: (16 - 12.5)*0.5 + 12.5 = 1.75 + 12.5 = 14.25
    # t4: (18 - 14.25)*0.5 + 14.25 = 1.875 + 14.25 = 16.125
    # t5: (20 - 16.125)*0.5 + 16.125 = 18.0625
    
    # At index 5 (last): Close=20, EMA=18.06
    # Close > EMA => Trend 1
    
    trend = detector._get_trend(i=-1)
    print(f"Index -1 Trend: {trend}")
    assert trend == 1, f"Expected trend 1, got {trend}"
    
    # Test Downtrend
    data_down = {
        'open': [20]*6, 'high': [20]*6, 'low': [10]*6,
        'close': [20, 18, 16, 14, 12, 10]
    }
    df_down = pd.DataFrame(data_down)
    detector_down = CandlePatternDetector(df_down, trend_lookback=3)
    trend_down = detector_down._get_trend(i=-1)
    print(f"Index -1 Trend Down: {trend_down}")
    assert trend_down == -1, f"Expected trend -1, got {trend_down}"
    
    print("ALL TESTS PASSED")

if __name__ == "__main__":
    test_trend()

import pandas as pd
import pandas_ta as ta
import numpy as np

def test_bbands():
    # Create mock data
    df = pd.DataFrame({
        'close': np.random.uniform(100, 200, 100)
    })
    
    print("Pandas TA version:", ta.version)
    
    # Calculate Bollinger Bands
    try:
        bb = ta.bbands(df['close'], length=20, std=2)
        print("\nColumns returned by ta.bbands:")
        print(bb.columns.tolist())
        
        # Try to access the specific column
        print("\nAccessing 'BBU_20_2.0':")
        print(bb['BBU_20_2.0'].head())
        print("Success!")
        
    except Exception as e:
        print(f"\nError: {e}")
        if 'bb' in locals() and bb is not None:
             print("BB DataFrame head:")
             print(bb.head())

if __name__ == "__main__":
    test_bbands()

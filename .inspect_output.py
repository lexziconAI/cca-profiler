import os, pandas as pd
df = pd.read_excel(os.environ["CCIP_OUT"])
score_cols = [c for c in ["DT Score","TR Score","CO Score","CA Score","EP Score"] if c in df.columns]
print("Score columns:", score_cols)
if score_cols: print(df[score_cols].head().to_string(index=False))

import os, pandas as pd
p = os.environ["CCIP_IN"]
df = pd.read_excel(p, nrows=5)
cols = list(df.columns)
anchor_idx = next((i for i,c in enumerate(cols)
                   if isinstance(c,str) and "prefer to be clear and direct" in c.lower()), None)
print("anchor_idx:", anchor_idx)
if anchor_idx is not None:
    q_headers = cols[anchor_idx+1:anchor_idx+26]
    print("Q1-Q25 headers:", q_headers)
print("Has ID:", "ID" in df.columns, "Has Email:", "Email" in df.columns)

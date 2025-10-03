import pandas as pd
import numpy as np

# Load CSV
df = pd.read_csv(
    r"C:\Users\sunil\Downloads\1_himansh_station_4052_CSV.csv",
    dtype=str,        # all columns as string
    low_memory=False  # avoids chunked reading warning
)

# Remove duplicates
df = df.drop_duplicates()

# Replace "/" with "-"
df = df.replace("/", "-", regex=True).infer_objects(copy=False)

# Add Clear column
def is_clear(val):
    if pd.isna(val) or str(val).strip() == "":
        return 1
    allowed = set("0123456789 :-")
    return 0 if set(str(val)).issubset(allowed) else 1

df["Clear"] = df['TIMESTAMP_RAW'].apply(is_clear)

# Filter Clear=0
df = df[df["Clear"] == 0].copy()

# Split TIMESTAMP_RAW
split = df['TIMESTAMP_RAW'].str.split(" ", n=1, expand=True)
df["Column1.1"], df["Column1.2"] = split[0], split[1]

# ---- Flag detection ----
def get_flag(val):
    parts = str(val).split("-")
    if len(parts) < 3: 
        return "N"
    try:
        i = 1 if len(parts[0]) == 4 else 0
        j = 1 if len(parts[2]) == 4 else 2
        a, b = int(parts[i]), int(parts[j])
        return "Y" if (a > 12 or b > 12) else "N"
    except:
        return "N"

df["Flag"] = df["Column1.1"].apply(get_flag)

# ---- Add D_Index ----
def get_d_index(val, flag):
    if flag != "Y": return None
    parts = str(val).split("-")
    if len(parts) < 3: return None
    i = 1 if len(parts[0]) == 4 else 0
    j = 1 if len(parts[2]) == 4 else 2
    a, b = int(parts[i]), int(parts[j])
    return i if a > 12 else j

df["D_Index"] = [get_d_index(x, f) for x, f in zip(df["Column1.1"], df["Flag"])]

# Fill D_Index down & up
df["D_Index"] = df["D_Index"].bfill().ffill()

# Convert to int
df["D_Index"] = df["D_Index"].astype(int)

# ---- Add Ref ----
def make_ref(val, flag):
    if flag != "Y": return None
    parts = str(val).split("-")
    if len(parts) < 3: return None
    i = 1 if len(parts[0]) == 4 else 0
    j = 1 if len(parts[2]) == 4 else 2
    k = 3 - i - j
    a, b, y = int(parts[i]), int(parts[j]), int(parts[k])
    m = b if a > 12 else a
    d = a if a > 12 else b
    return f"{y}-{m:02d}-{d:02d}"

df["Ref"] = [make_ref(x, f) for x, f in zip(df["Column1.1"], df["Flag"])]

# Fill Ref down, then fill missing with yyyy-mm-01
df["Ref"] = df["Ref"].ffill()
first_ref = df["Ref"].dropna().iloc[0]
if pd.notna(first_ref):
    df["Ref"] = df["Ref"].fillna(first_ref[:-2] + "01")

# ---- OP_1 and OP_2 ----
def op_dates(val, flag):
    if flag == "Y": return (None, None)
    parts = str(val).split("-")
    if len(parts) < 3: return (None, None)
    i = 1 if len(parts[0]) == 4 else 0
    j = 1 if len(parts[2]) == 4 else 2
    k = 3 - i - j
    a, b, y = int(parts[i]), int(parts[j]), int(parts[k])
    return (f"{y}-{a:02d}-{b:02d}", f"{y}-{b:02d}-{a:02d}")

df[["OP_1","OP_2"]] = df.apply(lambda r: pd.Series(op_dates(r["Column1.1"], r["Flag"])), axis=1)

def choose_correct(r):
    # convert once
    dOp1 = pd.to_datetime(r.OP_1, format="%Y-%m-%d", errors='coerce')
    dOp2 = pd.to_datetime(r.OP_2, format="%Y-%m-%d", errors='coerce')
    dRef = pd.to_datetime(r.Ref, format="%Y-%m-%d", errors='coerce')

    if r.Flag == "Y":
        return dRef
    if dOp1 == dOp2:
        return dOp1
    if dRef >= min(dOp1, dOp2) and dRef <= max(dOp1, dOp2):
        return max(dOp1, dOp2)
    
    try:
        d1, d2 = abs((dOp1 - dRef).days), abs((dOp2 - dRef).days)
        if d1 <= 30 and d2 <= 30:
            return dOp1 if d1 <= d2 else dOp2
    except:
        pass

    # --- reconstruct from Column1.1 and D_Index ---
    temp = str(r["Column1.1"]).split("-")
    i = r.D_Index
    k = 0 if len(temp[0]) == 4 else 1 if len(temp[1]) == 4 else 2
    j = 3 - i - k
    reconstructed = f"{temp[k]}-{int(temp[j]):02d}-{int(temp[i]):02d}"
    return pd.to_datetime(reconstructed, format="%Y-%m-%d", errors='coerce')

df["Correct"] = pd.to_datetime(df.apply(choose_correct, axis=1), format="%Y-%m-%d", errors='coerce')

# ---- P_Correct (previous different value) ----
def prev_diff(series):
    result = []
    for i in range(len(series)):
        val, prev_val = series.iloc[i], ""
        for j in range(i-1, -1, -1):
            if series.iloc[j] != val:
                prev_val = series.iloc[j]
                break
        result.append(prev_val)
    return result

df["P_Correct"] = pd.to_datetime(prev_diff(df["Correct"]), format="%Y-%m-%d", errors='coerce')

def make_final(row):
    # Flag = "Y" case
    if row.Flag == "Y":
        return f"{row.Correct.strftime('%Y-%m-%d')} {row['Column1.2']}"
    
    # Flag != "Y" case
    correct_date = row.Correct
    p_correct_date = row.P_Correct
    
    # If P_Correct is None or <= Correct, use Correct
    if pd.isna(p_correct_date) or p_correct_date <= correct_date:
        base_value = correct_date.strftime('%Y-%m-%d')
    else:
        # Swap month and day
        parts = correct_date.strftime('%Y-%m-%d').split('-')
        base_value = f"{parts[0]}-{parts[2]}-{parts[1]}"
    
    # Append Column1.2 string
    final_value = f"{base_value} {row['Column1.2']}"
    return final_value

# Apply to DataFrame
df['Final'] = pd.to_datetime(df.apply(make_final, axis=1), format="%Y-%m-%d %H:%M", errors='coerce')

df.drop(columns=["Clear","Column1.1","Column1.2","Flag","D_Index","Ref","OP_1","OP_2","Correct","P_Correct"], inplace=True)

# Replace
df = df.replace("NAN", None, regex=True).infer_objects(copy=False)
df = df.replace("#NAME?", None, regex=True).infer_objects(copy=False)

df = df.astype({"RECORD":"int","BattV_Avg":"float","PTemp_C_Avg":"float","AirTC_Avg":"float","RH":"float","SUp_Avg":"float","SDn_Avg":"float",
                "LUp_Avg":"float","LDn_Avg":"float","CNR4TC_Avg":"float","CNR4TK_Avg":"float","RsNet_Avg":"float","RlNet_Avg":"float",
                "Albedo_Avg":"float","Rn_Avg":"float","LUpCo_Avg":"float","LDnCo_Avg":"float","WS_ms_Avg":"float","WS_ms_S_WVT":"float",
                "WindDir_D1_WVT":"float","WindDir_SD1_WVT":"float","WS_6m_ms_Avg":"float","WS_6m_ms_S_WVT":"float","WindDir_6m_D1_WVT":"float",
                "WindDir_6m_SD1_WVT":"float","DT_Avg":"float","Q_Avg":"float","TCDT_Avg":"float","DBTCDT_Avg":"float","TT_C_Avg":"float",
                "SBT_C_Avg":"float","BP_mmHg":"float","Rain_mm":"float","Precipitation_Diff":"float","Precipitation_Intensity":"float",
                "Precipitation_type":"float"})

df